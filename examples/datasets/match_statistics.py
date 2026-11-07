"""Download statistics for explicit ESPN, 365Scores or Sofascore match IDs.

Base install downloads/validates records. --output-dir and --open-dir need
[parquet]. --pandas prints a DataFrame and requires [pandas].
"""

import argparse
import sys
from importlib.util import find_spec
from pathlib import Path

import esd


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("espn", "scores365", "sofascore"))
    parser.add_argument("--league", help="ESPN league slug or native competition ID")
    parser.add_argument("--season", type=int, help="ESPN native year or caller year label for other sources")
    parser.add_argument("--season-id", help="Native season ID, required for 365Scores and Sofascore")
    parser.add_argument("--match-id", action="append", help="Exact native match ID; repeat for more matches")
    parser.add_argument("--max-match-requests", type=int, help="Maximum endpoint reads before transport retries (default: 20)")
    parser.add_argument("--cache-dir", type=Path, help="Caller-selected response cache directory")
    parser.add_argument("--refresh", action="store_true", help="Fetch detail responses again")
    parser.add_argument("--pandas", action="store_true", help="Display the optional DataFrame")
    storage = parser.add_mutually_exclusive_group()
    storage.add_argument("--output-dir", type=Path, help="New Parquet snapshot directory")
    storage.add_argument("--open-dir", type=Path, help="Read a match-statistics snapshot without HTTP")
    args = parser.parse_args(argv)
    if args.open_dir is not None and (args.refresh or any(value is not None for value in (
        args.source, args.league, args.season, args.season_id, args.match_id, args.max_match_requests, args.cache_dir,
    ))):
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
            if "match_stats" not in dataset.metadata.tables:
                raise ValueError("Choose a snapshot containing match_stats")
        else:
            dataset = esd.load_dataset(
                source=args.source, league=args.league, season=args.season, season_id=args.season_id,
                tables=("match_stats",), match_ids=args.match_id,
                max_match_requests=args.max_match_requests if args.max_match_requests is not None else 20,
                on_error="collect", cache_dir=args.cache_dir, refresh=args.refresh,
            )
        report = esd.validate_dataset(dataset)
        print("Source:", dataset.metadata.source, "| Scope:", dataset.metadata.coverage_scope, "| Complete:", dataset.complete)
        print("Requested IDs:", ", ".join(dataset.metadata.requested_match_ids))
        print("Successful tasks:", len(dataset.metadata.successful_tasks), "| Cached:", len(dataset.metadata.cached_tasks))
        for row in dataset.match_stat_records:
            print(row.match_id, "| Shots:", row.home_shots, row.away_shots,
                  "| Possession (%):", row.home_possession_pct, row.away_possession_pct,
                  "| xG:", row.home_xg, row.away_xg, "| Source period:", row.source_period)
        for issue in dataset.errors:
            print(f"{issue.step} {issue.target}: {issue.error_type}: {issue.message}", file=sys.stderr)
        for issue in report.issues:
            print(f"{issue.severity}: {issue.code}: {issue.message}", file=sys.stderr)
        if not report.valid:
            return 1
        if args.output_dir is not None:
            path = dataset.save(args.output_dir)
            if esd.open_dataset(path) != dataset:
                raise esd.DatasetFormatError("Reopened statistics snapshot differs from the download")
            print("Saved and verified:", path)
        if args.pandas:
            print(dataset.match_stats)
        return 0 if dataset.complete else 1
    except (ValueError, OSError, ImportError) as exc:
        parser.error(str(exc))
    except esd.ESDException as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
