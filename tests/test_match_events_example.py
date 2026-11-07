"""Event CLI arguments, shared downloads and offline snapshots."""

import runpy
from pathlib import Path
from unittest.mock import Mock

import pytest

import esd
from esd import _provider_datasets

ROOT = Path(__file__).resolve().parent.parent / "examples/datasets"
OPTIONS = ["--source", "espn", "--league", "example.cup", "--season", "2026", "--match-id", "1"]


@pytest.fixture
def example(monkeypatch):
    payload = runpy.run_path(str(ROOT / "match_events_offline.py"))["payload"]
    fetch = Mock(return_value=payload("espn"))
    monkeypatch.setattr(_provider_datasets, "get_api_json", fetch)
    return runpy.run_path(str(ROOT / "match_events.py")), fetch


def test_cli_combined_detail_shares_one_read_and_shows_shootout(example, capsys):
    module, fetch = example
    assert module["main"](OPTIONS + ["--with-players", "--max-match-requests", "1"]) == 0
    assert fetch.call_count == 1 and "shootout 120'" in capsys.readouterr().out


@pytest.mark.parametrize("extra,options", [("pyarrow", ["--output-dir", "event-snapshot"]), ("pandas", ["--pandas"])])
def test_cli_extras_are_checked_before_http(example, extra, options):
    module, fetch = example
    module["main"].__globals__["find_spec"] = lambda name: None if name == extra else object()
    with pytest.raises(SystemExit) as exc:
        module["main"](OPTIONS + options)
    assert exc.value.code == 2
    fetch.assert_not_called()


@pytest.mark.parametrize("options", [[], ["--limit", "0"], ["--open-dir", "x", "--with-players"],
                                    ["--source", "sofascore"], ["--open-dir", "x", "--cache-dir", "x"]])
def test_cli_invalid_selection_is_offline(example, options):
    module, fetch = example
    with pytest.raises(SystemExit) as exc:
        module["main"](options)
    assert exc.value.code == 2
    fetch.assert_not_called()


def test_cli_existing_destination_is_rejected_before_http(example, tmp_path):
    module, fetch = example
    with pytest.raises(SystemExit) as exc:
        module["main"](OPTIONS + ["--output-dir", str(tmp_path)])
    assert exc.value.code == 2
    fetch.assert_not_called()


def test_cli_snapshot_reopens_without_http_and_rejects_other_tables(example, tmp_path):
    pytest.importorskip("pyarrow")
    module, fetch = example
    target = tmp_path / "events"
    assert module["main"](OPTIONS + ["--output-dir", str(target)]) == 0
    fetch.side_effect = AssertionError("Unexpected HTTP")
    assert module["main"](["--open-dir", str(target)]) == 0 and fetch.call_count == 1
    from dataclasses import replace
    dataset = esd.open_dataset(target)
    replace(dataset, metadata=replace(dataset.metadata, tables=("matches", "teams")), match_event_records=()).save(tmp_path / "no-events")
    with pytest.raises(SystemExit) as exc:
        module["main"](["--open-dir", str(tmp_path / "no-events")])
    assert exc.value.code == 2 and fetch.call_count == 1


def test_cli_missing_event_list_is_a_partial_source_failure(example):
    module, fetch = example
    fetch.return_value.pop("keyEvents")
    assert module["main"](OPTIONS) == 1


@pytest.mark.parametrize("code,failures,raises,calls", [(145, 1, False, 2), (145, 3, True, 3), (5, 1, True, 1)])
def test_event_example_cleanup_retries_only_bounded_directory_not_empty_errors(tmp_path, code, failures, raises, calls):
    module = runpy.run_path(str(ROOT / "match_events_offline.py"))
    namespace = module["workflow_directory"].__wrapped__.__globals__
    error = OSError("Simulated temporary-directory cleanup failure")
    error.winerror = code
    temporary = Mock()
    temporary.name = str(tmp_path)
    temporary.cleanup.side_effect = [*([error] * failures), None]
    namespace["TemporaryDirectory"] = Mock(return_value=temporary)
    pause = Mock()
    namespace["sleep"] = pause

    def run():
        with module["workflow_directory"]() as directory:
            assert directory == tmp_path

    if raises:
        with pytest.raises(OSError) as exc:
            run()
        assert exc.value is error
    else:
        run()
    assert temporary.cleanup.call_count == calls and pause.call_count == calls - 1
