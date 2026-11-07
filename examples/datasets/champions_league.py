"""Download up to seven UTC days of UEFA Champions League matches from 365Scores.

Downloads use the base installation. --cache-dir stores source responses.
--output-dir saves Parquet and --open-dir reads it offline, both requiring [parquet].
"""

import argparse
import sys
from datetime import datetime
from importlib.util import find_spec
from pathlib import Path

import esd

CHAMPIONS_LEAGUE_ID = 572


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", help="First UTC day, YYYY-MM-DD (default: 2026-11-03)")
    parser.add_argument("--end-date", help="Last UTC day, inclusive (default: 2026-11-04)")
    parser.add_argument(
        "--season", type=int, help="Caller year label (default: 2026); dates select matches"
    )
    parser.add_argument("--cache-dir", type=Path, help="Directory for persistent source responses")
    parser.add_argument(
        "--refresh", action="store_true", help="Fetch again instead of reusing cache"
    )
    storage = parser.add_mutually_exclusive_group()
    storage.add_argument("--output-dir", type=Path, help="New Parquet snapshot directory")
    storage.add_argument("--open-dir", type=Path, help="Read a Parquet snapshot without network access")
    args = parser.parse_args(argv)
    if args.open_dir is not None and (
        args.start_date is not None or args.end_date is not None or args.season is not None
        or args.cache_dir is not None or args.refresh
    ):
        parser.error("--open-dir cannot be combined with download options")
    try:
        if args.output_dir is not None:
            args.output_dir = args.output_dir.expanduser()
            if args.output_dir.exists() or args.output_dir.is_symlink():
                raise FileExistsError(f"Dataset destination already exists: {args.output_dir}")
        if (args.output_dir is not None or args.open_dir is not None) and find_spec("pyarrow") is None:
            raise ImportError('Parquet requires PyArrow. Install it with python -m pip install -e ".[parquet]".')
        if args.open_dir is not None:
            args.open_dir = args.open_dir.expanduser()
            dataset = esd.open_dataset(args.open_dir)
            if (
                dataset.metadata.source != "scores365"
                or dataset.metadata.league != str(CHAMPIONS_LEAGUE_ID)
                or "matches" not in dataset.metadata.tables
            ):
                raise ValueError("Choose a 365Scores Champions League matches snapshot")
        else:
            args.start_date = args.start_date if args.start_date is not None else "2026-11-03"
            args.end_date = args.end_date if args.end_date is not None else "2026-11-04"
            start = datetime.strptime(args.start_date, "%Y-%m-%d").date()
            end = datetime.strptime(args.end_date, "%Y-%m-%d").date()
            if start.isoformat() != args.start_date or end.isoformat() != args.end_date:
                raise ValueError("Dates must use YYYY-MM-DD")
            if not 0 <= (end - start).days <= 6:
                raise ValueError("Choose an ordered range of one to seven days")
            dataset = esd.load_dataset(
                source="scores365",
                league=CHAMPIONS_LEAGUE_ID,
                season=args.season if args.season is not None else 2026,
                start_date=args.start_date,
                end_date=args.end_date,
                tables=["matches"],
                on_error="collect",
                cache_dir=args.cache_dir,
                refresh=args.refresh,
            )
    except (ValueError, OSError, ImportError, esd.CacheError, esd.DatasetFormatError) as exc:
        parser.error(str(exc))

    print(f"UEFA Champions League | {dataset.metadata.start_date} to {dataset.metadata.end_date} (UTC)")
    if args.open_dir is not None:
        print("Opened snapshot:", args.open_dir.absolute())
    print(
        f"Complete: {dataset.complete} | Matches: {len(dataset.match_records)} | Teams: {len(dataset.team_records)}"
    )
    if args.cache_dir is not None:
        print("Response cache:", args.cache_dir.expanduser().absolute())
        print("Days reused from cache:", len(dataset.metadata.cached_tasks))
    for match in dataset.match_records:
        kickoff = match.kickoff.isoformat() if match.kickoff is not None else "Unknown"
        home = str(match.home_score) if match.home_score is not None else "?"
        away = str(match.away_score) if match.away_score is not None else "?"
        status = match.source_status_text or match.source_status or "Unknown"
        print(
            f"{match.match_id} | {kickoff} | {match.home_team_name} {home} - {away} {match.away_team_name} | {status}"
        )
    if dataset.complete and not dataset.match_records:
        print("No fixtures returned for this date range.")
    for issue in dataset.errors:
        print(f"{issue.step} {issue.target}: {issue.error_type}: {issue.message}", file=sys.stderr)
    if args.output_dir is not None:
        try:
            print("Saved snapshot:", dataset.save(args.output_dir, format="parquet"))
        except (ImportError, OSError, ValueError) as exc:
            parser.error(str(exc))
    return 0 if dataset.complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
