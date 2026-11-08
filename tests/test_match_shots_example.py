"""Shot examples preflight extras and reproduce saved observations without HTTP."""

import json
import runpy
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

import esd
from tests.test_match_players import sofa_event
from tests.test_match_shots import load, shotmap

ROOT = Path(__file__).resolve().parent.parent / "examples/datasets"
OPTIONS = ["--source", "sofascore", "--league", "72", "--season", "2026", "--season-id", "228", "--match-id", "1"]


@pytest.fixture
def example(monkeypatch):
    fetch = Mock(side_effect=[sofa_event(), shotmap()])
    monkeypatch.setattr("esd._provider_datasets.get_api_json", fetch)
    dataset = load()
    loader = Mock(return_value=dataset)
    monkeypatch.setattr(esd, "load_dataset", loader)
    return runpy.run_path(str(ROOT / "match_shots.py")), loader, dataset


def test_explicit_ids_flags_and_cache_paths_are_forwarded(example, tmp_path):
    module, loader, _ = example
    assert module["main"]([*OPTIONS, "--max-match-requests", "4", "--with-events", "--with-players", "--cache-dir", str(tmp_path)]) == 0
    query = loader.call_args.kwargs
    assert query["tables"] == ["shots", "player_match_stats", "match_events"]
    assert query["match_ids"] == ["1"] and query["max_match_requests"] == 4 and query["cache_dir"] == tmp_path


@pytest.mark.parametrize("options", [[], ["--open-dir", "saved", "--with-events"], ["--open-dir", "saved", "--source", "espn"],
                                   [*OPTIONS, "--limit", "0"]])
def test_invalid_options_fail_before_network(example, options):
    module, loader, _ = example
    with pytest.raises(SystemExit) as exc:
        module["main"](options)
    assert exc.value.code == 2
    loader.assert_not_called()


def test_missing_extras_and_existing_destination_fail_before_download(example, monkeypatch, tmp_path):
    module, loader, _ = example
    monkeypatch.setitem(module["main"].__globals__, "find_spec", lambda _: None)
    for options in (["--pandas"], ["--output-dir", str(tmp_path / "new")], ["--output-dir", str(tmp_path)]):
        with pytest.raises(SystemExit) as exc:
            module["main"]([*OPTIONS, *options])
        assert exc.value.code == 2
    loader.assert_not_called()


def test_save_reopen_is_offline_and_keeps_source_details(example, tmp_path):
    pytest.importorskip("pyarrow")
    module, loader, dataset = example
    target = tmp_path / "shots"
    assert module["main"]([*OPTIONS, "--output-dir", str(target)]) == 0
    assert esd.open_dataset(target) == dataset
    loader.reset_mock()
    assert module["main"](["--open-dir", str(target)]) == 0
    loader.assert_not_called()


def test_partial_shot_failures_survive_saved_snapshot(example, tmp_path):
    pytest.importorskip("pyarrow")
    module, loader, dataset = example
    failed = replace(dataset, shot_records=(), metadata=replace(dataset.metadata, successful_tasks=("match:1",),
                                                              response_fetched_at=dataset.metadata.response_fetched_at[:1]),
                     errors=(esd.DatasetIssue("shots", "1", "SourceBlocked", "HTTP 403"),))
    loader.return_value = failed
    target = tmp_path / "partial"
    assert module["main"]([*OPTIONS, "--output-dir", str(target)]) == 1
    assert module["main"](["--open-dir", str(target)]) == 1
    assert esd.open_dataset(target) == failed


def test_scoped_identities_survive_every_comparison_example_reader(tmp_path):
    from datetime import datetime, timezone

    identities = esd.IdentityMap([esd.EntityAlias("player", "p", "espn", "001", team_id="010",
                                                 valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc))])
    path = tmp_path / "identities.json"
    path.write_text(json.dumps(identities.to_dict()), encoding="utf-8")
    for script, name in (("champions_event_comparison.py", "read_identities"), ("champions_player_comparison.py", "read_identities"),
                         ("champions_workflow.py", "read_identities"), ("champions_compare.py", "read_identities"),
                         ("champions_statistics.py", "read_aliases")):
        result = runpy.run_path(str(ROOT / script))[name](path)
        restored = result[1] if isinstance(result, tuple) else result
        assert restored.aliases == identities.aliases
