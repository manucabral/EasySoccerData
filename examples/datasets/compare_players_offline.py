"""Artificial player comparisons without HTTP. Extras enable frames or snapshots."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import esd


def fixture():
    now = datetime(2026, 11, 3, 20, tzinfo=timezone.utc)
    pair, aliases = [], []
    for source, identifier, competition, home, away, players in (
        ("espn", "1", "example.cup", "10", "20", ("101", "102", "103", "104", "105")),
        ("scores365", "2", "72", "30", "40", ("201", "202", "203", "204")),
    ):
        task = f"{'match_details' if source == 'espn' else 'lineups'}:{identifier}"
        lineups = tuple(esd.NormalizedLineup(source, identifier, away, player, home_away="away",
                                             starter=(source == "espn") if i == 0 else False,
                                             position="MID", jersey_number=f"0{i + 1}")
                        for i, player in enumerate(players))
        statistics = (esd.NormalizedPlayerMatchStats(source, identifier, away, players[0], goals=1,
                                                     shots=3 if source == "espn" else 4,
                                                     minutes=None if source == "espn" else 90, xg=0.5),)
        pair.append(esd.SoccerDataset(
            esd.DatasetMetadata(source, competition, 2026, ("matches", "lineups", "player_match_stats"), now, now,
                                expected_tasks=(task,), successful_tasks=(task,), response_fetched_at=((task, now.isoformat()),)),
            match_records=(esd.NormalizedMatch(source, identifier, competition_id=competition,
                                               home_team_id=home, away_team_id=away, kickoff=now),),
            lineup_records=lineups, player_match_stat_records=statistics,
        ))
        aliases.extend(esd.EntityAlias(kind, canonical, source, native) for kind, canonical, native in (
            ("competition", "cup", competition), ("team", "home", home), ("team", "away", away),
            ("player", "scorer", players[0]), ("player", "unused", players[1]),
        ))
        aliases.extend(esd.EntityAlias("player", "ambiguous", source, native) for native in players[3:])
    return tuple(pair), esd.IdentityMap(aliases)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pandas", action="store_true")
    parser.add_argument("--parquet", action="store_true")
    args = parser.parse_args(argv)
    pair, identities = fixture()
    options = {"identities": identities, "metrics": ["goals", "shots", "minutes", "xg"]}
    report = esd.compare_match_players(*pair, **options)
    assert len(report.differences) == 1 and len(report.unresolved) == 5
    assert len(report.statistic_differences) == 1
    assert sum(row.left_lineup is not None for row in report.rows) == len(pair[0].lineup_records)
    assert sum(row.right_lineup is not None for row in report.rows) == len(pair[1].lineup_records)
    print("Artificial comparison: 2 paired players, 5 unresolved observations")
    for row in report.rows:
        print(row.status, row.reason, "| Differences:", row.differences, "| Unknown:", row.unknown_fields)
    for row in report.statistics[:8]:
        print(row.metric, row.left_value, row.right_value, row.status, "| Delta:", row.delta)
    if args.parquet:
        with TemporaryDirectory(prefix="esd-compare-players-") as directory:
            restored = tuple(esd.open_dataset(item.save(Path(directory) / item.metadata.source)) for item in pair)
            assert esd.compare_match_players(*restored, **options) == report
            print("Source snapshots reproduce the comparison without HTTP or pandas")
    if args.pandas:
        print(report.to_dataframe())
        print(report.to_dataframe("statistics").head(8))


if __name__ == "__main__":
    main()
