"""Download ESPN/Sofascore attempts for explicit match IDs, or open a snapshot.

ESPN attempts are a partial feed with native field positions where reported and no inferred xG.
Sofascore retains native player coordinates and source xG/xGOT when supplied.
"""

import argparse
import sys
from importlib.util import find_spec
from pathlib import Path

import esd


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("espn", "sofascore"))
    parser.add_argument("--league")
    parser.add_argument("--season", type=int)
    parser.add_argument("--season-id", help="Required native Sofascore season ID")
    parser.add_argument("--match-id", action="append")
    parser.add_argument("--max-match-requests", type=int)
    parser.add_argument("--with-players", action="store_true")
    parser.add_argument("--with-events", action="store_true")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--pandas", action="store_true")
    parser.add_argument("--limit", type=int, default=30)
    storage = parser.add_mutually_exclusive_group()
    storage.add_argument("--output-dir", type=Path)
    storage.add_argument("--open-dir", type=Path)
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be positive")
    if args.open_dir is not None and (args.with_players or args.with_events or args.refresh or any(
        value is not None for value in (args.source, args.league, args.season, args.season_id,
                                       args.match_id, args.max_match_requests, args.cache_dir)
    )):
        parser.error("--open-dir cannot be combined with download options")
    if args.open_dir is None and any(value is None for value in (args.source, args.league, args.season, args.match_id)):
        parser.error("Download requires --source, --league, --season and --match-id")
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
            if "shots" not in dataset.metadata.tables:
                raise ValueError("Choose a snapshot containing shots")
        else:
            tables = ["shots"]
            if args.with_players:
                tables.append("player_match_stats")
            if args.with_events:
                tables.append("match_events")
            dataset = esd.load_dataset(
                source=args.source, league=args.league, season=args.season, season_id=args.season_id,
                tables=tables, match_ids=args.match_id,
                max_match_requests=args.max_match_requests if args.max_match_requests is not None else 20,
                cache_dir=args.cache_dir, refresh=args.refresh, on_error="collect",
            )
        report = esd.validate_dataset(dataset)
        print("Source:", dataset.metadata.source, "| Complete tasks:", dataset.complete, "| Observed attempts:", len(dataset.shot_records))
        print("A successful download does not establish a complete shot feed or equal coordinate/xG models")
        print("Cached tasks:", dataset.metadata.cached_tasks, "| Original fetches:", dataset.metadata.response_fetched_at)
        for row in dataset.shot_records[:args.limit]:
            print(row.match_id, row.shot_id, row.minute, row.result, "| Native player:", row.player_id,
                  "| Shootout:", row.is_shootout, "| Coordinates:", row.coordinate_system, row.x, row.y,
                  "| xG model:", row.xg_model, "| xG:", row.xg, "| xGOT:", row.xgot)
        for issue in dataset.errors:
            print(f"{issue.step} {issue.target}: {issue.error_type}: {issue.message}", file=sys.stderr)
        for issue in report.issues:
            print(f"{issue.severity}: {issue.code}: {issue.message}", file=sys.stderr)
        if not report.valid:
            return 1
        if args.output_dir is not None:
            path = dataset.save(args.output_dir)
            if esd.open_dataset(path) != dataset:
                raise esd.DatasetFormatError("Reopened shot snapshot differs from the download")
            print("Saved and verified:", path)
        if args.pandas:
            print(dataset.shots.head(args.limit))
        return 0 if dataset.complete else 1
    except (ValueError, OSError, ImportError) as exc:
        parser.error(str(exc))
    except esd.ESDException as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
