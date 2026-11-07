"""Resume or update an ESPN season using a caller-selected cache directory.

This example makes network requests when run directly and requires no optional
dependencies. Pass a directory on the command line, for example:
python examples/datasets/cached_season.py C:/data/esd-cache
"""

import argparse

import esd


def main():
    parser = argparse.ArgumentParser(description="Download or resume an ESPN season")
    parser.add_argument("cache_dir", help="Directory in which to store response cache files")
    parser.add_argument("--refresh", action="store_true", help="Bypass cache and fetch again")
    args = parser.parse_args()
    progress = []
    dataset = esd.load_dataset(
        source="espn", league="eng.1", season=2024,
        cache_dir=args.cache_dir, refresh=args.refresh,
        on_error="collect", progress=progress.append,
    )
    print("Calendar coverage complete:", dataset.complete)
    print("Matches:", len(dataset.match_records))
    print("Tasks served from cache:", sum(event.cached for event in progress))
    for issue in dataset.errors:
        print(issue.step, issue.target, issue.message)


if __name__ == "__main__":
    main()
