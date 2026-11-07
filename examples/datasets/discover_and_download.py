"""Find a 365Scores competition/season, download up to seven UTC days and validate.

The download uses the base install. --output-dir saves and verifies a new Parquet
snapshot with [parquet]. --open-dir validates a saved snapshot without HTTP.
"""

import argparse
import sys
from datetime import datetime
from importlib.util import find_spec
from pathlib import Path

import esd


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", help="Competition search text (default: Champions)")
    parser.add_argument("--competition-id", help="Exact native ID among search results (default: 572)")
    parser.add_argument("--season-id", help="Exact native season ID from discover.py; required for download")
    parser.add_argument("--season", type=int, help="Caller year label (default: 2026)")
    parser.add_argument("--start-date", help="First UTC day (default: 2026-11-03)")
    parser.add_argument("--end-date", help="Last UTC day (default: 2026-11-04)")
    parser.add_argument("--cache-dir", type=Path, help="Caller-selected response cache directory")
    parser.add_argument("--refresh", action="store_true", help="Fetch source responses again")
    storage = parser.add_mutually_exclusive_group()
    storage.add_argument("--output-dir", type=Path, help="New snapshot directory; existing paths are rejected")
    storage.add_argument("--open-dir", type=Path, help="Read and validate a snapshot offline")
    args = parser.parse_args(argv)
    if args.open_dir is not None and (args.refresh or any(value is not None for value in (
        args.query, args.competition_id, args.season_id, args.season, args.start_date, args.end_date, args.cache_dir,
    ))):
        parser.error("--open-dir cannot be combined with download options")
    try:
        if args.output_dir is not None:
            args.output_dir = args.output_dir.expanduser()
            if args.output_dir.exists() or args.output_dir.is_symlink():
                raise FileExistsError(f"Snapshot destination already exists: {args.output_dir}")
        if (args.output_dir is not None or args.open_dir is not None) and find_spec("pyarrow") is None:
            raise ImportError('Snapshot storage requires EasySoccerData[parquet]')
        if args.open_dir is not None:
            dataset = esd.open_dataset(args.open_dir.expanduser())
            if dataset.metadata.source != "scores365" or "matches" not in dataset.metadata.tables:
                raise ValueError("Choose a 365Scores matches snapshot")
        else:
            competition_id = args.competition_id if args.competition_id is not None else "572"
            if (not competition_id.isascii() or not competition_id.isdigit() or int(competition_id) < 1
                    or args.season_id is None or not args.season_id.isascii()
                    or not args.season_id.isdigit() or int(args.season_id) < 1):
                raise ValueError("Choose positive native competition and season IDs; --season-id is required")
            competition_id, season_id = str(int(competition_id)), str(int(args.season_id))
            year = args.season if args.season is not None else 2026
            if not 1000 <= year <= 9999:
                raise ValueError("--season must be a four-digit caller year label")
            start_text = args.start_date if args.start_date is not None else "2026-11-03"
            end_text = args.end_date if args.end_date is not None else "2026-11-04"
            start, end = (datetime.strptime(value, "%Y-%m-%d").date() for value in (start_text, end_text))
            if start.isoformat() != start_text or end.isoformat() != end_text or not 0 <= (end - start).days <= 6:
                raise ValueError("Choose an ordered range of one to seven UTC days using YYYY-MM-DD")
            discovery_options = {"cache_dir": args.cache_dir, "refresh": args.refresh}
            query = args.query if args.query is not None else "Champions"
            competitions = esd.list_competitions("scores365", query=query, **discovery_options)
            selected = next((row for row in competitions.competitions if row.competition_id == competition_id), None)
            if selected is None:
                raise ValueError("Competition ID was not returned by this search; inspect discover.py results")
            seasons = esd.list_seasons("scores365", competition_id, **discovery_options)
            season = next((row for row in seasons.seasons if row.season_id == season_id), None)
            if season is None:
                raise ValueError("Season ID was not returned in competition details; historical coverage is not guaranteed")
            print("Selected:", selected.name, "| Competition ID:", competition_id, "| Season ID:", season_id, "| Label:", season.name)
            dataset = esd.load_dataset(source="scores365", league=competition_id, season=year,
                                       season_id=season_id, start_date=start_text, end_date=end_text,
                                       tables=("matches", "standings"), on_error="collect", **discovery_options)
        report = esd.validate_dataset(dataset)
        print("Complete:", dataset.complete, "| Matches:", len(dataset.match_records), "| Standings:", len(dataset.standing_records))
        print("Validation errors:", len(report.errors), "| Warnings:", len(report.warnings))
        for issue in dataset.errors:
            print(f"{issue.step} {issue.target}: {issue.error_type}: {issue.message}", file=sys.stderr)
        for issue in report.issues:
            print(f"{issue.severity}: {issue.code}: {issue.message}", file=sys.stderr)
        if not report.valid:
            return 1
        if args.output_dir is not None:
            destination = dataset.save(args.output_dir, format="parquet")
            restored = esd.open_dataset(destination)
            if restored != dataset:
                raise esd.DatasetFormatError("Reopened snapshot differs from the downloaded dataset")
            print("Saved and verified:", destination)
            if not dataset.complete:
                print("Snapshot retains partial coverage and source errors.")
        return 0 if dataset.complete else 1
    except (ValueError, OSError, ImportError) as exc:
        parser.error(str(exc))
    except esd.ESDException as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
