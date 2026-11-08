"""Artificial match events, shared detail reads and cache reuse without HTTP."""

import argparse
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from time import sleep
from unittest.mock import patch

import esd


@contextmanager
def workflow_directory():
    """Clean owned files, retrying Windows directory-not-empty errors twice."""
    temporary = TemporaryDirectory(prefix="esd-match-events-")
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


def payload(source):
    """Small invented responses exercising stoppage time and shootout counters."""
    if source == "espn":
        return {"header": {"id": "1", "league": {"slug": "example.cup"}, "season": {"year": 2026},
                           "competitions": [{"id": "1", "date": "2026-11-03T20:00:00Z", "competitors": [
                               {"homeAway": "home", "team": {"id": "10"}},
                               {"homeAway": "away", "team": {"id": "20"}},
                           ]}]}, "rosters": [{"team": {"id": "10"}, "roster": [
                               {"athlete": {"id": "101", "displayName": "Example player"}, "starter": True,
                                "stats": [{"name": "totalGoals", "value": 1}]},
                           ]}], "keyEvents": [
                               {"id": "goal-1", "type": {"id": "70"}, "period": {"number": 1},
                                "clock": {"value": 2700, "displayValue": "45'+2'"}, "team": {"id": "10"},
                                "participants": [{"athlete": {"id": "101", "displayName": "Example player"}}],
                                "shootout": False},
                           ], "commentary": [{"sequence": 20, "play": {
                               "id": "shootout-1", "type": {"id": "104"}, "period": {"number": 5},
                               "clock": {"value": 7200, "displayValue": "120'"},
                           }}]}
    if source == "sofascore":
        return {"incidents": [
            {"id": 1, "incidentType": "goal", "incidentClass": "regular", "time": 45, "addedTime": 2,
             "isHome": True, "player": {"id": 101, "name": "Example player"}, "rescinded": False},
            {"id": 2, "incidentType": "penaltyShootout", "incidentClass": "missed", "time": -1},
        ]}
    return {"game": {"id": 1, "competitionId": 72, "seasonNum": 228, "sportId": 1,
                     "startTime": "2026-11-03T20:00:00+00:00", "hasLineups": True,
                     "members": [{"id": 101, "athleteId": 777, "name": "Example player", "competitorId": 10}],
                     "homeCompetitor": {"id": 10, "lineups": {"members": [
                         {"id": 101, "status": 1, "stats": [{"type": 27, "value": 1}]}]}},
                     "awayCompetitor": {"id": 20, "lineups": {"members": []}},
                     "events": [
                         {"order": 1, "stageId": 7, "gameTime": 45, "addedTime": 2, "gameTimeDisplay": "45'",
                          "playerId": 101, "competitorId": 10, "eventType": {"id": 1, "subTypeId": 1}},
                         {"order": 2, "stageId": 11, "gameTime": 121, "gameTimeDisplay": "1",
                          "eventType": {"id": 6}},
                     ]}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pandas", action="store_true")
    parser.add_argument("--parquet", action="store_true")
    args = parser.parse_args(argv)
    with workflow_directory() as root:
        for source in ("espn", "scores365", "sofascore"):
            def fake_fetch(url, source=source, **options):
                if source != "sofascore":
                    return payload(source)
                if url.endswith("/incidents"):
                    return payload(source)
                if url.endswith("/lineups"):
                    return {"home": {"players": [
                        {"player": {"id": 101, "name": "Example player"}, "substitute": False,
                         "statistics": {"goals": 1}},
                    ]}, "away": {"players": []}}
                return {"event": {"id": 1, "season": {"id": 228}, "startTimestamp": 1793736000,
                                  "tournament": {"uniqueTournament": {"id": 72}},
                                  "homeTeam": {"id": 10}, "awayTeam": {"id": 20}}}

            reads = 3 if source == "sofascore" else 1
            options = {"source": source, "league": "example.cup" if source == "espn" else "72", "season": 2026,
                       "season_id": None if source == "espn" else 228, "match_ids": [1], "max_match_requests": reads,
                       "tables": ["match_events", "player_match_stats"], "cache_dir": root / source / "responses"}
            with patch("esd._provider_datasets.get_api_json", side_effect=fake_fetch) as fetch:
                dataset = esd.load_dataset(**options)
                cached = esd.load_dataset(**options)
            assert fetch.call_count == reads and dataset.complete and esd.validate_dataset(dataset).valid
            assert dataset.match_event_records == cached.match_event_records
            assert dataset.metadata.response_fetched_at == cached.metadata.response_fetched_at
            goal, penalty = dataset.match_event_records
            assert goal.minute == 45 and goal.added_minute == 2
            assert penalty.is_shootout and penalty.minute is None and penalty.player_id is None
            print("Artificial", source, ": 2 events,", reads, "endpoint reads, second query cached")
            print("Goal:", goal.minute, "+", goal.added_minute, "| Shootout minute:", penalty.minute)
            if args.parquet:
                assert esd.open_dataset(dataset.save(root / source / "snapshot")) == dataset
                print("Events and players restored from Parquet without HTTP")
            if args.pandas:
                assert str(dataset.match_events.is_shootout.dtype) == "boolean"
                print(dataset.match_events[["match_id", "minute", "added_minute", "is_shootout", "player_id"]])


if __name__ == "__main__":
    main()
