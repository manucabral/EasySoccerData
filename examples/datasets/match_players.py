"""Download normalized lineups/player-match statistics for explicit native IDs.

Base installation reads records. --pandas needs [pandas]; snapshot save/open
needs [parquet]. --with-match-stats also selects the existing team totals.
"""

import argparse
import sys
from importlib.util import find_spec
from pathlib import Path

import esd


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("espn", "scores365", "sofascore"))
    parser.add_argument("--league", help="Native ESPN league slug or numeric competition ID")
    parser.add_argument("--season", type=int)
    parser.add_argument("--season-id", help="Native season ID required for 365Scores/Sofascore")
    parser.add_argument("--match-id", action="append", help="Repeat for more native match IDs")
    parser.add_argument("--max-match-requests", type=int, help="Maximum endpoint reads before retries, default 20")
    parser.add_argument("--lineups-only", action="store_true", help="Skip parsing individual metrics")
    parser.add_argument("--with-match-stats", action="store_true", help="Also request team match totals")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--pandas", action="store_true")
    parser.add_argument("--limit", type=int, default=5, help="Maximum preview rows per table, default 5")
    storage = parser.add_mutually_exclusive_group()
    storage.add_argument("--output-dir", type=Path, help="New Parquet snapshot directory")
    storage.add_argument("--open-dir", type=Path, help="Read a saved lineup dataset without HTTP")
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be positive")
    if args.open_dir is not None and (args.refresh or args.lineups_only or args.with_match_stats or any(
        value is not None for value in (args.source, args.league, args.season, args.season_id,
                                       args.match_id, args.max_match_requests, args.cache_dir)
    )):
        parser.error("--open-dir cannot be combined with download options")
    if args.open_dir is None and any(value is None for value in (args.source, args.league, args.season, args.match_id)):
        parser.error("Download requires --source, --league, --season and at least one --match-id")
    try:
        if args.output_dir is not None:
            args.output_dir = args.output_dir.expanduser()
            if args.output_dir.exists() or args.output_dir.is_symlink():
                raise FileExistsError(f"Snapshot destination already exists: {args.output_dir}")
        if (args.output_dir is not None or args.open_dir is not None) and find_spec("pyarrow") is None:
            raise ImportError("Snapshot storage requires EasySoccerData[parquet]")
        if args.pandas and find_spec("pandas") is None:
            raise ImportError("DataFrame display requires EasySoccerData[pandas]")
        if args.open_dir is not None:
            dataset = esd.open_dataset(args.open_dir.expanduser())
            if "lineups" not in dataset.metadata.tables:
                raise ValueError("Choose a snapshot containing lineups")
        else:
            tables = ["lineups"] if args.lineups_only else ["lineups", "player_match_stats"]
            if args.with_match_stats:
                tables.append("match_stats")
            dataset = esd.load_dataset(
                source=args.source, league=args.league, season=args.season, season_id=args.season_id,
                tables=tables, match_ids=args.match_id,
                max_match_requests=args.max_match_requests if args.max_match_requests is not None else 20,
                cache_dir=args.cache_dir, refresh=args.refresh, on_error="collect",
            )
        report = esd.validate_dataset(dataset)
        print("Source:", dataset.metadata.source, "| Complete:", dataset.complete, "| Scope:", dataset.metadata.coverage_scope)
        print("Matches:", len(dataset.match_records), "| Listed players:", len(dataset.lineup_records),
              "| Player statistic rows:", len(dataset.player_match_stat_records))
        print("Successful tasks:", dataset.metadata.successful_tasks, "| Cached:", dataset.metadata.cached_tasks)
        print("Original fetches:", dataset.metadata.response_fetched_at)
        for row in dataset.lineup_records[:args.limit]:
            print("Lineup:", row.match_id, row.team_id, row.player_id, row.player_name,
                  "| Starter:", row.starter, "| Confirmed:", row.confirmed, "| Formation:", row.formation,
                  "| Athlete ID:", row.source_athlete_id)
        for row in dataset.player_match_stat_records[:args.limit]:
            print("Player stats:", row.match_id, row.team_id, row.player_id, "| Minutes:", row.minutes,
                  "| Goals:", row.goals, "| Assists:", row.assists, "| xG:", row.xg)
        for row in dataset.match_stat_records[:args.limit]:
            print("Match totals:", row.match_id, "| Shots:", row.home_shots, row.away_shots)
        for issue in dataset.errors:
            print(f"{issue.step} {issue.target}: {issue.error_type}: {issue.message}", file=sys.stderr)
        for issue in report.issues:
            print(f"{issue.severity}: {issue.code}: {issue.message}", file=sys.stderr)
        if not report.valid:
            return 1
        if args.output_dir is not None:
            path = dataset.save(args.output_dir)
            if esd.open_dataset(path) != dataset:
                raise esd.DatasetFormatError("Reopened lineup snapshot differs from the download")
            print("Saved and verified:", path)
        if args.pandas:
            print(dataset.lineups.head(args.limit))
            if "player_match_stats" in dataset.metadata.tables:
                print(dataset.player_match_stats.head(args.limit))
        return 0 if dataset.complete else 1
    except (ValueError, OSError, ImportError) as exc:
        parser.error(str(exc))
    except esd.ESDException as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
