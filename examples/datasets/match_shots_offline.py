"""Artificial attempts, native coordinates and cached detail reads without HTTP."""

import argparse
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from time import sleep
from unittest.mock import patch

import esd


@contextmanager
def workflow_directory():
    temporary = TemporaryDirectory(prefix="esd-match-shots-")
    try:
        yield Path(temporary.name)
    finally:
        for attempt in range(3):
            try:
                temporary.cleanup()
            except OSError as exc:
                if getattr(exc, "winerror", None) != 145 or attempt == 2:
                    raise
                sleep(0.05 * (attempt + 1))
            else:
                break


def payloads():
    """Invented responses, not observations from a real fixture."""
    espn = {"header": {"id": "1", "league": {"slug": "example.cup"}, "season": {"year": 2026},
                       "competitions": [{"id": "1", "date": "2026-11-03T20:00:00Z", "competitors": [
                           {"homeAway": "home", "team": {"id": "10"}}, {"homeAway": "away", "team": {"id": "20"}},
                       ]}]}, "keyEvents": [], "commentary": [
                           {"play": {"id": "attempt-1", "type": {"id": "106", "text": "Shot On Target"},
                                     "team": {"id": "10"}, "clock": {"displayValue": "45'+2'"},
                                     "participants": [{"athlete": {"id": "101"}}],
                                     "fieldPositionX": 80.9, "fieldPositionY": 67.8}}
                       ]}
    event = {"event": {"id": 1, "season": {"id": 228}, "startTimestamp": 1793736000,
                        "tournament": {"uniqueTournament": {"id": 72}, "name": "Example cup"},
                        "homeTeam": {"id": 10, "name": "Home"}, "awayTeam": {"id": 20, "name": "Away"},
                        "status": {"type": "finished", "description": "Ended"},
                        "homeScore": {"current": 0}, "awayScore": {"current": 0}}}
    shotmap = {"shotmap": [
        {"id": 1, "player": {"id": 101}, "isHome": True, "time": 45, "addedTime": 2,
         "shotType": "save", "playerCoordinates": {"x": 87.2, "y": 39.1, "z": 0},
         "xg": 0.0, "xgot": 0.1, "bodyPart": "right-foot"},
        {"shotType": "miss", "time": -1},
    ]}
    return espn, event, shotmap


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pandas", action="store_true")
    parser.add_argument("--parquet", action="store_true")
    args = parser.parse_args(argv)
    espn, event, shotmap = payloads()
    with workflow_directory() as directory:
        for source, responses, reads in (("espn", [espn], 1), ("sofascore", [event, shotmap], 2)):
            options = {"source": source, "league": "example.cup" if source == "espn" else 72,
                       "season": 2026, "season_id": None if source == "espn" else 228,
                       "tables": ["shots"], "match_ids": [1], "max_match_requests": reads,
                       "cache_dir": directory / source / "responses", "request_delay": 0}
            with patch("esd._provider_datasets.get_api_json", side_effect=responses) as fetch:
                dataset = esd.load_dataset(**options)
                cached = esd.load_dataset(**options)
            assert fetch.call_count == reads and dataset.complete and esd.validate_dataset(dataset).valid
            assert dataset.shot_records == cached.shot_records
            assert dataset.metadata.response_fetched_at == cached.metadata.response_fetched_at
            assert cached.metadata.cached_tasks == cached.metadata.expected_tasks
            first = dataset.shot_records[0]
            assert first.minute == 45 and first.added_minute == 2
            if source == "espn":
                assert first.coordinate_system == "espn-native-field" and first.x == 80.9 and first.y == 67.8
                assert first.xg_model is None and first.xg is None
            else:
                assert first.xg == 0.0 and first.xgot == 0.1 and first.xg_model == "sofascore"
                assert first.x == 87.2 and first.coordinate_system == "sofascore-native-player"
                assert dataset.shot_records[1].team_id is None and dataset.shot_records[1].is_shootout is None
            print("Artificial", source, ":", len(dataset.shot_records), "attempts,", reads, "reads, second query cached")
            if args.parquet:
                assert esd.open_dataset(dataset.save(directory / source / "snapshot")) == dataset
                print("Native attempts restored without HTTP or pandas")
            if args.pandas:
                assert str(dataset.shots.is_shootout.dtype) == "boolean"
                assert str(dataset.shots.xgot.dtype) == "Float64"
                print(dataset.shots[["shot_id", "coordinate_system", "x", "y", "xg", "xgot", "xg_model"]])


if __name__ == "__main__":
    main()
