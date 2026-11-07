"""Inspect native match events for explicit ESPN/365Scores IDs, or open a snapshot.

Base records need no extra. --pandas needs [pandas], save/open needs [parquet].
Choose --with-players to include lineups/player statistics in the same detail read.
"""

import argparse
import sys
from importlib.util import find_spec
from pathlib import Path

import esd


def timeline_key(row):
    """Display by observed clock, with shootout attempts after match events."""
    return (row.match_id or "", row.is_shootout is True,
            row.minute if row.minute is not None else float("inf"),
            row.added_minute if row.added_minute is not None else 0,
            row.source_order if row.source_order is not None else 0)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("espn", "scores365"))
    parser.add_argument("--league", help="Native competition slug (ESPN) or numeric ID (365Scores)")
    parser.add_argument("--season", type=int, help="Native ESPN year or caller year label for 365Scores")
    parser.add_argument("--season-id", help="Required native season ID for 365Scores")
    parser.add_argument("--match-id", action="append", help="Explicit native ID, repeat for more matches")
    parser.add_argument("--max-match-requests", type=int)
    parser.add_argument("--with-players", action="store_true")
    parser.add_argument("--with-match-stats", action="store_true")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--pandas", action="store_true")
    parser.add_argument("--limit", type=int, default=30)
    storage = parser.add_mutually_exclusive_group()
    storage.add_argument("--output-dir", type=Path, help="New Parquet snapshot directory")
    storage.add_argument("--open-dir", type=Path, help="Read a snapshot without HTTP")
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be positive")
    if args.open_dir is not None and (args.refresh or args.with_players or args.with_match_stats or any(
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
            if "match_events" not in dataset.metadata.tables:
                raise ValueError("Choose a snapshot containing match_events")
        else:
            tables = ["match_events"]
            if args.with_players:
                tables.append("player_match_stats")
            if args.with_match_stats:
                tables.append("match_stats")
            dataset = esd.load_dataset(
                source=args.source, league=args.league, season=args.season, season_id=args.season_id,
                tables=tables, match_ids=args.match_id,
                max_match_requests=args.max_match_requests if args.max_match_requests is not None else 20,
                cache_dir=args.cache_dir, refresh=args.refresh, on_error="collect",
            )
        report = esd.validate_dataset(dataset)
        print("Source:", dataset.metadata.source, "| Complete:", dataset.complete,
              "| Events:", len(dataset.match_event_records))
        print("Cached tasks:", dataset.metadata.cached_tasks)
        print("Original fetches:", dataset.metadata.response_fetched_at)
        print("Preview sorted by observed minute; unknown clocks remain unknown")
        for row in sorted(dataset.match_event_records, key=timeline_key)[:args.limit]:
            clock = "shootout " + (row.source_clock or "?") if row.is_shootout else (
                "?" if row.minute is None else str(row.minute) + (f"+{row.added_minute}" if row.added_minute else ""))
            print(row.match_id, clock, row.event_type, "|", row.player_name or "?",
                  "| Native player:", row.player_id, "| Related:", row.related_player_id,
                  "| Event ID:", row.event_id, "| Source order:", row.source_order)
        for issue in dataset.errors:
            print(f"{issue.step} {issue.target}: {issue.error_type}: {issue.message}", file=sys.stderr)
        for issue in report.issues:
            print(f"{issue.severity}: {issue.code}: {issue.message}", file=sys.stderr)
        if not report.valid:
            return 1
        if args.output_dir is not None:
            path = dataset.save(args.output_dir)
            if esd.open_dataset(path) != dataset:
                raise esd.DatasetFormatError("Reopened event snapshot differs from the download")
            print("Saved and verified:", path)
        if args.pandas:
            print(dataset.match_events.head(args.limit))
        return 0 if dataset.complete else 1
    except (ValueError, OSError, ImportError) as exc:
        parser.error(str(exc))
    except esd.ESDException as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
