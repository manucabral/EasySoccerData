"""Versioned Parquet snapshots. Optional Arrow imports stay inside I/O calls."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import tempfile
from dataclasses import asdict, fields
from datetime import datetime, timezone
from pathlib import Path

from .datasets import DatasetFormatError, DatasetIssue, DatasetMetadata, SoccerDataset
from .normalized import SCHEMA_VERSION
from .normalized.schema import FLOAT_COLUMNS, INTEGER_COLUMNS, TABLE_MODELS

_FORMAT = "easysoccerdata-parquet"
_STORAGE_VERSION = 1
_RECORDS = {
    "matches": "match_records", "teams": "team_records", "standings": "standing_records",
    "match_stats": "match_stat_records", "player_stats": "player_stat_records", "shots": "shot_records",
    "players": "player_records", "market_values": "market_value_records", "transfers": "transfer_records",
}


def _arrow():
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ModuleNotFoundError as exc:
        if exc.name != "pyarrow" and not (exc.name or "").startswith("pyarrow."):
            raise
        raise ImportError(
            'Dataset storage requires pyarrow. Install it with pip install "EasySoccerData[parquet]".'
        ) from exc
    return pa, pq


def _schema(pa, table):
    return pa.schema([
        (field.name, pa.timestamp("us", tz="UTC") if field.name == "kickoff" else
         pa.int64() if field.name in INTEGER_COLUMNS else
         pa.float64() if field.name in FLOAT_COLUMNS else pa.string())
        for field in fields(TABLE_MODELS[table])
    ])


def _checksum(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc(value):
    date = datetime.fromisoformat(value)
    if date.tzinfo is None or date.utcoffset() is None:
        raise ValueError("Snapshot timestamps must include a timezone")
    return date.astimezone(timezone.utc)


def _metadata(data):
    meta = dict(data)
    meta.setdefault("cached_tasks", [])
    meta.setdefault("response_fetched_at", [])
    for key in ("expected_tasks", "successful_tasks", "requested_match_ids", "requested_club_ids", "requested_player_ids"):
        meta.setdefault(key, [])
    for key in ("started_at", "finished_at"):
        meta[key] = _utc(meta[key])
    for key in ("tables", "calendar_dates", "successful_dates", "cached_tasks",
                "expected_tasks", "successful_tasks", "requested_match_ids", "requested_club_ids", "requested_player_ids"):
        if not isinstance(meta[key], list) or any(not isinstance(item, str) for item in meta[key]):
            raise ValueError(f"Invalid {key}")
        if len(set(meta[key])) != len(meta[key]):
            raise ValueError(f"Duplicate {key}")
        meta[key] = tuple(meta[key])
    response_times = meta["response_fetched_at"]
    if not isinstance(response_times, list) or any(
        not isinstance(item, list) or len(item) != 2
        or not all(isinstance(value, str) for value in item) for item in response_times
    ):
        raise ValueError("Invalid response timestamps")
    if len({item[0] for item in response_times}) != len(response_times):
        raise ValueError("Duplicate response timestamps")
    for _, timestamp in response_times:
        _utc(timestamp)
    meta["response_fetched_at"] = tuple(tuple(item) for item in response_times)
    if not set(meta["cached_tasks"]) <= {item[0] for item in response_times}:
        raise ValueError("Cached tasks are missing their response timestamps")
    result = DatasetMetadata(**meta)
    if result.schema_version != SCHEMA_VERSION:
        raise ValueError(f"Unsupported schema version: {result.schema_version}")
    if not result.tables or any(table not in TABLE_MODELS for table in result.tables):
        raise ValueError("Invalid table selection")
    if any(not isinstance(value, str) or not value for value in (result.source, result.league)):
        raise ValueError("Source and league are required")
    if type(result.season) is not int or not 1000 <= result.season <= 9999:
        raise ValueError("Invalid season year")
    if type(result.calendar_loaded) is not bool or type(result.standings_loaded) is not bool:
        raise ValueError("Invalid coverage flags")
    if result.finished_at < result.started_at:
        raise ValueError("Invalid snapshot timestamps")
    for day in (*result.calendar_dates, *result.successful_dates):
        if datetime.strptime(day, "%Y-%m-%d").date().isoformat() != day:
            raise ValueError("Invalid calendar day")
    if not set(result.successful_dates) <= set(result.calendar_dates):
        raise ValueError("Successful dates are not in the source calendar")
    if not result.calendar_loaded and (result.calendar_dates or result.successful_dates):
        raise ValueError("Dates exist without a loaded calendar")
    if not set(result.successful_tasks) <= set(result.expected_tasks):
        raise ValueError("Successful tasks are outside the query scope")
    if result.coverage_scope not in ("season", "date_range", "entities"):
        raise ValueError("Invalid coverage scope")
    for name in ("source_season_id", "start_date", "end_date", "source_timezone", "source_season"):
        if getattr(result, name) is not None and not isinstance(getattr(result, name), str):
            raise ValueError(f"Invalid {name}")
    return result


def _metadata_json(metadata):
    data = asdict(metadata)
    for key in ("started_at", "finished_at"):
        data[key] = data[key].isoformat()
    # Normalize tuples exactly as a JSON manifest will represent them.
    return json.loads(json.dumps(data))


def _validate_records(records, table):
    model = TABLE_MODELS[table]
    for record in records:
        if not isinstance(record, model):
            raise ValueError(f"Invalid record model for {table}")
        for field in fields(model):
            value = getattr(record, field.name)
            if value is None:
                if field.name == "source":
                    raise ValueError("Record source is required")
                continue
            if field.name == "kickoff":
                if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
                    raise ValueError("Kickoff must be a timezone-aware datetime")
            elif field.name in INTEGER_COLUMNS:
                if type(value) is not int:
                    raise ValueError(f"{field.name} must be an integer or None")
            elif field.name in FLOAT_COLUMNS:
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise ValueError(f"{field.name} must be a finite number or None")
            elif not isinstance(value, str):
                raise ValueError(f"{field.name} must be a string or None")


def save_dataset(dataset, path, *, format="parquet"):
    if format != "parquet":
        raise ValueError("Only format='parquet' is supported")
    target = Path(path).absolute()
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"Dataset destination already exists: {target}")
    pa, pq = _arrow()
    metadata = _metadata_json(dataset.metadata)
    _metadata(metadata)
    for table, attribute in _RECORDS.items():
        records = getattr(dataset, attribute)
        if records and table not in dataset.metadata.tables:
            raise ValueError(f"Unselected table {table} contains records")
        _validate_records(records, table)
    for issue in dataset.errors:
        if not isinstance(issue, DatasetIssue) or any(
            not isinstance(value, str) for value in asdict(issue).values()
        ):
            raise ValueError("Invalid dataset issue")
    target.parent.mkdir(parents=True, exist_ok=True)
    parent = target.parent.resolve()
    target = parent / target.name
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=parent)).resolve()
    try:
        tables = {}
        for table in dataset.metadata.tables:
            records = getattr(dataset, _RECORDS[table])
            arrow_table = pa.Table.from_pylist([asdict(record) for record in records],
                                             schema=_schema(pa, table))
            filename = f"{table}.parquet"
            pq.write_table(arrow_table, staging / filename, compression="snappy")
            tables[table] = {"file": filename, "rows": len(records),
                             "sha256": _checksum(staging / filename)}
        manifest = {
            "format": _FORMAT, "storage_version": _STORAGE_VERSION,
            "metadata": metadata, "errors": [asdict(issue) for issue in dataset.errors],
            "tables": tables,
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"Dataset destination already exists: {target}")
        os.rename(staging, target)
    finally:
        # Only remove the temporary directory created directly under this parent.
        if staging.parent == parent and staging.exists():
            shutil.rmtree(staging)
    return target


def read_dataset(path):
    root = Path(path)
    if not root.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {root}")
    pa, pq = _arrow()
    try:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        if manifest["format"] != _FORMAT or type(manifest["storage_version"]) is not int:
            raise ValueError("Not an EasySoccerData snapshot")
        if manifest["storage_version"] != _STORAGE_VERSION:
            raise ValueError(f"Unsupported storage version: {manifest['storage_version']}")
        metadata = _metadata(manifest["metadata"])
        if set(manifest["tables"]) != set(metadata.tables):
            raise ValueError("Manifest tables do not match requested tables")
        if not isinstance(manifest["errors"], list):
            raise ValueError("Invalid dataset issues list")
        errors = tuple(DatasetIssue(**issue) for issue in manifest["errors"])
        if any(not isinstance(value, str) for issue in errors for value in asdict(issue).values()):
            raise ValueError("Invalid dataset issue")
        records = {}
        for table in metadata.tables:
            entry = manifest["tables"][table]
            if entry["file"] != f"{table}.parquet":
                raise ValueError(f"Invalid filename for {table}")
            filename = root / entry["file"]
            if filename.is_symlink() or _checksum(filename) != entry["sha256"]:
                raise ValueError(f"Checksum mismatch or invalid file for {table}")
            with pq.ParquetFile(filename) as reader:
                arrow_table = reader.read()
            if not arrow_table.schema.equals(_schema(pa, table), check_metadata=False):
                raise ValueError(f"Invalid Parquet schema for {table}")
            if type(entry["rows"]) is not int or arrow_table.num_rows != entry["rows"]:
                raise ValueError(f"Row count mismatch for {table}")
            if table == "matches":
                # Schema validation already established UTC. Materialize naive UTC
                # values to avoid Arrow consulting optional timezone databases.
                index = arrow_table.schema.get_field_index("kickoff")
                arrow_table = arrow_table.set_column(
                    index, "kickoff", arrow_table.column(index).cast(pa.timestamp("us")),
                )
            values = arrow_table.to_pylist()
            if table == "matches":
                for row in values:
                    if row["kickoff"] is not None:
                        row["kickoff"] = row["kickoff"].replace(tzinfo=timezone.utc)
            rows = tuple(TABLE_MODELS[table](**row) for row in values)
            _validate_records(rows, table)
            records[_RECORDS[table]] = rows
        return SoccerDataset(metadata=metadata, errors=errors, **records)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise DatasetFormatError(f"Invalid dataset at {root}: {exc}") from exc
