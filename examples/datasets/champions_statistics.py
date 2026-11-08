"""Compare explicit Champions League match IDs from ESPN and 365Scores.

Downloads use at most one endpoint per source before transport retries.
--output-dir/--open-dir require [parquet]. --pandas requires [pandas].
Aliases in champions_identities.json are a checked sample, not a global registry.
"""

import argparse
import json
import math
import os
import sys
from dataclasses import asdict
from importlib.util import find_spec
from pathlib import Path
from tempfile import TemporaryDirectory

import esd

DEFAULT_IDENTITIES = Path(__file__).with_name("champions_identities.json")


def nonnegative(value):
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("Expected a finite nonnegative number")
    return number


def native_id(value):
    if not value.isascii() or not value.isdecimal() or int(value) <= 0:
        raise argparse.ArgumentTypeError("Expected a positive native numeric ID")
    return str(int(value))


def read_aliases(path):
    identities = esd.IdentityMap.from_dict(json.loads(path.read_text(encoding="utf-8")))
    return identities.to_dict(), identities


def save_pair(destination, pair, aliases, report):
    """Stage validated source snapshots and a JSON report without replacing files."""
    destination = destination.absolute()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".esd-statistics-", dir=destination.parent) as temporary:
        staging = Path(temporary) / "pair"
        staging.mkdir()
        for dataset in pair:
            path = dataset.save(staging / dataset.metadata.source)
            if esd.open_dataset(path) != dataset:
                raise esd.DatasetFormatError("Reopened source snapshot differs from the download")
        (staging / "identities.json").write_text(json.dumps(aliases, indent=2) + "\n", encoding="utf-8")
        (staging / "comparison.json").write_text(
            json.dumps(asdict(report), default=lambda value: value.isoformat(), indent=2) + "\n", encoding="utf-8",
        )
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"Comparison destination already exists: {destination}")
        os.rename(staging, destination)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--espn-match-id", type=native_id)
    parser.add_argument("--scores365-match-id", type=native_id)
    parser.add_argument("--season", type=int, help="Native ESPN year, not inferred from a season label")
    parser.add_argument("--season-id", type=native_id, help="Native 365Scores season ID")
    parser.add_argument("--identities", type=Path, help="Caller-supplied JSON aliases")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--possession-tolerance", type=nonnegative, default=0.1, help="Absolute percentage points")
    parser.add_argument("--kickoff-tolerance", type=nonnegative, default=300, help="Seconds allowed for match linkage")
    parser.add_argument("--pandas", action="store_true")
    storage = parser.add_mutually_exclusive_group()
    storage.add_argument("--output-dir", type=Path, help="New directory for both snapshots, aliases and report")
    storage.add_argument("--open-dir", type=Path, help="Read saved sources/aliases and recompute without HTTP")
    args = parser.parse_args(argv)
    selection = (args.espn_match_id, args.scores365_match_id, args.season, args.season_id)
    if args.open_dir is not None and (any(item is not None for item in (*selection, args.identities, args.cache_dir)) or args.refresh):
        parser.error("--open-dir cannot be combined with download options or external aliases")
    if args.open_dir is None and any(item is None for item in selection):
        parser.error("Download requires --espn-match-id, --scores365-match-id, --season and --season-id")
    try:
        if args.output_dir is not None:
            args.output_dir = args.output_dir.expanduser()
            if args.output_dir.exists() or args.output_dir.is_symlink():
                raise FileExistsError(f"Comparison destination already exists: {args.output_dir}")
        if (args.open_dir is not None or args.output_dir is not None) and find_spec("pyarrow") is None:
            raise ImportError("Snapshot storage requires EasySoccerData[parquet]")
        if args.pandas and find_spec("pandas") is None:
            raise ImportError("DataFrame display requires EasySoccerData[pandas]")
        if args.open_dir is not None:
            directory = args.open_dir.expanduser()
            aliases, identities = read_aliases(directory / "identities.json")
            pair = [esd.open_dataset(directory / source) for source in ("espn", "scores365")]
        else:
            aliases, identities = read_aliases((args.identities or DEFAULT_IDENTITIES).expanduser())
            pair = [esd.load_dataset(
                source=source, league=league, season=args.season, season_id=season_id,
                match_ids=[identifier], tables=["match_stats"], max_match_requests=1,
                cache_dir=args.cache_dir, refresh=args.refresh, on_error="collect",
            ) for source, league, season_id, identifier in (
                ("espn", "uefa.champions", None, args.espn_match_id),
                ("scores365", "572", args.season_id, args.scores365_match_id),
            )]
        for dataset, source, league in zip(pair, ("espn", "scores365"), ("uefa.champions", "572")):
            if (dataset.metadata.source, dataset.metadata.league) != (source, league):
                raise ValueError(f"Expected a {source} Champions League snapshot")
        report = esd.compare_match_statistics(
            *pair, identities=identities, tolerance_seconds=args.kickoff_tolerance,
            tolerances={"home_possession_pct": args.possession_tolerance, "away_possession_pct": args.possession_tolerance},
        )
        print("Linked matches:", len(report.linkage.links), "| Differences:", len(report.differences),
              "| Unresolved metrics:", len(report.unresolved))
        for metadata, complete in ((report.left_metadata, report.left_complete), (report.right_metadata, report.right_complete)):
            print(metadata.source, "| Complete:", complete, "| Cached:", metadata.cached_tasks,
                  "| Original fetches:", metadata.response_fetched_at)
        for row in report.rows:
            print(row.metric, row.left_value, row.right_value, "|", row.status, "| delta:", row.delta, row.unit)
        for side, identifiers in (("Unmatched ESPN", report.linkage.unmatched_left),
                                  ("Unmatched 365Scores", report.linkage.unmatched_right),
                                  ("Ambiguous ESPN", report.linkage.ambiguous_left),
                                  ("Ambiguous 365Scores", report.linkage.ambiguous_right)):
            if identifiers:
                print(side, identifiers)
        for issue in (*report.left_errors, *report.right_errors):
            print(f"{issue.step} {issue.target}: {issue.error_type}: {issue.message}", file=sys.stderr)
        if args.output_dir is not None:
            save_pair(args.output_dir, pair, aliases, report)
            print("Saved and verified:", args.output_dir)
        if args.pandas:
            print(report.to_dataframe())
        usable = (report.left_complete and report.right_complete and bool(report.rows)
                  and not any((report.linkage.unmatched_left, report.linkage.unmatched_right,
                               report.linkage.ambiguous_left, report.linkage.ambiguous_right))
                  and all(row.left_statistics_available and row.right_statistics_available for row in report.rows))
        return 0 if usable else 1
    except (ValueError, OSError, ImportError) as exc:
        parser.error(str(exc))
    except esd.ESDException as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
