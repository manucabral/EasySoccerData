"""Lineup CLI preflight, combined downloads and offline snapshots."""

import runpy
from pathlib import Path
from unittest.mock import Mock

import pytest

from esd import _provider_datasets

ROOT = Path(__file__).resolve().parent.parent / "examples/datasets"
OPTIONS = ["--source", "espn", "--league", "example.cup", "--season", "2026", "--match-id", "1"]


@pytest.fixture
def example(monkeypatch):
    payload = runpy.run_path(str(ROOT / "match_players_offline.py"))["payload"]
    fetch = Mock(side_effect=lambda *args, **kwargs: payload())
    monkeypatch.setattr(_provider_datasets, "get_api_json", fetch)
    return runpy.run_path(str(ROOT / "match_players.py")), fetch


def test_combined_cli_fetches_one_summary_and_prints_player_and_match_records(example, capsys):
    module, fetch = example
    assert module["main"](OPTIONS + ["--with-match-stats", "--max-match-requests", "1"]) == 0
    assert fetch.call_count == 1
    output = capsys.readouterr().out
    assert "Listed players: 3 | Player statistic rows: 1" in output and "Match totals:" in output


@pytest.mark.parametrize("extra,options", [("pyarrow", ["--output-dir", "new-lineups"]), ("pandas", ["--pandas"])])
def test_optional_extras_are_checked_before_requests(example, extra, options):
    module, fetch = example
    module["main"].__globals__["find_spec"] = lambda name: None if name == extra else object()
    with pytest.raises(SystemExit) as exc:
        module["main"](OPTIONS + options)
    assert exc.value.code == 2
    fetch.assert_not_called()


@pytest.mark.parametrize("options", [[], ["--limit", "0"], ["--open-dir", "x", "--lineups-only"]])
def test_invalid_cli_selection_is_offline(example, options):
    module, fetch = example
    with pytest.raises(SystemExit) as exc:
        module["main"](options)
    assert exc.value.code == 2
    fetch.assert_not_called()


def test_existing_destination_is_rejected_before_requests(example, tmp_path):
    module, fetch = example
    with pytest.raises(SystemExit) as exc:
        module["main"](OPTIONS + ["--output-dir", str(tmp_path)])
    assert exc.value.code == 2
    fetch.assert_not_called()


def test_snapshot_reopens_without_http_and_retains_unknown_flags(example, tmp_path, capsys):
    pytest.importorskip("pyarrow")
    module, fetch = example
    assert module["main"](OPTIONS + ["--output-dir", str(tmp_path / "players")]) == 0
    fetch.side_effect = AssertionError("Unexpected source request")
    assert module["main"](["--open-dir", str(tmp_path / "players")]) == 0
    assert fetch.call_count == 1 and "Confirmed: None" in capsys.readouterr().out
