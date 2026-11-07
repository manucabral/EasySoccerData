"""Run small live dataset queries separately from the offline test suite."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from contextlib import nullcontext
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.util import find_spec
from pathlib import Path
from tempfile import TemporaryDirectory
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
    """Count selected records. Quality diagnostics come from validate_dataset()."""
    from esd._dataset_storage import _RECORDS

    return {table: len(getattr(dataset, _RECORDS[table])) for table in dataset.metadata.tables}


def validate_sample(dataset):
    """Keep validation errors and warnings separate from source download failures."""
    import esd

    try:
        report = esd.validate_dataset(dataset)
        return {
            "status": "failed" if not report.valid else "warnings" if report.warnings else "passed",
            "valid": report.valid, "errors": [asdict(issue) for issue in report.errors],
            "warnings": [asdict(issue) for issue in report.warnings],
        }
    except Exception as exc:
        return {"status": "error", "error_type": type(exc).__name__, "message": str(exc)}


def check_storage(dataset, path):
    """Save and reopen records, metadata, source errors and completeness without pandas."""
    import esd
    from esd._dataset_storage import _RECORDS

    try:
        saved = dataset.save(path)
        restored = esd.open_dataset(saved)
        checks = {
            "records_equal": all(getattr(restored, attribute) == getattr(dataset, attribute)
                                 for attribute in _RECORDS.values()),
            "metadata_equal": restored.metadata == dataset.metadata,
            "errors_equal": restored.errors == dataset.errors,
            "complete_equal": restored.complete == dataset.complete,
        }
        return {"status": "passed" if all(checks.values()) else "failed", "checks": checks,
                "path": str(saved), "retained": True}
    except Exception as exc:
        return {"status": "error", "error_type": type(exc).__name__, "message": str(exc)}


def passed(result):
    """Require a complete download, valid quality report and any requested storage check."""
    return (
        result["status"] in ("ok", "empty")
        and result.get("validation", {}).get("status") in ("passed", "warnings")
        and result.get("storage", {}).get("status") in ("passed", "not_requested")
    )


def probe(source, day, max_requests, snapshot_path=None):
    import httpx
    from curl_cffi.requests import Session

    import esd
    from esd.exceptions import SourceError

    result = {
        "source": source, "selection": selection(source, day), "requests": [],
        "validation": {"status": "not_run"},
        "storage": {"status": "not_requested" if snapshot_path is None else "not_run"},
    }
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
        result["validation"] = validate_sample(dataset)
        if snapshot_path is not None:
            result["storage"] = check_storage(dataset, snapshot_path)
    except Exception as exc:
        result.update(status="error", error_type=type(exc).__name__, message=str(exc))
    result["elapsed_seconds"] = round(time.monotonic() - started, 2)
    return result


def run_source(source, day, timeout, max_requests, snapshot_dir=None):
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
    if snapshot_dir is not None:
        command.extend(["--snapshot-dir", str(snapshot_dir)])
    try:
        process = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired:
        return {"source": source, "status": "timeout", "elapsed_seconds": timeout}
    if process.returncode:
        return {"source": source, "status": "error", "message": process.stderr[-1000:]}
    try:
        result = json.loads(process.stdout)
        if not isinstance(result, dict) or result.get("source") != source or not isinstance(result.get("status"), str):
            raise ValueError("Invalid worker report")
        return result
    except ValueError:
        return {
            "source": source,
            "status": "error",
            "message": "Worker did not return a valid JSON report",
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", nargs="+", choices=SOURCES, default=list(SOURCES))
    parser.add_argument("--date", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--timeout", type=float, default=45, help="Maximum seconds per source")
    parser.add_argument("--max-requests", type=int, default=3, help="HTTP attempt limit per source")
    parser.add_argument("--output", type=Path, help="Write the JSON report to this path")
    parser.add_argument("--check-parquet", action="store_true", help="Check snapshot round trips using temporary files; needs [parquet]")
    parser.add_argument("--snapshot-dir", type=Path, help="New directory for retained source snapshots; implies --check-parquet")
    parser.add_argument("--worker", choices=SOURCES, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if datetime.strptime(args.date, "%Y-%m-%d").date().isoformat() != args.date:
            raise ValueError
    except ValueError:
        parser.error("--date must use YYYY-MM-DD")
    if not 0 < args.timeout <= 60 or args.max_requests < 1:
        parser.error("--timeout must be in (0, 60] and --max-requests must be positive")
    storage_requested = args.check_parquet or args.snapshot_dir is not None
    if storage_requested and find_spec("pyarrow") is None:
        parser.error('Snapshot checks require python -m pip install -e ".[parquet]".')
    if args.snapshot_dir is not None:
        args.snapshot_dir = args.snapshot_dir.expanduser().absolute()
        if not args.worker:
            try:
                args.snapshot_dir.mkdir(parents=True, exist_ok=False)
            except OSError as exc:
                parser.error(str(exc))
    context = TemporaryDirectory(prefix="esd-source-checks-") if storage_requested and args.snapshot_dir is None else nullcontext(args.snapshot_dir)
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "results": []}
    with context as directory:
        root = Path(directory) if directory is not None else None
        if args.worker:
            result = probe(args.worker, args.date, args.max_requests, root / args.worker if root else None)
            if args.snapshot_dir is None and "path" in result["storage"]:
                result["storage"].update(path=None, retained=False)
            print(json.dumps(result))
            return 0
        for source in dict.fromkeys(args.source):
            print(f"Checking {source}...", flush=True)
            result = run_source(source, args.date, args.timeout, args.max_requests, root)
            if args.snapshot_dir is None and "path" in result.get("storage", {}):
                result["storage"].update(path=None, retained=False)
            report["results"].append(result)
            print(f"{source}: {result['status']} {result.get('counts', {})} | validation={result.get('validation', {}).get('status', 'not_run')} | parquet={result.get('storage', {}).get('status', 'not_run')}", flush=True)
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            parser.error(str(exc))
        print(f"Report: {args.output}")
    return int(any(not passed(item) for item in report["results"]))


if __name__ == "__main__":
    raise SystemExit(main())
