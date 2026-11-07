"""Live check limits and reports tested with fake transports and processes."""

import runpy
import subprocess
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import esd

CHECKS = runpy.run_path(str(Path(__file__).resolve().parent.parent / "scripts/check_sources.py"))


def sample():
    now = datetime(2026, 11, 7, tzinfo=timezone.utc)
    return esd.SoccerDataset(
        esd.DatasetMetadata(
            "espn",
            "eng.1",
            2024,
            ("standings",),
            now,
            now,
            expected_tasks=("standings:2024",),
            successful_tasks=("standings:2024",),
        ),
        standing_records=(esd.NormalizedStanding(source="espn", team_id="001"),),
    )


def test_live_report_keeps_source_block_separate_from_empty(monkeypatch):
    base = sample()
    error = esd.DatasetIssue("standings", "2024", "SourceBlocked", "Blocked")
    monkeypatch.setattr(esd, "load_dataset", lambda **kwargs: replace(
        base, metadata=replace(base.metadata, successful_tasks=()), errors=(error,),
    ))
    report = CHECKS["probe"]("espn", "2026-11-07", 1)
    assert report["status"] == "blocked"
    assert not report["complete"]
    assert report["errors"][0]["error_type"] == "SourceBlocked"
    assert report["validation"]["status"] == "warnings"
    assert not report["validation"]["errors"]


def test_empty_live_selection_is_not_an_error(monkeypatch):
    monkeypatch.setattr(
        esd, "load_dataset", lambda **kwargs: replace(sample(), standing_records=())
    )
    assert CHECKS["probe"]("espn", "2026-11-07", 1)["status"] == "empty"


def test_live_request_limit_bounds_transport_calls(monkeypatch):
    import httpx

    calls = []
    monkeypatch.setattr(
        httpx.Client, "request", lambda *a, **k: calls.append(k) or SimpleNamespace(status_code=200)
    )

    def load(**kwargs):
        httpx.Client.request(None, "GET", "https://example.test/first")
        httpx.Client.request(None, "GET", "https://example.test/second")

    monkeypatch.setattr(esd, "load_dataset", load)
    report = CHECKS["probe"]("espn", "2026-11-07", 1)
    assert len(calls) == len(report["requests"]) == 1
    assert calls[0]["timeout"] == 10
    assert "request limit" in report["message"]


def test_live_timeout_does_not_abort_other_sources(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", timeout)
    result = CHECKS["run_source"]("espn", "2026-11-07", 1, 1)
    assert result == {"source": "espn", "status": "timeout", "elapsed_seconds": 1}


def test_live_validation_reports_missing_native_ids_as_quality_warnings():
    dataset = replace(sample(), standing_records=(esd.NormalizedStanding(source="espn"),))
    assert CHECKS["inspect_dataset"](dataset) == {"standings": 1}
    report = CHECKS["validate_sample"](dataset)
    assert report["valid"] and report["status"] == "warnings"
    assert report["warnings"][0]["code"] == "missing_identifier"


def test_live_validation_reports_naive_kickoffs_as_quality_errors():
    dataset = replace(
        sample(),
        metadata=replace(sample().metadata, tables=("matches",)),
        match_records=(esd.NormalizedMatch("espn", match_id="1", kickoff=datetime(2026, 11, 7)),),
    )
    report = CHECKS["validate_sample"](dataset)
    assert not report["valid"] and report["status"] == "failed"
    assert report["errors"][0]["code"] == "invalid_record"


def test_quality_failure_does_not_replace_successful_download_status(monkeypatch):
    dataset = replace(sample(), standing_records=sample().standing_records * 2)
    monkeypatch.setattr(esd, "load_dataset", lambda **kwargs: dataset)
    report = CHECKS["probe"]("espn", "2026-11-07", 1)
    assert report["status"] == "ok" and report["complete"]
    assert not report["errors"]
    assert report["validation"]["status"] == "failed"
    assert report["validation"]["errors"][0]["code"] == "duplicate_key"
    assert not CHECKS["passed"](report)


def test_validator_exception_is_separate_from_download(monkeypatch):
    monkeypatch.setattr(esd, "load_dataset", lambda **kwargs: sample())
    monkeypatch.setattr(esd, "validate_dataset", Mock(side_effect=RuntimeError("Sample validation bug")))
    report = CHECKS["probe"]("espn", "2026-11-07", 1)
    assert report["status"] == "ok"
    assert report["validation"]["status"] == "error"
    assert "Sample validation bug" in report["validation"]["message"]
    assert not CHECKS["passed"](report)


@pytest.mark.parametrize("kind", ["complete", "empty", "partial"])
def test_parquet_check_preserves_records_metadata_errors_and_complete(monkeypatch, tmp_path, kind):
    pytest.importorskip("pyarrow")
    dataset = sample()
    if kind == "empty":
        dataset = replace(dataset, standing_records=())
    elif kind == "partial":
        dataset = replace(
            dataset, metadata=replace(dataset.metadata, successful_tasks=()),
            errors=(esd.DatasetIssue("standings", "2024", "SourceBlocked", "Sample source block"),),
        )
    monkeypatch.setattr(esd, "load_dataset", lambda **kwargs: dataset)
    destination = tmp_path / "chosen snapshot"
    report = CHECKS["probe"]("espn", "2026-11-07", 1, destination)
    assert report["storage"]["status"] == "passed"
    assert all(report["storage"]["checks"].values())
    assert esd.open_dataset(destination) == dataset
    assert report["status"] == {"complete": "ok", "empty": "empty", "partial": "blocked"}[kind]
    assert CHECKS["passed"](report) == (kind != "partial")


def test_storage_mismatch_is_separate_from_download(monkeypatch, tmp_path):
    pytest.importorskip("pyarrow")
    monkeypatch.setattr(esd, "load_dataset", lambda **kwargs: sample())
    monkeypatch.setattr(esd, "open_dataset", lambda path: replace(sample(), standing_records=()))
    report = CHECKS["probe"]("espn", "2026-11-07", 1, tmp_path / "snapshot")
    assert report["status"] == "ok" and report["validation"]["status"] == "passed"
    assert report["storage"]["status"] == "failed"
    assert not report["storage"]["checks"]["records_equal"]
    assert not CHECKS["passed"](report)


def test_failed_snapshot_write_is_reported_without_losing_download(monkeypatch, tmp_path):
    monkeypatch.setattr(esd, "load_dataset", lambda **kwargs: sample())
    monkeypatch.setattr(esd.SoccerDataset, "save", Mock(side_effect=OSError("disk full")))
    report = CHECKS["probe"]("espn", "2026-11-07", 1, tmp_path / "snapshot")
    assert report["status"] == "ok"
    assert report["storage"]["status"] == "error"
    assert report["storage"]["message"] == "disk full"
    assert not CHECKS["passed"](report)
    assert list(tmp_path.iterdir()) == []


def test_snapshot_path_is_forwarded_to_worker(monkeypatch, tmp_path):
    runner = Mock(return_value=SimpleNamespace(returncode=0, stdout='{"source":"espn","status":"ok"}'))
    monkeypatch.setattr(subprocess, "run", runner)
    CHECKS["run_source"]("espn", "2026-11-07", 45, 3, tmp_path)
    command = runner.call_args.args[0]
    assert command[-2:] == ["--snapshot-dir", str(tmp_path)]
    assert runner.call_args.kwargs["timeout"] == 45


@pytest.mark.parametrize("payload", ["[]", "null", "bad JSON", '{"source":"fbref","status":"ok"}'])
def test_invalid_worker_output_is_reported(monkeypatch, payload):
    monkeypatch.setattr(subprocess, "run", Mock(return_value=SimpleNamespace(returncode=0, stdout=payload)))
    result = CHECKS["run_source"]("espn", "2026-11-07", 45, 3)
    assert result["status"] == "error"
    assert "valid JSON report" in result["message"]


@pytest.mark.parametrize("flag", ["--check-parquet", "--snapshot-dir"])
def test_optional_dependency_is_checked_before_any_query(monkeypatch, tmp_path, flag):
    main = CHECKS["main"]
    runner = Mock(side_effect=AssertionError("Unexpected source query"))
    monkeypatch.setitem(main.__globals__, "find_spec", lambda name: None)
    monkeypatch.setitem(main.__globals__, "run_source", runner)
    arguments = [flag] if flag == "--check-parquet" else [flag, str(tmp_path / "snapshots")]
    with pytest.raises(SystemExit) as exc:
        main(arguments)
    assert exc.value.code == 2
    assert list(tmp_path.iterdir()) == []
    runner.assert_not_called()


def test_existing_snapshot_root_is_not_modified(monkeypatch, tmp_path):
    main = CHECKS["main"]
    root = tmp_path / "existing"
    root.mkdir()
    marker = root / "keep"
    marker.write_text("original", encoding="utf-8")
    runner = Mock(side_effect=AssertionError("Unexpected source query"))
    monkeypatch.setitem(main.__globals__, "find_spec", lambda name: object())
    monkeypatch.setitem(main.__globals__, "run_source", runner)
    with pytest.raises(SystemExit) as exc:
        main(["--snapshot-dir", str(root)])
    assert exc.value.code == 2
    assert marker.read_text(encoding="utf-8") == "original"
    runner.assert_not_called()


@pytest.mark.parametrize("retained", [False, True])
def test_main_cleans_temporary_snapshots_but_keeps_requested_data(monkeypatch, tmp_path, retained):
    main = CHECKS["main"]
    locations = []

    def run(source, day, timeout, max_requests, root):
        locations.append(root)
        path = root / source
        path.mkdir()
        (path / "sample").write_text("source data", encoding="utf-8")
        return {"source": source, "status": "ok", "validation": {"status": "warnings"},
                "storage": {"status": "passed", "path": str(path), "retained": True}}

    monkeypatch.setitem(main.__globals__, "find_spec", lambda name: object())
    monkeypatch.setitem(main.__globals__, "run_source", run)
    output = tmp_path / "report.json"
    options = ["--snapshot-dir", str(tmp_path / "chosen-root")] if retained else ["--check-parquet"]
    assert main(["--source", "espn", "--output", str(output), *options]) == 0
    import json

    report = json.loads(output.read_text(encoding="utf-8"))
    storage = report["results"][0]["storage"]
    assert locations[0].exists() == retained
    assert storage["retained"] == retained
    assert (storage["path"] is not None) == retained


def test_temporary_snapshot_root_is_cleaned_on_worker_timeout(monkeypatch):
    main = CHECKS["main"]
    locations = []

    def timeout(source, day, timeout, max_requests, root):
        locations.append(root)
        (root / "staging").mkdir()
        return {"source": source, "status": "timeout"}

    monkeypatch.setitem(main.__globals__, "find_spec", lambda name: object())
    monkeypatch.setitem(main.__globals__, "run_source", timeout)
    assert main(["--source", "espn", "--check-parquet"]) == 1
    assert not locations[0].exists()
