"""Parquet snapshots round-trip records and coverage without network access."""

import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from esd import (
    DatasetFormatError,
    DatasetIssue,
    DatasetMetadata,
    NormalizedMatch,
    NormalizedStanding,
    NormalizedTeam,
    SoccerDataset,
    open_dataset,
)

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")


@pytest.fixture
def dataset():
    timestamp = datetime(2024, 8, 16, 21, 0, 0, 123456, tzinfo=timezone.utc)
    return SoccerDataset(
        metadata=DatasetMetadata(
            source="espn", league="eng.1", season=2024,
            tables=("matches", "teams", "standings"),
            started_at=timestamp, finished_at=timestamp,
            calendar_dates=("2024-08-16", "2024-08-17"),
            successful_dates=("2024-08-16",), calendar_loaded=True,
            calendar_name="2024-25", calendar_type="day", standings_loaded=True,
            response_fetched_at=(("matches:2024-08-16", timestamp.isoformat()),),
            cached_tasks=("matches:2024-08-16",),
        ),
        match_records=(
            NormalizedMatch(source="espn", match_id="001", kickoff=timestamp,
                            home_team_id="001", home_score=0, away_score=None),
            NormalizedMatch(source="espn", match_id="002"),
        ),
        team_records=(NormalizedTeam(source="espn", team_id="001", name="Peñarol"),),
        standing_records=(NormalizedStanding(source="espn", team_id="001", points=0,
                                             goal_difference=-2, deductions=None),),
        errors=(DatasetIssue("matches", "2024-08-17", "SourceError", "Unavailable"),),
    )


def read_manifest(path):
    return json.loads((path / "manifest.json").read_text(encoding="utf-8"))


def write_manifest(path, manifest):
    (path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_round_trip_preserves_values_metadata_coverage_and_types(dataset, tmp_path):
    # '=' in a directory name must not create inferred Hive partition columns.
    destination = tmp_path / "league=eng.1" / "snapshot"
    assert dataset.save(destination) == destination
    restored = open_dataset(destination)
    assert restored == dataset
    assert not restored.complete
    assert restored.match_records[0].kickoff.microsecond == 123456
    assert restored.match_records[0].home_score == 0
    assert restored.match_records[0].away_score is None
    assert restored.match_records[1].kickoff is None
    assert restored.team_records[0].name == "Peñarol"
    assert restored.errors == dataset.errors
    pd = pytest.importorskip("pandas")
    for table in dataset.metadata.tables:
        pd.testing.assert_frame_equal(getattr(dataset, table), getattr(restored, table))


@pytest.mark.parametrize("tables", [("matches", "teams"), ("standings",)])
def test_empty_complete_snapshot_preserves_selected_tables(dataset, tmp_path, tables):
    metadata = replace(dataset.metadata, tables=tables, successful_dates=("2024-08-16", "2024-08-17"))
    empty = SoccerDataset(metadata)
    target = empty.save(tmp_path / "empty")
    restored = open_dataset(target)
    assert restored == empty
    assert restored.complete
    assert set(read_manifest(target)["tables"]) == set(tables)
    if "standings" not in tables:
        assert not (target / "standings.parquet").exists()


def test_existing_destination_is_not_modified(dataset, tmp_path):
    destination = dataset.save(tmp_path / "saved")
    manifest = (destination / "manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        dataset.save(destination)
    assert (destination / "manifest.json").read_bytes() == manifest
    assert open_dataset(destination) == dataset


def test_older_manifest_without_cache_provenance_still_opens(dataset, tmp_path):
    target = dataset.save(tmp_path / "older")
    manifest = read_manifest(target)
    manifest["metadata"].pop("response_fetched_at")
    manifest["metadata"].pop("cached_tasks")
    write_manifest(target, manifest)
    expected = replace(dataset, metadata=replace(dataset.metadata, response_fetched_at=(), cached_tasks=()))
    assert open_dataset(target) == expected


def test_failed_write_publishes_no_snapshot_and_cleans_staging(dataset, tmp_path, monkeypatch):
    original = pq.write_table
    calls = 0

    def failing_write(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("disk full")
        return original(*args, **kwargs)

    monkeypatch.setattr(pq, "write_table", failing_write)
    with pytest.raises(OSError, match="disk full"):
        dataset.save(tmp_path / "failed")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("change", ["version", "schema", "rows", "filename", "coverage", "errors"])
def test_invalid_manifest_is_rejected(dataset, tmp_path, change):
    target = dataset.save(tmp_path / "saved")
    manifest = read_manifest(target)
    if change == "version":
        manifest["storage_version"] = 99
    elif change == "schema":
        manifest["metadata"]["schema_version"] = "99"
    elif change == "rows":
        manifest["tables"]["matches"]["rows"] = 99
    elif change == "filename":
        manifest["tables"]["matches"]["file"] = "../outside.parquet"
    elif change == "coverage":
        manifest["metadata"]["successful_dates"] = ["2024-09-01"]
    else:
        manifest["errors"] = ""
    write_manifest(target, manifest)
    with pytest.raises(DatasetFormatError):
        open_dataset(target)


@pytest.mark.parametrize("damage", ["missing", "changed", "wrong_schema", "invalid_parquet"])
def test_damaged_tables_are_rejected(dataset, tmp_path, damage):
    target = dataset.save(tmp_path / "saved")
    file = target / "matches.parquet"
    if damage == "missing":
        file.unlink()
    elif damage == "changed":
        file.write_bytes(b"damaged")
    else:
        if damage == "wrong_schema":
            pq.write_table(pa.table({"unexpected": [1]}), file)
        else:
            file.write_bytes(b"not parquet")
        manifest = read_manifest(target)
        manifest["tables"]["matches"]["sha256"] = hashlib.sha256(file.read_bytes()).hexdigest()
        write_manifest(target, manifest)
    with pytest.raises(DatasetFormatError):
        open_dataset(target)


def test_unsupported_format_does_not_create_files(dataset, tmp_path):
    with pytest.raises(ValueError, match="parquet"):
        dataset.save(tmp_path / "wrong", format="csv")
    assert not list(tmp_path.iterdir())


def test_invalid_records_do_not_silently_change_type(dataset, tmp_path):
    invalid = replace(dataset, match_records=(NormalizedMatch(source="espn", home_score=1.5),))
    with pytest.raises(ValueError, match="integer"):
        invalid.save(tmp_path / "wrong")
    assert not list(tmp_path.iterdir())


def test_unselected_records_cannot_be_silently_discarded(dataset, tmp_path):
    invalid = replace(dataset, metadata=replace(dataset.metadata, tables=("standings",)))
    with pytest.raises(ValueError, match="Unselected"):
        invalid.save(tmp_path / "wrong")


def test_missing_directory_and_manifest_fail(tmp_path):
    with pytest.raises(FileNotFoundError):
        open_dataset(tmp_path / "missing")
    with pytest.raises(DatasetFormatError):
        open_dataset(tmp_path)


def test_parquet_save_and_open_work_without_pandas_or_timezone_database(tmp_path):
    code = '''
import importlib.abc
import sys
import zoneinfo
from datetime import datetime, timezone

class WithoutPandas(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in ("pandas", "pytz", "tzdata"):
            raise ModuleNotFoundError("Optional package blocked", name=fullname.split(".")[0])

sys.meta_path.insert(0, WithoutPandas())
zoneinfo.reset_tzpath(())
zoneinfo.ZoneInfo.clear_cache()
import esd
date = datetime(2024, 8, 16, tzinfo=timezone.utc)
metadata = esd.DatasetMetadata(source="espn", league="eng.1", season=2024,
                              tables=("matches",), started_at=date, finished_at=date)
dataset = esd.SoccerDataset(metadata, match_records=(
    esd.NormalizedMatch(source="espn", match_id="001", home_score=0, kickoff=date),
))
dataset.save(sys.argv[1])
assert esd.open_dataset(sys.argv[1]) == dataset
assert "pandas" not in sys.modules
assert "pytz" not in sys.modules and "tzdata" not in sys.modules
'''
    result = subprocess.run([sys.executable, "-c", code, str(tmp_path / "without-pandas")],
                            capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr
