"""Example CLI selections and exit codes, without contacting providers."""

import runpy
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

import esd

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def cli(monkeypatch):
    timestamp = datetime(2024, 8, 16, tzinfo=timezone.utc)
    dataset = esd.SoccerDataset(
        esd.DatasetMetadata(
            "espn",
            "eng.1",
            2024,
            ("matches",),
            timestamp,
            timestamp,
            expected_tasks=("example",),
            successful_tasks=("example",),
        )
    )
    fetch = Mock(return_value=dataset)
    monkeypatch.setattr(esd, "load_dataset", fetch)
    module = runpy.run_path(str(ROOT / "examples/datasets/providers.py"))

    def run(*args):
        monkeypatch.setattr(sys, "argv", ["providers.py", *args])
        return module["main"]()

    return run, fetch, dataset


def test_list_never_downloads(cli, capsys):
    run, fetch, _ = cli
    assert run("--list") == 0
    fetch.assert_not_called()
    assert "transfermarkt" in capsys.readouterr().out


def test_transfermarkt_table_override_drops_sample_clubs(cli):
    run, fetch, _ = cli
    assert (
        run(
            "--source",
            "transfermarkt",
            "--tables",
            "players",
            "--player-ids",
            "9",
            "--league",
            "GB1",
            "--season",
            "2025",
            "--preview",
            "2",
        )
        == 0
    )
    query = fetch.call_args.kwargs
    assert query["player_ids"] == [9] and query["season"] == 2025
    assert "club_ids" not in query and query["tables"] == ["players"]


def test_understat_player_stats_override_drops_sample_shots(cli):
    run, fetch, _ = cli
    assert run("--source", "understat", "--tables", "player_stats") == 0
    assert "match_ids" not in fetch.call_args.kwargs


def test_besoccer_standings_override_drops_sample_dates(cli):
    run, fetch, _ = cli
    assert run("--source", "besoccer", "--tables", "standings") == 0
    assert "start_date" not in fetch.call_args.kwargs
    assert "end_date" not in fetch.call_args.kwargs


def test_explicit_dates_native_season_and_cache_options_are_forwarded(cli):
    run, fetch, _ = cli
    assert (
        run(
            "--source",
            "scores365",
            "--league",
            "72",
            "--season-id",
            "228",
            "--start-date",
            "2024-08-16",
            "--end-date",
            "2024-08-17",
            "--cache-dir",
            "my-cache",
            "--refresh",
        )
        == 0
    )
    query = fetch.call_args.kwargs
    assert (query["league"], query["season_id"]) == ("72", 228)
    assert query["refresh"] and query["cache_dir"] == "my-cache"
    assert query["end_date"] == "2024-08-17"


@pytest.mark.parametrize("mode", ["raise", "collect"])
def test_partial_downloads_exit_one_and_show_errors(cli, mode, capsys):
    run, fetch, dataset = cli
    partial = replace(
        dataset, errors=(esd.DatasetIssue("matches", "example", "SourceBlocked", "Blocked"),)
    )
    if mode == "raise":
        fetch.side_effect = esd.DatasetLoadError(partial)
    else:
        fetch.return_value = partial
    assert run("--on-error", mode) == 1
    assert "SourceBlocked" in capsys.readouterr().out


def test_invalid_selection_exits_two_with_a_useful_message(cli, capsys):
    run, fetch, _ = cli
    fetch.side_effect = ValueError("Unsupported dataset table")
    with pytest.raises(SystemExit) as caught:
        run("--tables", "unsupported")
    assert caught.value.code == 2
    assert "Unsupported dataset table" in capsys.readouterr().err


def test_negative_preview_never_downloads(cli):
    run, fetch, _ = cli
    with pytest.raises(SystemExit) as caught:
        run("--preview", "-1")
    assert caught.value.code == 2
    fetch.assert_not_called()


def test_requested_snapshot_uses_the_callers_new_path(cli, monkeypatch, tmp_path):
    run, _, _ = cli
    save = Mock(return_value=tmp_path / "snapshot")
    monkeypatch.setattr(esd.SoccerDataset, "save", save)
    assert run("--output", str(tmp_path / "snapshot")) == 0
    save.assert_called_once_with(str(tmp_path / "snapshot"))
