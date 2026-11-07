"""Resolve reviewed competition IDs and explicitly query native seasons.

Default execution lists the local catalog without HTTP. --seasons/--season-id
request one provider index. This script does not download a dataset.
"""

import argparse
import sys
from pathlib import Path

import esd


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, help="Caller-owned catalog JSON, otherwise use the bundled sample")
    parser.add_argument("--list", action="store_true", help="List reviewed competition IDs without source requests")
    parser.add_argument("--competition", help="Canonical ID, name or declared alias")
    parser.add_argument("--source", choices=tuple(esd.get_dataset_capabilities()))
    parser.add_argument("--seasons", action="store_true", help="Query this provider's native season index")
    parser.add_argument("--season-id", help="Query seasons and select this exact returned native ID")
    parser.add_argument("--year", type=int, help="Caller year label, required when the source has no explicit year")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args(argv)
    discovery = args.seasons or args.season_id is not None
    listing = args.list or not any((args.competition, args.source, discovery, args.year, args.cache_dir, args.refresh))
    if listing and any((args.competition, args.source, discovery, args.year, args.cache_dir, args.refresh)):
        parser.error("--list cannot be combined with provider selection or discovery options")
    if not listing and (args.competition is None or args.source is None):
        parser.error("Choose --competition and --source")
    if args.year is not None and args.season_id is None:
        parser.error("--year requires an explicit --season-id")
    if not discovery and (args.cache_dir is not None or args.refresh):
        parser.error("Cache/refresh options require --seasons or --season-id")
    try:
        catalog = esd.open_catalog(args.catalog) if args.catalog is not None else esd.get_catalog()
        print("Catalog:", catalog.version, "| Reviewed team identities:", len(catalog.teams))
        if listing:
            for competition in catalog.competitions:
                print(competition.canonical_id, "|", competition.name,
                      "|", ", ".join(f"{ref.source}={ref.source_id}" for ref in competition.references))
            return 0
        competition = catalog.competition(args.competition)
        ref = competition.for_source(args.source)
        print(competition.name, "| Source:", ref.source, "| Dataset ID:", ref.source_id, "| Native ID:", ref.native_id)
        print("Reviewed:", ref.verified_at.isoformat(), "| Evidence:", ref.source_url)
        if discovery:
            result = catalog.list_seasons(args.competition, args.source, cache_dir=args.cache_dir, refresh=args.refresh)
            print("Original fetch:", result.fetched_at.isoformat(), "| Cached:", result.cached, "| Scope:", result.scope)
            for season in result.seasons:
                print(season.season_id, "|", season.name, "| Native year:", season.year, "| Source label:", season.source_season)
            if args.season_id is not None:
                selected = next((row for row in result.seasons if row.season_id == args.season_id), None)
                if selected is None:
                    raise ValueError("Choose an exact season ID returned by this source; missing history is not inferred")
                print("Dataset options:", catalog.dataset_options(args.competition, selected, year=args.year))
        return 0
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    except esd.ESDException as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
