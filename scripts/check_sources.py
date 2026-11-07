"""Run small live dataset queries separately from the offline test suite."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

SOURCES = (
    "espn",
    "sofascore",
    "scores365",
    "understat",
    "fbref",
    "goaloo",
    "promiedos",
    "besoccer",
    "transfermarkt",
)
TABLES = {
    "matches": ("match_records", "match_id"),
    "teams": ("team_records", "team_id"),
    "standings": ("standing_records", "team_id"),
    "player_stats": ("player_stat_records", "player_id"),
}


def selection(source, day):
    """Select one day, standings table, season response or club profile."""
    queries = {
        "espn": {"league": "eng.1", "season": 2024, "tables": ["standings"]},
        "sofascore": {"league": 17, "season": 2024, "season_id": 61627, "tables": ["standings"]},
        "scores365": {"league": 7, "season": int(day[:4]), "start_date": day, "end_date": day},
        "understat": {"league": "EPL", "season": 2024, "tables": ["player_stats"]},
        "fbref": {
            "league": 9,
            "season": 2024,
            "start_date": "2024-08-16",
            "end_date": "2024-08-16",
            "source_timezone": "Europe/London",
        },
        "goaloo": {
            "league": 36,
            "season": 2024,
            "source_season": "2024-2025",
            "tables": ["teams", "standings"],
        },
        "promiedos": {
            "league": "hc",
            "season": int(day[:4]),
            "start_date": day,
            "end_date": day,
            "source_timezone": "America/Argentina/Buenos_Aires",
        },
        "besoccer": {"league": "torneo_final", "season": int(day[:4]), "tables": ["standings"]},
        "transfermarkt": {
            "league": "GB1",
            "season": int(day[:4]),
            "tables": ["teams"],
            "club_ids": [281],
        },
    }
    return queries[source]


def inspect_dataset(dataset):
    """Check record types, native IDs, source labels and UTC kickoff values."""
    from esd.normalized.schema import TABLE_MODELS

    counts = {}
    for table in dataset.metadata.tables:
        attribute, identifier = TABLES[table]
        rows = getattr(dataset, attribute)
        counts[table] = len(rows)
        for row in rows:
            if not isinstance(row, TABLE_MODELS[table]):
                raise ValueError(f"Unexpected record type in {table}")
            if row.source != dataset.metadata.source or not getattr(row, identifier):
                raise ValueError(f"Missing source identity in {table}")
            kickoff = getattr(row, "kickoff", None)
            if kickoff is not None and (
                kickoff.utcoffset() is None or kickoff.utcoffset().total_seconds() != 0
            ):
                raise ValueError("Kickoff is not timezone-aware UTC")
    return counts


def probe(source, day, max_requests):
    import httpx
    from curl_cffi.requests import Session

    import esd
    from esd.exceptions import SourceError

    result = {"source": source, "selection": selection(source, day), "requests": []}
    started = time.monotonic()

    def bounded(original):
        def request(*args, **kwargs):
            if len(result["requests"]) >= max_requests:
                raise SourceError("Live check reached its HTTP request limit")
            event = {}
            result["requests"].append(event)
            kwargs["timeout"] = 10
            try:
                response = original(*args, **kwargs)
                event["status"] = response.status_code
                return response
            except Exception as exc:
                event["error_type"] = type(exc).__name__
                raise

        return request

    def no_browser(*args, **kwargs):
        raise RuntimeError("Live dataset checks do not launch browsers")

    try:
        with (
            patch.object(httpx.Client, "request", bounded(httpx.Client.request)),
            patch.object(Session, "request", bounded(Session.request)),
            patch("esd.utils.BrowserSession._launch", no_browser),
        ):
            dataset = esd.load_dataset(source=source, **result["selection"], on_error="collect")
        result["counts"] = inspect_dataset(dataset)
        result["complete"] = dataset.complete
        result["errors"] = [vars(issue) for issue in dataset.errors]
        types = {issue.error_type for issue in dataset.errors}
        if dataset.complete:
            result["status"] = "ok" if any(result["counts"].values()) else "empty"
        elif "SourceBlocked" in types:
            result["status"] = "blocked"
        elif "SourceNotFound" in types:
            result["status"] = "not_found"
        else:
            result["status"] = "source_error"
    except Exception as exc:
        result.update(status="error", error_type=type(exc).__name__, message=str(exc))
    result["elapsed_seconds"] = round(time.monotonic() - started, 2)
    return result


def run_source(source, day, timeout, max_requests):
    command = [
        sys.executable,
        "-X",
        "utf8",
        str(Path(__file__).resolve()),
        "--worker",
        source,
        "--date",
        day,
        "--max-requests",
        str(max_requests),
    ]
    try:
        process = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired:
        return {"source": source, "status": "timeout", "elapsed_seconds": timeout}
    if process.returncode:
        return {"source": source, "status": "error", "message": process.stderr[-1000:]}
    try:
        return json.loads(process.stdout)
    except ValueError:
        return {
            "source": source,
            "status": "error",
            "message": "Worker did not return a JSON report",
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", nargs="+", choices=SOURCES, default=list(SOURCES))
    parser.add_argument("--date", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--timeout", type=float, default=45, help="Maximum seconds per source")
    parser.add_argument("--max-requests", type=int, default=3, help="HTTP attempt limit per source")
    parser.add_argument("--output", type=Path, help="Write the JSON report to this path")
    parser.add_argument("--worker", choices=SOURCES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if datetime.strptime(args.date, "%Y-%m-%d").date().isoformat() != args.date:
            raise ValueError
    except ValueError:
        parser.error("--date must use YYYY-MM-DD")
    if not 0 < args.timeout <= 60 or args.max_requests < 1:
        parser.error("--timeout must be in (0, 60] and --max-requests must be positive")
    if args.worker:
        print(json.dumps(probe(args.worker, args.date, args.max_requests)))
        return 0
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "results": []}
    for source in dict.fromkeys(args.source):
        print(f"Checking {source}...", flush=True)
        result = run_source(source, args.date, args.timeout, args.max_requests)
        report["results"].append(result)
        print(f"{source}: {result['status']} {result.get('counts', {})}", flush=True)
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Report: {args.output}")
    return int(any(item["status"] not in ("ok", "empty") for item in report["results"]))


if __name__ == "__main__":
    raise SystemExit(main())
