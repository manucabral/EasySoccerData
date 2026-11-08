"""Coverage CLI preserves snapshots, reports partial tasks and publishes new JSON."""

import json
import runpy
from pathlib import Path
from unittest.mock import Mock

import pytest

import esd

ROOT = Path(__file__).resolve().parent.parent / "examples/datasets"


@pytest.fixture
def example(monkeypatch):
    fetch = Mock(side_effect=AssertionError("Coverage must not request sources"))
    monkeypatch.setattr("esd._provider_datasets.get_api_json", fetch)
    return runpy.run_path(str(ROOT / "coverage.py")), fetch


def test_contract_query_and_json_need_no_source_requests(example, tmp_path, capsys):
    module, fetch = example
    target = tmp_path / "caller" / "fields.json"
    assert module["main"](["--source", "espn", "--table", "shots", "--output-json", str(target)]) == 0
    doc = json.loads(target.read_text(encoding="utf-8"))
    xg = next(field for field in doc["fields"] if field["field"] == "xg")
    assert doc["format"] == "easysoccerdata-field-contracts" and xg["support"] == "unavailable"
    assert "espn-native-field" in capsys.readouterr().out
    fetch.assert_not_called()


def test_partial_snapshot_reports_counts_and_errors_without_modifying_files(example, tmp_path, capsys):
    pytest.importorskip("pyarrow")
    module, fetch = example
    fixture = runpy.run_path(str(ROOT / "coverage_offline.py"))["fixture"]()
    target = fixture.save(tmp_path / "snapshot")
    before = {path.name: path.read_bytes() for path in target.iterdir()}
    output = tmp_path / "report.json"
    assert module["main"](["--open-dir", str(target), "--table", "lineups", "--output-json", str(output)]) == 1
    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["complete"] is False and len(document["tables"]) == 1
    assert document["tables"][0]["task_status"] == "partial"
    assert "SourceBlocked" in capsys.readouterr().err
    assert before == {path.name: path.read_bytes() for path in target.iterdir()}
    assert esd.open_dataset(target) == fixture
    fetch.assert_not_called()


def test_existing_output_is_not_replaced_and_publication_failures_clean_staging(example, tmp_path, monkeypatch):
    module, _ = example
    target = tmp_path / "existing.json"
    target.write_text("caller data", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        module["main"](["--source", "espn", "--output-json", str(target)])
    assert exc.value.code == 2 and target.read_text(encoding="utf-8") == "caller data"
    monkeypatch.setattr(module["os"], "link", Mock(side_effect=OSError("Publication unavailable")))
    with pytest.raises(OSError):
        module["write_report"](tmp_path / "new.json", {"report": True})
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize("options", [[], ["--source", "espn", "--pandas"],
                                      ["--source", "scores365", "--table", "shots"],
                                      ["--source", "unknown"], ["--source", "espn", "--open-dir", "saved"]])
def test_invalid_selections_fail_without_source_access(example, options):
    module, fetch = example
    with pytest.raises(SystemExit) as exc:
        module["main"](options)
    assert exc.value.code == 2
    fetch.assert_not_called()
