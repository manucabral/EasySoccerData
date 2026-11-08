"""Artificial event comparisons with explicit identities and no source requests."""

import argparse
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import esd


def fixture():
    """Invented IDs and observations, including one ambiguous card and a shootout."""
    now = datetime(2026, 11, 3, 20, tzinfo=timezone.utc)
    pair, aliases = [], []
    for source, competition, match_id, home, away, player, period, shootout_period in (
        ("espn", "example.cup", "1", "10", "20", "101", "2", "5"),
        ("scores365", "72", "2", "30", "40", "201", "9", "11"),
    ):
        for kind, canonical, native in (("competition", "cup", competition), ("team", "home", home),
                                        ("team", "away", away), ("player", "scorer", player)):
            aliases.append(esd.EntityAlias(kind, canonical, source, native))
        task = f"match_details:{match_id}" if source == "espn" else f"match_events:{match_id}"
        goal = esd.NormalizedMatchEvent(source, match_id, event_id="g1" if source == "espn" else None,
                                        source_order=None if source == "espn" else 1, event_type="goal", team_id=away,
                                        player_id=player, source_period=period, minute=59 if source == "espn" else 60,
                                        is_shootout=False, added_minute=None if source == "espn" else 0)
        rows = [goal, replace(goal, event_id="c1" if source == "espn" else None, source_order=2,
                              event_type="yellow_card", minute=66),
                replace(goal, event_id="p1" if source == "espn" else None, source_order=3,
                        event_type="penalty_scored" if source == "espn" else "penalty_missed",
                        source_period=shootout_period, is_shootout=True, minute=None, added_minute=None),
                replace(goal, event_id="unknown" if source == "espn" else None, source_order=4, player_id=None),
                replace(goal, event_id="phase" if source == "espn" else None, source_order=5, event_type="other")]
        if source == "scores365":
            rows.append(replace(rows[1], source_order=6, minute=67))
        pair.append(esd.SoccerDataset(
            esd.DatasetMetadata(source, competition, 2026, ("matches", "match_events"), now, now,
                                expected_tasks=(task,), successful_tasks=(task,), response_fetched_at=((task, now.isoformat()),)),
            match_records=(esd.NormalizedMatch(source, match_id, competition_id=competition, kickoff=now,
                                               home_team_id=home, away_team_id=away),), match_event_records=tuple(rows),
        ))
    return pair, esd.IdentityMap(aliases)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pandas", action="store_true")
    parser.add_argument("--parquet", action="store_true")
    args = parser.parse_args(argv)
    pair, identities = fixture()
    report = esd.compare_match_events(*pair, identities=identities)
    assert len(report.differences) == 2 and len(report.unresolved) == 5
    assert report.differences[0].differences == ("minute",)
    assert "added_minute" in report.differences[0].unknown_fields
    print("Artificial events: minute difference, penalty outcome, ambiguous cards and unknown players")
    for row in report.rows:
        print(row.status, row.reason, "| Differences:", row.differences, "| Unknown:", row.unknown_fields)
    print("Excluded native phase records:", len(report.excluded_left), len(report.excluded_right))
    if args.parquet:
        with TemporaryDirectory(prefix="esd-event-comparison-") as directory:
            restored = [esd.open_dataset(item.save(Path(directory) / str(index))) for index, item in enumerate(pair)]
            assert esd.compare_match_events(*restored, identities=identities) == report
            print("Event comparison recomputed from snapshots without HTTP")
    if args.pandas:
        print(report.to_dataframe())


if __name__ == "__main__":
    main()
