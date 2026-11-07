"""Artificial ESPN totals with nullable metrics and an explicit request budget.

No source requests. --parquet uses temporary storage; --pandas displays a frame.
"""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import esd


def payload():
    """Artificial response with away-first statistics and no inferred metric values."""
    return {"header": {"id": "1", "league": {"slug": "example.cup"}, "season": {"year": 2026},
                       "competitions": [{"id": "1", "date": "2026-11-03T20:00:00Z", "competitors": [
                           {"homeAway": "home", "team": {"id": "10", "displayName": "Home"}},
                           {"homeAway": "away", "team": {"id": "20", "displayName": "Away"}},
                       ]}]}, "boxscore": {"teams": [
                           {"team": {"id": "20"}, "statistics": [{"name": "totalShots", "displayValue": "4"}]},
                           {"team": {"id": "10"}, "statistics": [{"name": "totalShots", "displayValue": "12"},
                                                                    {"name": "redCards", "displayValue": "0"}]},
                       ]}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parquet", action="store_true", help="Save/reopen a temporary snapshot with [parquet]")
    parser.add_argument("--pandas", action="store_true", help="Display nullable columns with [pandas]")
    args = parser.parse_args(argv)
    with patch("esd._provider_datasets.get_api_json", return_value=payload()) as fetch:
        dataset = esd.load_dataset(source="espn", league="example.cup", season=2026,
                                   tables=("match_stats",), match_ids=[1], max_match_requests=1)
    assert fetch.call_count == 1 and dataset.complete and esd.validate_dataset(dataset).valid
    row = dataset.match_stat_records[0]
    assert (row.home_shots, row.away_shots) == (12, 4)
    assert row.home_red_cards == 0 and row.away_red_cards is None
    print("Artificial match totals:", row)
    if args.parquet:
        with TemporaryDirectory(prefix="esd-match-statistics-") as directory:
            assert esd.open_dataset(dataset.save(Path(directory) / "snapshot")) == dataset
            print("Statistics, source scope and request coverage restored without HTTP")
    if args.pandas:
        frame = dataset.match_stats
        assert str(frame.home_shots.dtype) == "Int64"
        assert frame.away_red_cards.isna().all()
        print(frame[["match_id", "home_shots", "away_shots", "home_red_cards", "away_red_cards"]])


if __name__ == "__main__":
    main()
