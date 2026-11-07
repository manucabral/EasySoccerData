"""Statistics CLI preflight, explicit selection and offline snapshot behavior."""

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
    payload = runpy.run_path(str(ROOT / "match_statistics_offline.py"))["payload"]
    fetch = Mock(side_effect=lambda *args, **kwargs: payload())
    monkeypatch.setattr(_provider_datasets, "get_api_json", fetch)
    return runpy.run_path(str(ROOT / "match_statistics.py")), fetch


def test_import_help_and_missing_selection_are_offline(example):
    module, fetch = example
    with pytest.raises(SystemExit) as exc:
        module["main"](["--help"])
    assert exc.value.code == 0
    with pytest.raises(SystemExit) as exc:
        module["main"]([])
    assert exc.value.code == 2
    fetch.assert_not_called()


def test_cli_uses_explicit_native_ids_without_a_calendar(example, capsys):
    module, fetch = example
    assert module["main"](OPTIONS + ["--max-match-requests", "1"]) == 0
    assert fetch.call_count == 1
    output = capsys.readouterr().out
    assert "Scope: match_ids" in output and "Shots: 12 4" in output


@pytest.mark.parametrize("extra,options", [("pyarrow", ["--output-dir", "new-stats"]), ("pandas", ["--pandas"])])
def test_optional_dependency_preflight_precedes_source_requests(example, extra, options):
    module, fetch = example
    module["main"].__globals__["find_spec"] = lambda name: None if name == extra else object()
    with pytest.raises(SystemExit) as exc:
        module["main"](OPTIONS + options)
    assert exc.value.code == 2
    fetch.assert_not_called()


def test_existing_destination_is_rejected_before_network(example, tmp_path):
    module, fetch = example
    with pytest.raises(SystemExit) as exc:
        module["main"](OPTIONS + ["--output-dir", str(tmp_path)])
    assert exc.value.code == 2
    fetch.assert_not_called()


def test_source_block_returns_partial_failure(example, capsys):
    module, fetch = example
    fetch.side_effect = esd.SourceBlocked("Example source block")
    assert module["main"](OPTIONS) == 1
    assert "SourceBlocked" in capsys.readouterr().err


def test_snapshot_reopens_without_discovery_or_http(example, tmp_path, capsys):
    pytest.importorskip("pyarrow")
    module, fetch = example
    destination = tmp_path / "stats"
    assert module["main"](OPTIONS + ["--output-dir", str(destination)]) == 0
    assert fetch.call_count == 1
    fetch.side_effect = AssertionError("Unexpected source request")
    assert module["main"](["--open-dir", str(destination)]) == 0
    assert fetch.call_count == 1
    assert "Saved and verified:" in capsys.readouterr().out


def test_offline_read_cannot_mix_download_filters(example):
    module, fetch = example
    with pytest.raises(SystemExit) as exc:
        module["main"](["--open-dir", "stats", "--match-id", "1"])
    assert exc.value.code == 2
    fetch.assert_not_called()
