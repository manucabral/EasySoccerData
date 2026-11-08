"""Compare Champions League matches from 365Scores and ESPN using explicit IDs.

Downloads and comparison use the base installation. Saving or opening the pair
requires [parquet], without pandas. Source status codes remain separate.
"""

import argparse
import json
import math
import os
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from importlib.util import find_spec
from pathlib import Path
from tempfile import TemporaryDirectory

import esd

DEFAULT_IDENTITIES = Path(__file__).with_name("champions_identities.json")


def read_identities(path):
    """Read the caller's aliases without matching names or native IDs across sources."""
    identities = esd.IdentityMap.from_dict(json.loads(path.read_text(encoding="utf-8")))
    return identities.to_dict(), identities


def download_espn(start, end, season, cache_dir=None, refresh=False):
    """Query daily scoreboards with one boundary day on either side, then filter UTC.

    Boundary queries cover fixtures that a source day may place on an adjacent
    UTC date. Repeated native IDs keep the newest original response observation.
    """
    started = datetime.now(timezone.utc)
    days = [(start + timedelta(days=offset)).isoformat()
            for offset in range(-1, (end - start).days + 2)]
    client = esd.ESPNClient(
        response_cache=esd.ResponseCache(cache_dir) if cache_dir is not None else None,
        refresh=refresh, request_delay=0.25,
    )
    successful, errors, times, cached = [], [], [], []
    matches, teams, observations = {}, {}, {}
    for day in days:
        key = f"matches:{day}"
        try:
            events = client.get_scoreboard("uefa.champions", day, expected_season=season)
            batch = []
            for event in events:
                row = esd.normalize_match(event, competition_id="uefa.champions", season=season)
                if row.kickoff is None:
                    raise ValueError(f"ESPN match {row.match_id} has no UTC kickoff")
                if start <= row.kickoff.date() <= end:
                    batch.append(row)
            info = client.last_response
            observed = info.fetched_at if info is not None else datetime.now(timezone.utc).timestamp()
            for row in batch:
                if observed >= observations.get(row.match_id, float("-inf")):
                    matches[row.match_id] = row
                    observations[row.match_id] = observed
            successful.append(key)
            if info is not None:
                times.append((key, datetime.fromtimestamp(observed, timezone.utc).isoformat()))
                if info.cached:
                    cached.append(key)
        except (esd.ESDException, ValueError, TypeError, KeyError) as exc:
            errors.append(esd.DatasetIssue("matches", day, type(exc).__name__, str(exc)))
    for row in matches.values():
        for team_id, name in ((row.home_team_id, row.home_team_name), (row.away_team_id, row.away_team_name)):
            if team_id is not None:
                teams[team_id] = esd.NormalizedTeam("espn", team_id, name)
    return esd.SoccerDataset(
        esd.DatasetMetadata(
            "espn", "uefa.champions", season, ("matches", "teams"), started,
            datetime.now(timezone.utc), coverage_scope="date_range",
            start_date=start.isoformat(), end_date=end.isoformat(),
            expected_tasks=tuple(f"matches:{day}" for day in days),
            successful_tasks=tuple(successful), response_fetched_at=tuple(times),
            cached_tasks=tuple(cached),
        ),
        match_records=tuple(matches.values()), team_records=tuple(teams.values()), errors=tuple(errors),
    )


def compare(left, right, identities, tolerance_seconds=300):
    """Report unique links, unresolved IDs and raw score/kickoff differences."""
    for dataset, source, league in ((left, "scores365", "572"), (right, "espn", "uefa.champions")):
        meta = dataset.metadata
        if (meta.source, meta.league, meta.coverage_scope) != (source, league, "date_range"):
            raise ValueError(f"Expected a {source} Champions League date-range snapshot")
        if meta.start_date is None or meta.end_date is None:
            raise ValueError("Both snapshots must preserve their UTC date bounds")
        if any(row.kickoff is not None and not meta.start_date <= row.kickoff.date().isoformat() <= meta.end_date
               for row in dataset.match_records):
            raise ValueError(f"{source} snapshot includes matches outside its date bounds")
    if (left.metadata.start_date, left.metadata.end_date) != (right.metadata.start_date, right.metadata.end_date):
        raise ValueError("Both snapshots must select the same UTC date range")
    result = esd.link_dataset_matches(left, right, identities=identities, tolerance_seconds=tolerance_seconds)
    by_left = {row.match_id: row for row in left.match_records}
    by_right = {row.match_id: row for row in right.match_records}
    links = []
    for link in result.links:
        first, second = by_left[link.left_match_id], by_right[link.right_match_id]
        values = (first.home_score, first.away_score, second.home_score, second.away_score)
        score = "unknown" if None in values else "equal" if values[:2] == values[2:] else "different"
        links.append({
            "scores365": asdict(first), "espn": asdict(second),
            "kickoff_difference_seconds": link.kickoff_difference_seconds, "score_comparison": score,
        })
    sources = {}
    for dataset in (left, right):
        meta = dataset.metadata
        sources[meta.source] = {
            "complete": dataset.complete, "matches": len(dataset.match_records),
            "started_at": meta.started_at.isoformat(), "finished_at": meta.finished_at.isoformat(),
            "season_label": meta.season, "response_fetched_at": dict(meta.response_fetched_at),
            "cached_tasks": list(meta.cached_tasks), "errors": [asdict(issue) for issue in dataset.errors],
        }
    return {
        "start_date": left.metadata.start_date, "end_date": left.metadata.end_date,
        "tolerance_seconds": tolerance_seconds, "sources": sources,
        "compatibility": asdict(result.compatibility), "links": links,
        "unmatched": {"scores365": result.unmatched_left, "espn": result.unmatched_right},
        "ambiguous": {"scores365": result.ambiguous_left, "espn": result.ambiguous_right},
    }


def save_pair(destination, left, right, aliases, report):
    """Publish both snapshots, the supplied aliases and report to a new directory."""
    destination = destination.absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Comparison destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".esd-comparison-", dir=destination.parent) as temporary:
        staging = Path(temporary) / "pair"
        staging.mkdir()
        left.save(staging / "scores365")
        right.save(staging / "espn")
        (staging / "identities.json").write_text(json.dumps(aliases, indent=2) + "\n", encoding="utf-8")
        (staging / "comparison.json").write_text(
            json.dumps(report, default=lambda value: value.isoformat(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"Comparison destination already exists: {destination}")
        os.rename(staging, destination)
    return destination


def display(report):
    print(f"UEFA Champions League | {report['start_date']} to {report['end_date']} (UTC)")
    for source, provenance in report["sources"].items():
        print(f"{source}: complete={provenance['complete']} | matches={provenance['matches']}")
        print(f"  Loader: {provenance['started_at']} to {provenance['finished_at']}")
        for task, timestamp in provenance["response_fetched_at"].items():
            print(f"  Original fetch: {task} | {timestamp} | cached={task in provenance['cached_tasks']}")
        for issue in provenance["errors"]:
            print(f"{source} {issue['step']} {issue['target']}: {issue['error_type']}: {issue['message']}", file=sys.stderr)
    print("Schema compatible:", report["compatibility"]["schema_compatible"])
    print("Identity coverage complete:", report["compatibility"]["identity_compatible"])
    for issue in report["compatibility"]["issues"]:
        print("Compatibility:", issue)
    print("Linked matches:", len(report["links"]))
    for link in report["links"]:
        print(f"Link | kickoff difference={link['kickoff_difference_seconds']}s | scores={link['score_comparison']}")
        for source in ("scores365", "espn"):
            row = link[source]
            score = [str(row[key]) if row[key] is not None else "?" for key in ("home_score", "away_score")]
            print(f"  {source}:{row['match_id']} | {row['kickoff']} | {row['home_team_name']} {score[0]} - {score[1]} {row['away_team_name']} | status={row['source_status']} ({row['source_status_text']})")
    for label in ("unmatched", "ambiguous"):
        for source, identifiers in report[label].items():
            print(f"{label.capitalize()} {source}: {', '.join(identifiers) or 'none'}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--output-dir", type=Path, help="New directory for both snapshots, aliases and report")
    mode.add_argument("--open-dir", type=Path, help="Compare a saved pair without network access")
    parser.add_argument("--identities", type=Path, help="Explicit JSON aliases, replacing the sample or saved aliases")
    parser.add_argument("--start-date", help="First UTC day (default: 2026-11-03)")
    parser.add_argument("--end-date", help="Last UTC day, inclusive (default: 2026-11-04)")
    parser.add_argument("--season", type=int, help="365Scores caller label (default: 2026)")
    parser.add_argument("--espn-season", type=int, help="ESPN source season year (default: 2026)")
    parser.add_argument("--cache-dir", type=Path, help="Persistent response cache for both providers")
    parser.add_argument("--refresh", action="store_true", help="Fetch again instead of reusing responses")
    parser.add_argument("--tolerance-seconds", type=float, help="Maximum UTC kickoff difference (default: 300, or saved value)")
    args = parser.parse_args(argv)
    if args.open_dir is not None and (
        any(value is not None for value in (args.start_date, args.end_date, args.season, args.espn_season, args.cache_dir))
        or args.refresh
    ):
        parser.error("--open-dir cannot be combined with download options")
    try:
        tolerance = args.tolerance_seconds if args.tolerance_seconds is not None else 300
        if not math.isfinite(tolerance) or tolerance < 0:
            raise ValueError("Tolerance must be finite and nonnegative")
        if args.output_dir is not None:
            args.output_dir = args.output_dir.expanduser()
            if args.output_dir.exists() or args.output_dir.is_symlink():
                raise FileExistsError(f"Comparison destination already exists: {args.output_dir}")
        if (args.output_dir is not None or args.open_dir is not None) and find_spec("pyarrow") is None:
            raise ImportError('Saving or opening requires python -m pip install -e ".[parquet]".')
        if args.open_dir is not None:
            root = args.open_dir.expanduser()
            if args.tolerance_seconds is None:
                saved_report = json.loads((root / "comparison.json").read_text(encoding="utf-8"))
                if not isinstance(saved_report, dict) or type(saved_report.get("tolerance_seconds")) not in (int, float):
                    raise ValueError("Saved comparison is missing a numeric tolerance")
                tolerance = saved_report["tolerance_seconds"]
            identities_path = args.identities.expanduser() if args.identities else root / "identities.json"
            aliases, identities = read_identities(identities_path)
            left, right = esd.open_dataset(root / "scores365"), esd.open_dataset(root / "espn")
        else:
            start_text = args.start_date if args.start_date is not None else "2026-11-03"
            end_text = args.end_date if args.end_date is not None else "2026-11-04"
            start, end = (datetime.strptime(value, "%Y-%m-%d").date() for value in (start_text, end_text))
            if start.isoformat() != start_text or end.isoformat() != end_text or not 0 <= (end - start).days <= 6:
                raise ValueError("Choose one to seven ordered UTC days using YYYY-MM-DD")
            # Check padding dates before either provider is queried.
            start - timedelta(days=1), end + timedelta(days=1)
            season = args.season if args.season is not None else 2026
            espn_season = args.espn_season if args.espn_season is not None else 2026
            if not all(1000 <= year <= 9999 for year in (season, espn_season)):
                raise ValueError("Season years must contain four digits")
            identities_path = args.identities.expanduser() if args.identities else DEFAULT_IDENTITIES
            aliases, identities = read_identities(identities_path)
            left = esd.load_dataset(source="scores365", league=572, season=season,
                                    start_date=start_text, end_date=end_text, tables=["matches"],
                                    on_error="collect", cache_dir=args.cache_dir, refresh=args.refresh)
            right = download_espn(start, end, espn_season, args.cache_dir, args.refresh)
        report = compare(left, right, identities, tolerance)
        if args.output_dir is not None:
            print("Saved comparison:", save_pair(args.output_dir, left, right, aliases, report))
    except (OSError, ValueError, TypeError, OverflowError, ImportError, esd.ESDException) as exc:
        parser.error(str(exc))
    display(report)
    return 0 if left.complete and right.complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
