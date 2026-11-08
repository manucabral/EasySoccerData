"""Read explicit Champions League fixture IDs from ESPN, 365Scores and Sofascore.

Native IDs and season selectors must be supplied for each provider. Base records
need no extra. --output-dir needs [parquet]; --pandas independently needs [pandas].
"""

import argparse
import sys
from importlib.util import find_spec
from pathlib import Path

import esd


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for source in ("espn", "scores365", "sofascore"):
        parser.add_argument(f"--{source}-match-id", type=int, required=True)
    parser.add_argument("--espn-season", type=int, required=True, help="Native ESPN selector year")
    parser.add_argument("--year", type=int, required=True, help="Caller year label for 365Scores/Sofascore")
    parser.add_argument("--scores365-season-id", type=int, required=True)
    parser.add_argument("--sofascore-season-id", type=int, required=True)
    parser.add_argument("--max-match-requests", type=int, default=4, help="Total endpoint-read budget, default 4")
    parser.add_argument("--with-players", action="store_true")
    parser.add_argument("--with-match-stats", action="store_true")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--output-dir", type=Path, help="New directory, with one Parquet snapshot per source")
    parser.add_argument("--pandas", action="store_true")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args(argv)
    if any(value < 1 for value in (args.espn_match_id, args.scores365_match_id, args.sofascore_match_id,
                                  args.scores365_season_id, args.sofascore_season_id, args.limit)):
        parser.error("Native IDs and --limit must be positive")
    if not all(1000 <= value <= 9999 for value in (args.espn_season, args.year)):
        parser.error("Season years must have four digits")
    costs = {"espn": 1, "scores365": 1 + int(args.with_match_stats),
             "sofascore": 2 + int(args.with_players) + int(args.with_match_stats)}
    if args.max_match_requests < sum(costs.values()):
        parser.error(f"Selection needs {sum(costs.values())} endpoint reads, exceeding --max-match-requests")
    try:
        if args.output_dir is not None:
            args.output_dir = args.output_dir.expanduser()
            if args.output_dir.exists() or args.output_dir.is_symlink():
                raise FileExistsError(f"Snapshot destination already exists: {args.output_dir}")
            if find_spec("pyarrow") is None:
                raise ImportError("Snapshot storage requires EasySoccerData[parquet]")
        if args.pandas and find_spec("pandas") is None:
            raise ImportError("DataFrame display requires EasySoccerData[pandas]")
        tables = ["match_events"]
        if args.with_players:
            tables.append("player_match_stats")
        if args.with_match_stats:
            tables.append("match_stats")
        datasets = []
        for source, league, year, season_id, identifier in (
            ("espn", "uefa.champions", args.espn_season, None, args.espn_match_id),
            ("scores365", "572", args.year, args.scores365_season_id, args.scores365_match_id),
            ("sofascore", "7", args.year, args.sofascore_season_id, args.sofascore_match_id),
        ):
            dataset = esd.load_dataset(
                source=source, league=league, season=year, season_id=season_id, match_ids=[identifier],
                tables=tables, max_match_requests=costs[source], cache_dir=args.cache_dir,
                refresh=args.refresh, on_error="collect",
            )
            report = esd.validate_dataset(dataset)
            print(source, "| Complete:", dataset.complete, "| Events:", len(dataset.match_event_records))
            for match in dataset.match_records:
                print("Native match:", match.match_id, "| Kickoff UTC:", match.kickoff,
                      "| Native teams:", match.home_team_id, match.away_team_id)
            print("Original fetches:", dataset.metadata.response_fetched_at)
            print("Cached tasks:", dataset.metadata.cached_tasks)
            for row in dataset.match_event_records[:args.limit]:
                print(row.event_id, row.event_type, "| Minute:", row.minute, "| Added:", row.added_minute,
                      "| Shootout:", row.is_shootout, "| Rescinded:", row.rescinded, "| Player:", row.player_id)
            for issue in dataset.errors:
                print(f"{source} {issue.step}: {issue.error_type}: {issue.message}", file=sys.stderr)
            for issue in report.issues:
                print(f"{source} {issue.severity}: {issue.code}: {issue.message}", file=sys.stderr)
            datasets.append((dataset, report))
        if not all(report.valid for _, report in datasets):
            return 1
        if args.output_dir is not None:
            args.output_dir.mkdir(parents=True, exist_ok=False)
            for dataset, _ in datasets:
                target = dataset.save(args.output_dir / dataset.metadata.source)
                if esd.open_dataset(target) != dataset:
                    raise esd.DatasetFormatError("Reopened event snapshot differs from the download")
                print("Saved and verified:", target)
        if args.pandas:
            for dataset, _ in datasets:
                print(dataset.metadata.source, dataset.match_events.head(args.limit))
        return 0 if all(dataset.complete for dataset, _ in datasets) else 1
    except (ValueError, OSError, ImportError) as exc:
        parser.error(str(exc))
    except esd.ESDException as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
