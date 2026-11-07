"""Live check limits and reports tested with fake transports and processes."""

import runpy
import subprocess
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

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
    monkeypatch.setattr(esd, "load_dataset", lambda **kwargs: replace(base, errors=(error,)))
    report = CHECKS["probe"]("espn", "2026-11-07", 1)
    assert report["status"] == "blocked"
    assert not report["complete"]
    assert report["errors"][0]["error_type"] == "SourceBlocked"


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


def test_live_validation_rejects_missing_native_ids():
    dataset = replace(sample(), standing_records=(esd.NormalizedStanding(source="espn"),))
    with pytest.raises(ValueError, match="source identity"):
        CHECKS["inspect_dataset"](dataset)


def test_live_validation_rejects_naive_kickoffs():
    dataset = replace(
        sample(),
        metadata=replace(sample().metadata, tables=("matches",)),
        match_records=(esd.NormalizedMatch("espn", match_id="1", kickoff=datetime(2026, 11, 7)),),
    )
    with pytest.raises(ValueError, match="UTC"):
        CHECKS["inspect_dataset"](dataset)
