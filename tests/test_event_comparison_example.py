"""Saved event comparisons recompute from sources and keep reviewed player aliases."""

import json
import runpy
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import Mock

import pytest

import esd

ROOT = Path(__file__).resolve().parent.parent / "examples/datasets"
OPTIONS = ["--espn-match-id", "1", "--scores365-match-id", "2", "--espn-season", "2026", "--year", "2026", "--season-id", "74"]


@pytest.fixture
def example(monkeypatch, tmp_path):
    pair, identities = runpy.run_path(str(ROOT / "compare_events_offline.py"))["fixture"]()
    pair = [replace(item, metadata=replace(item.metadata, league=league),
                    match_records=(replace(item.match_records[0], competition_id=league),))
            for item, league in zip(pair, ("uefa.champions", "572"))]
    aliases = [replace(alias, source_id="uefa.champions" if alias.source == "espn" else "572")
               if alias.kind == "competition" else alias for alias in identities.aliases]
    file = tmp_path / "aliases.json"
    file.write_text(json.dumps([asdict(alias) for alias in aliases]), encoding="utf-8")
    loader = Mock(side_effect=pair)
    monkeypatch.setattr(esd, "load_dataset", loader)
    module = runpy.run_path(str(ROOT / "champions_event_comparison.py"))
    return module, loader, [*OPTIONS, "--identities", str(file)], pair


def test_native_selectors_and_event_read_budgets_are_explicit(example, capsys):
    module, loader, options, _ = example
    assert module["main"](options) == 1
    assert loader.call_count == 2
    assert loader.call_args_list[0].kwargs["league"] == "uefa.champions"
    assert loader.call_args_list[1].kwargs["season_id"] == "74"
    assert all(call.kwargs["tables"] == ["match_events"] and call.kwargs["max_match_requests"] == 1 for call in loader.call_args_list)
    assert "Paired events: 2" in capsys.readouterr().out


@pytest.mark.parametrize("extra,flags", [("pandas", ["--pandas"]), ("pyarrow", ["--output-dir", "event-pair"])])
def test_missing_optional_dependencies_are_checked_before_http(example, extra, flags):
    module, loader, options, _ = example
    module["main"].__globals__["find_spec"] = lambda name: None if name == extra else object()
    with pytest.raises(SystemExit) as exc:
        module["main"](options + flags)
    assert exc.value.code == 2
    loader.assert_not_called()


@pytest.mark.parametrize("options", [[], ["--open-dir", "x", "--minute-tolerance", "0"],
                                    ["--open-dir", "x", "--refresh"], ["--limit", "0"],
                                    ["--minute-tolerance", "-1"], ["--kickoff-tolerance", "nan"],
                                    ["--espn-match-id", "0"]])
def test_invalid_arguments_are_offline(example, options):
    module, loader, _, _ = example
    with pytest.raises(SystemExit) as exc:
        module["main"](options)
    assert exc.value.code == 2
    loader.assert_not_called()


def test_snapshot_pair_recomputes_even_if_saved_report_is_replaced(example, tmp_path, capsys):
    pytest.importorskip("pyarrow")
    module, loader, options, _ = example
    target = tmp_path / "pair"
    assert module["main"](options + ["--output-dir", str(target), "--minute-tolerance", "0"]) == 1
    before = json.loads((target / "comparison.json").read_text(encoding="utf-8"))
    saved = esd.IdentityMap.from_dict(json.loads((target / "identities.json").read_text(encoding="utf-8")))
    assert before["minute_tolerance"] == 0 and any(alias.kind == "player" for alias in saved.aliases)
    (target / "comparison.json").write_text('{"invented_report": true}', encoding="utf-8")
    loader.side_effect = AssertionError("Offline pair attempted source access")
    assert module["main"](["--open-dir", str(target)]) == 1
    assert loader.call_count == 2
    assert "Unresolved:" in capsys.readouterr().out


def test_existing_snapshot_directory_is_not_overwritten(example, tmp_path):
    module, loader, options, _ = example
    with pytest.raises(SystemExit) as exc:
        module["main"](options + ["--output-dir", str(tmp_path)])
    assert exc.value.code == 2
    loader.assert_not_called()


def test_partial_source_errors_survive_snapshot_reopening(example, tmp_path):
    pytest.importorskip("pyarrow")
    module, loader, options, pair = example
    failed = replace(pair[1], match_event_records=(), metadata=replace(pair[1].metadata, successful_tasks=(), response_fetched_at=()),
                     errors=(esd.DatasetIssue("match_events", "2", "SourceBlocked", "Blocked source"),))
    loader.side_effect = [pair[0], failed]
    target = tmp_path / "partial"
    assert module["main"](options + ["--output-dir", str(target)]) == 1
    assert esd.open_dataset(target / "scores365").errors == failed.errors
    assert module["main"](["--open-dir", str(target)]) == 1


@pytest.mark.parametrize("raw", [{"format": "other"}, {"format": "easysoccerdata-event-comparison", "format_version": 99}])
def test_saved_comparison_options_reject_unknown_format(example, tmp_path, raw):
    module, _, _, _ = example
    path = tmp_path / "options.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError):
        module["read_options"](path)


def test_older_saved_options_without_unknown_period_policy_stay_strict(example, tmp_path):
    module, _, _, pair = example
    report = esd.compare_match_events(*pair)
    options = module["report_options"](report)
    del options["allow_unknown_period"]
    path = tmp_path / "options.json"
    path.write_text(json.dumps(options), encoding="utf-8")
    assert module["read_options"](path)["allow_unknown_period"] is False
