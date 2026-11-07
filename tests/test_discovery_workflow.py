"""Discovery-to-snapshot workflow checks native selection and errors before writes."""

import runpy
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

import esd
from esd import _provider_datasets, discovery

ROOT = Path(__file__).resolve().parent.parent / "examples/datasets"
OPTIONS = ["--season-id", "74", "--start-date", "2026-11-03", "--end-date", "2026-11-03"]


@pytest.fixture
def workflow(monkeypatch):
    example = runpy.run_path(str(ROOT / "discovery_workflow_offline.py"))
    fetch = Mock(side_effect=example["responses"])
    monkeypatch.setattr(discovery, "get_api_json", fetch)
    monkeypatch.setattr(_provider_datasets, "get_api_json", fetch)
    return runpy.run_path(str(ROOT / "discover_and_download.py")), fetch


def test_import_and_help_do_not_fetch(workflow):
    module, fetch = workflow
    with pytest.raises(SystemExit) as exc:
        module["main"](["--help"])
    assert exc.value.code == 0
    fetch.assert_not_called()


def test_native_discovery_download_cache_and_snapshot_round_trip(workflow, tmp_path, capsys):
    pytest.importorskip("pyarrow")
    module, fetch = workflow
    destination = tmp_path / "snapshot"
    options = OPTIONS + ["--cache-dir", str(tmp_path / "cache")]
    assert module["main"](options + ["--output-dir", str(destination)]) == 0
    assert fetch.call_count == 4
    restored = esd.open_dataset(destination)
    assert restored.complete and esd.validate_dataset(restored).valid
    assert restored.metadata.source_season_id == "74" and restored.metadata.season == 2026
    assert len(restored.match_records) == len(restored.standing_records) == 1
    assert restored.match_records[0].home_score == 1 and restored.match_records[0].away_score == 0
    assert restored.match_records[0].source_season_id == "74"
    fetch.side_effect = AssertionError("Unexpected HTTP")
    assert module["main"](options) == 0
    assert module["main"](["--open-dir", str(destination)]) == 0
    assert fetch.call_count == 4
    assert "Saved and verified:" in capsys.readouterr().out


@pytest.mark.parametrize("options", [
    [], ["--season-id", "2026"], ["--competition-id", "999"],
])
def test_missing_or_unlisted_native_selection_does_not_download(workflow, monkeypatch, options):
    module, fetch = workflow
    download = Mock(side_effect=AssertionError("Unexpected dataset download"))
    monkeypatch.setattr(esd, "load_dataset", download)
    arguments = [] if not options else OPTIONS + options
    with pytest.raises(SystemExit) as exc:
        module["main"](arguments)
    assert exc.value.code == 2
    download.assert_not_called()
    assert fetch.call_count <= 2


@pytest.mark.parametrize("options", [
    ["--start-date", "2026-11-04", "--end-date", "2026-11-03"],
    ["--start-date", "2026-11-01", "--end-date", "2026-11-08"],
    ["--start-date", "2026-1-03"], ["--season", "26"],
    ["--competition-id", "-1"], ["--season-id", "74x"],
    ["--query", ""], ["--start-date", ""],
    ["--open-dir", "snapshot", "--refresh"],
])
def test_bad_arguments_fail_before_discovery(workflow, options):
    module, fetch = workflow
    with pytest.raises(SystemExit) as exc:
        module["main"](OPTIONS + options)
    assert exc.value.code == 2
    fetch.assert_not_called()


def test_missing_arrow_and_existing_destination_fail_before_discovery(workflow, tmp_path):
    module, fetch = workflow
    module["main"].__globals__["find_spec"] = lambda name: None
    with pytest.raises(SystemExit) as exc:
        module["main"](OPTIONS + ["--output-dir", str(tmp_path / "new")])
    assert exc.value.code == 2
    with pytest.raises(SystemExit):
        module["main"](OPTIONS + ["--output-dir", str(tmp_path)])
    fetch.assert_not_called()


def test_source_block_returns_failure_instead_of_empty_success(workflow, capsys):
    module, fetch = workflow
    fetch.side_effect = esd.SourceBlocked("Sample challenge")
    assert module["main"](OPTIONS) == 1
    assert "SourceBlocked" in capsys.readouterr().err


def test_partial_dataset_snapshot_retains_errors_and_nonzero_exit(workflow, tmp_path):
    pytest.importorskip("pyarrow")
    module, fetch = workflow
    original = fetch.side_effect

    def partial(url, **kwargs):
        if "/games/" in url:
            raise esd.SourceBlocked("Sample source block")
        return original(url, **kwargs)

    fetch.side_effect = partial
    destination = tmp_path / "partial"
    assert module["main"](OPTIONS + ["--output-dir", str(destination)]) == 1
    restored = esd.open_dataset(destination)
    assert not restored.complete and len(restored.errors) == 1
    assert restored.errors[0].error_type == "SourceBlocked"
    assert esd.validate_dataset(restored).valid


def test_quality_errors_prevent_snapshot_write(workflow, tmp_path, capsys, monkeypatch):
    pytest.importorskip("pyarrow")
    module, _ = workflow
    original = esd.load_dataset

    def invalid(**kwargs):
        dataset = original(**kwargs)
        return replace(dataset, match_records=(replace(dataset.match_records[0], home_score=-1),))

    monkeypatch.setattr(esd, "load_dataset", invalid)
    destination = tmp_path / "invalid"
    assert module["main"](OPTIONS + ["--output-dir", str(destination)]) == 1
    assert not destination.exists()
    assert "negative_score" in capsys.readouterr().err
