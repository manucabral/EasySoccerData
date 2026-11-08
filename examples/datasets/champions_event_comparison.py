"""Compare explicit ESPN/365Scores Champions events or reopen a saved pair.

Base records need no extra. Snapshot save/open needs [parquet], without pandas.
The default aliases review only three players from Shakhtar-Sporting, Nov 3, 2026.
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

DEFAULT_IDENTITIES = Path(__file__).with_name("champions_event_identities.json")


def positive(value):
    if not value.isascii() or not value.isdecimal() or int(value) < 1:
        raise argparse.ArgumentTypeError("Expected a positive native numeric ID")
    return str(int(value))


def nonnegative(value):
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("Expected a finite nonnegative number")
    return number


def reference(event):
    if event is None:
        return None
    return f"id:{event.event_id}" if event.event_id is not None else f"order:{event.source_order}"


def read_identities(path):
    return esd.IdentityMap.from_dict(json.loads(path.read_text(encoding="utf-8")))


def report_options(report):
    return {"format": "easysoccerdata-event-comparison", "format_version": 1,
            "minute_tolerance": report.minute_tolerance, "tolerance_seconds": report.kickoff_tolerance_seconds,
            "event_types": list(report.event_types), "period_aliases": [list(item) for item in report.period_aliases],
            "allow_unknown_period": report.allow_unknown_period}


def read_options(path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    expected = {"format", "format_version", "minute_tolerance", "tolerance_seconds", "event_types", "period_aliases"}
    if (not isinstance(raw, dict) or set(raw) not in (expected, expected | {"allow_unknown_period"}) or raw["format"] != "easysoccerdata-event-comparison"
            or type(raw["format_version"]) is not int or raw["format_version"] != 1):
        raise ValueError("Invalid event comparison options format/version")
    periods = raw["period_aliases"]
    if not isinstance(periods, list) or any(not isinstance(row, list) or len(row) != 3
                                          or any(not isinstance(value, str) for value in row) for row in periods):
        raise ValueError("Invalid saved period aliases")
    mapping = {}
    for source, native, canonical in periods:
        if (source, native) in mapping:
            raise ValueError("Duplicate saved period alias")
        mapping[source, native] = canonical
    return {"minute_tolerance": raw["minute_tolerance"], "tolerance_seconds": raw["tolerance_seconds"],
            "event_types": raw["event_types"], "period_aliases": mapping,
            "allow_unknown_period": raw.get("allow_unknown_period", False)}


def save_pair(destination, pair, identities, report):
    """Stage both source snapshots, reviewed aliases, options and the report."""
    destination = destination.absolute()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".esd-event-comparison-", dir=destination.parent) as temporary:
        staging = Path(temporary) / "pair"
        staging.mkdir()
        for dataset in pair:
            target = dataset.save(staging / dataset.metadata.source)
            if esd.open_dataset(target) != dataset:
                raise esd.DatasetFormatError("Reopened event snapshot differs from the download")
        for name, value in (("identities", identities.to_dict()),
                            ("options", report_options(report)), ("comparison", asdict(report))):
            (staging / f"{name}.json").write_text(json.dumps(value, default=lambda item: item.isoformat(), indent=2) + "\n", encoding="utf-8")
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"Comparison destination already exists: {destination}")
        os.rename(staging, destination)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--espn-match-id", type=positive)
    parser.add_argument("--scores365-match-id", type=positive)
    parser.add_argument("--espn-season", type=int)
    parser.add_argument("--year", type=int, help="Caller year label for 365Scores")
    parser.add_argument("--season-id", type=positive, help="Native 365Scores season ID")
    parser.add_argument("--identities", type=Path)
    parser.add_argument("--minute-tolerance", type=int)
    parser.add_argument("--kickoff-tolerance", type=nonnegative)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--pandas", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    storage = parser.add_mutually_exclusive_group()
    storage.add_argument("--output-dir", type=Path, help="New directory for snapshots/identities/options/report")
    storage.add_argument("--open-dir", type=Path, help="Recompute from saved source snapshots without HTTP")
    args = parser.parse_args(argv)
    selection = (args.espn_match_id, args.scores365_match_id, args.espn_season, args.year, args.season_id)
    if args.limit < 1 or args.minute_tolerance is not None and args.minute_tolerance < 0:
        parser.error("--limit must be positive and --minute-tolerance nonnegative")
    if args.open_dir is not None and (args.refresh or any(value is not None for value in (
        *selection, args.identities, args.minute_tolerance, args.kickoff_tolerance, args.cache_dir,
    ))):
        parser.error("--open-dir cannot be combined with download options or external comparison settings")
    if args.open_dir is None and (any(value is None for value in selection)
                                 or not all(1000 <= value <= 9999 for value in (args.espn_season, args.year))):
        parser.error("Download needs both native match IDs, --espn-season, --year and --season-id")
    try:
        if args.output_dir is not None:
            args.output_dir = args.output_dir.expanduser()
            if args.output_dir.exists() or args.output_dir.is_symlink():
                raise FileExistsError(f"Comparison destination already exists: {args.output_dir}")
        if (args.output_dir is not None or args.open_dir is not None) and find_spec("pyarrow") is None:
            raise ImportError("Snapshot storage requires EasySoccerData[parquet]")
        if args.pandas and find_spec("pandas") is None:
            raise ImportError("DataFrame display requires EasySoccerData[pandas]")
        if args.open_dir is not None:
            directory = args.open_dir.expanduser()
            identities = read_identities(directory / "identities.json")
            options = read_options(directory / "options.json")
            pair = [esd.open_dataset(directory / source) for source in ("espn", "scores365")]
        else:
            identities = read_identities((args.identities or DEFAULT_IDENTITIES).expanduser())
            options = {"minute_tolerance": args.minute_tolerance if args.minute_tolerance is not None else 1,
                       "tolerance_seconds": args.kickoff_tolerance if args.kickoff_tolerance is not None else 300}
            pair = [esd.load_dataset(source=source, league=league, season=year, season_id=season,
                                      match_ids=[identifier], tables=["match_events"], max_match_requests=1,
                                      cache_dir=args.cache_dir, refresh=args.refresh, on_error="collect")
                    for source, league, year, season, identifier in (
                        ("espn", "uefa.champions", args.espn_season, None, args.espn_match_id),
                        ("scores365", "572", args.year, args.season_id, args.scores365_match_id),
                    )]
        for dataset, source, league in zip(pair, ("espn", "scores365"), ("uefa.champions", "572")):
            if (dataset.metadata.source, dataset.metadata.league) != (source, league):
                raise ValueError(f"Expected a {source} Champions League snapshot")
        report = esd.compare_match_events(*pair, identities=identities, **options)
        print("Linked matches:", len(report.linkage.links), "| Paired events:", sum(row.left_event is not None and row.right_event is not None for row in report.rows),
              "| Differences:", len(report.differences), "| Unresolved:", len(report.unresolved))
        for row in report.rows[:args.limit]:
            print(row.status, row.reason, "| Differences:", row.differences, "| Unknown:", row.unknown_fields,
                  "| Native events:", reference(row.left_event), reference(row.right_event))
        for dataset in pair:
            print(dataset.metadata.source, "| Complete:", dataset.complete, "| Cached:", dataset.metadata.cached_tasks,
                  "| Original fetches:", dataset.metadata.response_fetched_at)
            for issue in dataset.errors:
                print(f"{issue.step} {issue.target}: {issue.error_type}: {issue.message}", file=sys.stderr)
        print("Excluded types:", len(report.excluded_left), len(report.excluded_right))
        if args.output_dir is not None:
            save_pair(args.output_dir, pair, identities, report)
            print("Saved and verified:", args.output_dir)
        if args.pandas:
            print(report.to_dataframe().head(args.limit))
        unresolved_matches = (report.linkage.unmatched_left, report.linkage.unmatched_right,
                              report.linkage.ambiguous_left, report.linkage.ambiguous_right)
        return 0 if (report.left_complete and report.right_complete and report.linkage.links
                     and not report.unresolved and not any(unresolved_matches)) else 1
    except (ValueError, OSError, ImportError) as exc:
        parser.error(str(exc))
    except esd.ESDException as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
