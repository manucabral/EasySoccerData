"""Artificial lineups, individual metrics and match totals from one response.

No source requests. --pandas and --parquet use their independent extras.
"""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import esd


def payload():
    return {"header": {"id": "1", "league": {"slug": "example.cup"}, "season": {"year": 2026},
                       "competitions": [{"id": "1", "date": "2026-11-03T20:00:00Z", "competitors": [
                           {"homeAway": "home", "team": {"id": "10"}}, {"homeAway": "away", "team": {"id": "20"}},
                       ]}]}, "rosters": [
                           {"team": {"id": "20"}, "homeAway": "away", "roster": [
                               {"athlete": {"id": "202", "displayName": "Away substitute"}, "starter": False},
                           ]},
                           {"team": {"id": "10"}, "homeAway": "home", "formation": "4-4-2", "roster": [
                               {"athlete": {"id": "101", "displayName": "Home starter"}, "starter": True,
                                "jersey": "01", "stats": [{"name": "totalGoals", "value": 0},
                                                           {"name": "totalShots", "value": 3}]},
                               {"athlete": {"id": "102", "displayName": "Role not reported"}},
                           ]},
                       ], "boxscore": {"teams": [{"team": {"id": "10"},
                                                   "statistics": [{"name": "totalShots", "displayValue": "12"}]}]}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pandas", action="store_true")
    parser.add_argument("--parquet", action="store_true")
    args = parser.parse_args(argv)
    with patch("esd._provider_datasets.get_api_json", side_effect=lambda *args, **kwargs: payload()) as fetch:
        dataset = esd.load_dataset(source="espn", league="example.cup", season=2026,
                                   tables=["lineups", "player_match_stats", "match_stats"],
                                   match_ids=[1], max_match_requests=1)
    assert fetch.call_count == 1 and dataset.complete and esd.validate_dataset(dataset).valid
    assert len(dataset.lineup_records) == 3 and len(dataset.player_match_stat_records) == 1
    assert [row.starter for row in dataset.lineup_records] == [False, True, None]
    assert dataset.player_match_stat_records[0].goals == 0
    assert dataset.player_match_stat_records[0].minutes is None
    assert dataset.match_stat_records[0].home_shots == 12
    print("Artificial dataset:", len(dataset.lineup_records), "listed players, one observed player-statistics row")
    for row in dataset.lineup_records:
        print(row.player_id, row.player_name, "| Starter:", row.starter, "| Confirmed:", row.confirmed)
    print("Player minutes stay unknown; reported goals stay zero")
    if args.parquet:
        with TemporaryDirectory(prefix="esd-match-players-") as directory:
            assert esd.open_dataset(dataset.save(Path(directory) / "snapshot")) == dataset
            print("Lineups, player metrics and match totals restored without HTTP")
    if args.pandas:
        assert str(dataset.lineups.starter.dtype) == "boolean"
        assert str(dataset.player_match_stats.goals.dtype) == "Int64"
        print(dataset.lineups[["match_id", "team_id", "player_id", "starter", "confirmed"]])
        print(dataset.player_match_stats[["player_id", "minutes", "goals", "shots"]])


if __name__ == "__main__":
    main()
