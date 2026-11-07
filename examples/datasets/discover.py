"""Inspect discovery support or fetch provider competitions and seasons. Base install."""

import argparse
import sys
from pathlib import Path

import esd


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List implemented operations without network access")
    parser.add_argument("--source", choices=esd.get_discovery_capabilities(), default="espn")
    parser.add_argument("--query", help="365Scores search text, or local name filter for other listings")
    parser.add_argument("--category-id", type=int, help="Sofascore football category")
    parser.add_argument("--date", help="Promiedos source date, YYYY-MM-DD")
    parser.add_argument("--seasons", action="store_true", help="Discover seasons instead of competitions")
    parser.add_argument("--competition-id", help="Native ID or ESPN league slug, required with --seasons")
    parser.add_argument("--cache-dir", type=Path, help="Optional response cache directory")
    parser.add_argument("--refresh", action="store_true", help="Fetch again instead of reusing cache")
    args = parser.parse_args(argv)
    if args.list:
        for source, capability in esd.get_discovery_capabilities().items():
            print(source, "| competitions:", capability.competitions or "manual", "| seasons:", capability.seasons or "manual")
        return 0
    if args.seasons:
        if args.competition_id is None:
            parser.error("--seasons requires --competition-id")
        if any(value is not None for value in (args.query, args.category_id, args.date)):
            parser.error("--seasons cannot be combined with competition listing filters")
    elif args.competition_id is not None:
        parser.error("--competition-id requires --seasons")
    try:
        if args.seasons:
            result = esd.list_seasons(args.source, args.competition_id, cache_dir=args.cache_dir, refresh=args.refresh)
        else:
            result = esd.list_competitions(args.source, query=args.query, category_id=args.category_id,
                                           date=args.date, cache_dir=args.cache_dir, refresh=args.refresh)
    except (ValueError, TypeError) as exc:
        parser.error(str(exc))
    except esd.ESDException as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print("Source:", result.source, "| Scope:", result.scope, "| Cached:", result.cached)
    print("Original fetch:", result.fetched_at.isoformat())
    for row in result.competitions:
        print(row.competition_id, "| native ID:", row.native_id, "|", row.name)
    for row in result.seasons:
        print(row.season_id, "| name:", row.name, "| native year:", row.year, "| source label:", row.source_season)
    for note in result.notes:
        print("Note:", note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
