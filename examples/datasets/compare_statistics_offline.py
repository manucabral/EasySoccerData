"""Compare artificial ESPN/365Scores observations without source requests.

--pandas requires [pandas]. --parquet saves/reopens temporary source snapshots
with [parquet], then reproduces the same report without pandas or HTTP.
"""

import argparse
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import esd


def example_pair():
    """Artificial native IDs and values, unrelated to real teams or matches."""
    now = datetime(2026, 11, 3, 20, tzinfo=timezone.utc)
    datasets, aliases = [], []
    for source, match, competition, home, away, period, shots, possession in (
        ("espn", "1", "example.cup", "10", "20", "boxscore", 12, 51.5),
        ("scores365", "2", "72", "30", "40", "-1", 13, 51.6),
    ):
        task = f"match_stats:{match}"
        datasets.append(esd.SoccerDataset(
            esd.DatasetMetadata(source, competition, 2026, ("matches", "match_stats"), now, now,
                                expected_tasks=(task,), successful_tasks=(task,),
                                response_fetched_at=((task, now.isoformat()),)),
            match_records=(esd.NormalizedMatch(source, match_id=match, competition_id=competition,
                                               home_team_id=home, away_team_id=away, kickoff=now),),
            match_stat_records=(esd.NormalizedMatchStats(
                source, match_id=match, source_period=period, home_shots=shots,
                home_possession_pct=possession, home_red_cards=0, home_xg=1.2),),
        ))
        aliases.extend(esd.EntityAlias(kind, canonical, source, native)
                       for kind, canonical, native in (("competition", "cup", competition),
                                                       ("team", "home", home), ("team", "away", away)))
    return datasets, esd.IdentityMap(aliases)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pandas", action="store_true")
    parser.add_argument("--parquet", action="store_true")
    args = parser.parse_args(argv)
    pair, identities = example_pair()
    options = {"identities": identities,
               "metrics": ["home_shots", "home_possession_pct", "home_red_cards", "away_red_cards", "home_xg"],
               "tolerances": {"home_possession_pct": 0.1}}
    report = esd.compare_match_statistics(*pair, **options)
    assert len(report.linkage.links) == 1 and len(report.differences) == 1
    for row in report.rows:
        print(row.metric, row.left_value, row.right_value, "|", row.status, "| delta:", row.delta, row.unit)
    assert report.rows[2].left_value == 0 and report.rows[3].left_value is None
    assert report.rows[4].status == "source_specific" and report.rows[4].delta is None
    if args.parquet:
        with TemporaryDirectory(prefix="esd-statistics-comparison-") as directory:
            reopened = [esd.open_dataset(item.save(Path(directory) / item.metadata.source)) for item in pair]
            assert esd.compare_match_statistics(*reopened, **options) == report
            print("Source snapshots reproduce the report without HTTP")
    if args.pandas:
        print(report.to_dataframe())


if __name__ == "__main__":
    main()
