"""Champions League selection, bounded downloads and record output without live HTTP."""

import runpy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

import esd
from esd.exceptions import SourceError

EXAMPLE = Path(__file__).resolve().parent.parent / "examples/datasets/champions_league.py"


def test_import_and_help_do_not_download(monkeypatch):
    fetch = Mock(side_effect=AssertionError("Unexpected download"))
    monkeypatch.setattr(esd, "load_dataset", fetch)
    module = runpy.run_path(str(EXAMPLE))
    with pytest.raises(SystemExit) as exc:
        module["main"](["--help"])
    assert exc.value.code == 0
    fetch.assert_not_called()


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ("2026-11-04", "2026-11-03"),
        ("2026-11-01", "2026-11-08"),
        ("2026-11-31", "2026-12-01"),
        ("2026-1-03", "2026-11-04"),
        ("invalid", "2026-11-04"),
    ],
)
def test_invalid_range_never_downloads(monkeypatch, start, end):
    fetch = Mock()
    monkeypatch.setattr(esd, "load_dataset", fetch)
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(EXAMPLE))["main"](["--start-date", start, "--end-date", end])
    assert exc.value.code == 2
    fetch.assert_not_called()


def test_seven_day_range_and_champions_selection(monkeypatch, capsys):
    now = datetime(2026, 11, 3, tzinfo=timezone.utc)
    dataset = esd.SoccerDataset(
        esd.DatasetMetadata(
            "scores365",
            "572",
            2026,
            ("matches", "teams"),
            now,
            now,
            expected_tasks=("sample",),
            successful_tasks=("sample",),
        ),
        match_records=(
            esd.NormalizedMatch(
                "scores365",
                match_id="001",
                kickoff=now,
                home_team_name="Home",
                away_team_name="Away",
                home_score=0,
                away_score=None,
            ),
        ),
    )
    fetch = Mock(return_value=dataset)
    monkeypatch.setattr(esd, "load_dataset", fetch)
    result = runpy.run_path(str(EXAMPLE))["main"](
        ["--start-date", "2026-11-01", "--end-date", "2026-11-07", "--season", "2026"]
    )
    assert result == 0
    fetch.assert_called_once_with(
        source="scores365",
        league=572,
        season=2026,
        start_date="2026-11-01",
        end_date="2026-11-07",
        tables=["matches"],
        on_error="collect",
        cache_dir=None,
        refresh=False,
    )
    output = capsys.readouterr().out
    assert "Home 0 - ? Away" in output
    assert "001 | 2026-11-03T00:00:00+00:00" in output


def test_failed_day_retains_successful_champions_records(monkeypatch, capsys):
    calls = []

    def fetch(url, **kwargs):
        calls.append(url)
        if "04/11/2026" in url:
            raise SourceError("Sample failed day")
        return {
            "games": [
                {
                    "id": 1,
                    "competitionId": 572,
                    "seasonNum": 2026,
                    "startTime": "2026-11-03T20:00:00Z",
                    "statusGroup": 4,
                    "homeCompetitor": {"id": 10, "name": "Home", "score": 0},
                    "awayCompetitor": {"id": 20, "name": "Away", "score": 1},
                },
                {"id": 2, "competitionId": 332},
            ]
        }

    monkeypatch.setattr("esd._provider_datasets.get_api_json", fetch)
    assert runpy.run_path(str(EXAMPLE))["main"]([]) == 1
    output = capsys.readouterr()
    assert len(calls) == 2
    assert "Complete: False | Matches: 1 | Teams: 2" in output.out
    assert "Home 0 - 1 Away" in output.out
    assert "matches 2026-11-04: SourceError: Sample failed day" in output.err


def test_empty_range_is_reported_without_error(monkeypatch, capsys):
    monkeypatch.setattr("esd._provider_datasets.get_api_json", lambda *a, **k: {"games": []})
    assert runpy.run_path(str(EXAMPLE))["main"]([]) == 0
    assert "No fixtures returned" in capsys.readouterr().out


def test_cache_recovers_failed_day_reuses_fetch_times_and_refreshes(monkeypatch, tmp_path, capsys):
    main = runpy.run_path(str(EXAMPLE))["main"]
    arguments = ["--cache-dir", str(tmp_path / "chosen-cache")]
    calls, datasets = [], []
    blocked = [True]
    score = [0]
    clock = [datetime(2026, 11, 7, tzinfo=timezone.utc).timestamp()]
    original_load = esd.load_dataset

    def load(**kwargs):
        dataset = original_load(**kwargs)
        datasets.append(dataset)
        return dataset

    def fetch(url, **kwargs):
        day = 4 if "04/11/2026" in url else 3
        calls.append(day)
        if day == 4 and blocked[0]:
            raise SourceError("Sample failed day")
        return {
            "games": [
                {
                    "id": day,
                    "competitionId": 572,
                    "seasonNum": 2026,
                    "startTime": f"2026-11-{day:02d}T20:00:00Z",
                    "statusGroup": 4,
                    "homeCompetitor": {"id": 10, "name": "Home", "score": score[0]},
                    "awayCompetitor": {"id": 20, "name": "Away", "score": 1},
                }
            ]
        }

    monkeypatch.setattr(esd, "load_dataset", load)
    monkeypatch.setattr("esd._provider_datasets.get_api_json", fetch)
    monkeypatch.setattr("esd._response_reader.time.time", lambda: clock[0])
    assert main(arguments) == 1
    assert calls == [3, 4]
    assert len(list((tmp_path / "chosen-cache").rglob("*.json"))) == 1
    first_times = dict(datasets[-1].metadata.response_fetched_at)

    blocked[0] = False
    clock[0] += 10
    assert main(arguments) == 0
    assert calls == [3, 4, 4]
    assert datasets[-1].metadata.cached_tasks == ("matches:2026-11-03",)
    resumed_times = dict(datasets[-1].metadata.response_fetched_at)
    assert resumed_times["matches:2026-11-03"] == first_times["matches:2026-11-03"]

    clock[0] += 10
    assert main(arguments) == 0
    assert calls == [3, 4, 4]
    assert len(datasets[-1].metadata.cached_tasks) == 2
    assert dict(datasets[-1].metadata.response_fetched_at) == resumed_times
    assert "Days reused from cache: 2" in capsys.readouterr().out

    score[0] = 2
    clock[0] += 10
    assert main([*arguments, "--refresh"]) == 0
    assert calls == [3, 4, 4, 3, 4]
    assert not datasets[-1].metadata.cached_tasks
    assert all(match.home_score == 2 for match in datasets[-1].match_records)
    assert dict(datasets[-1].metadata.response_fetched_at) != resumed_times


def test_cache_path_cannot_be_a_file(monkeypatch, tmp_path, capsys):
    destination = tmp_path / "existing-file"
    destination.write_text("Keep this file", encoding="utf-8")
    fetch = Mock(side_effect=AssertionError("Unexpected HTTP"))
    monkeypatch.setattr("esd._provider_datasets.get_api_json", fetch)
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(EXAMPLE))["main"](["--cache-dir", str(destination)])
    assert exc.value.code == 2
    assert "not a directory" in capsys.readouterr().err
    assert destination.read_text(encoding="utf-8") == "Keep this file"
    fetch.assert_not_called()
