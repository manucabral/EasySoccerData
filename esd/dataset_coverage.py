"""Read-only normalized field presence and source-task coverage."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime

from ._dataset_storage import _RECORDS
from .dataset_fields import DatasetFieldCapability, get_dataset_field_capabilities
from .dataset_validation import DatasetValidationReport, validate_dataset
from .datasets import DatasetIssue, DatasetMetadata, SoccerDataset


@dataclass(frozen=True)
class DatasetFieldCoverage:
    """Counts in existing normalized rows, independent of task success.

    Empty tables have no presence ratio. Numeric zeros count as present;
    boolean False has its own counter and never counts as numeric zero.
    Parser defaults already in normalized records cannot be identified as raw
    observations. Counts do not describe omitted source rows or fixtures.
    """

    capability: DatasetFieldCapability
    row_count: int
    present_count: int
    missing_count: int
    zero_count: int | None
    true_count: int | None
    false_count: int | None
    blank_count: int | None = None

    @property
    def table(self) -> str:
        return self.capability.table

    @property
    def field(self) -> str:
        return self.capability.field

    @property
    def present_ratio(self) -> float | None:
        """Fraction of normalized rows containing a value, or None without rows."""
        return self.present_count / self.row_count if self.row_count else None

    @property
    def status(self) -> str:
        """empty, missing, partial or populated; not a download-success state."""
        return ("empty" if not self.row_count else "missing" if not self.present_count
                else "partial" if self.missing_count else "populated")

    @property
    def unmapped_values(self) -> bool:
        """Values exist in a column the current adapter does not populate.

        Caller enrichment or an older adapter can account for such values;
        this does not establish that the current provider supplies the field.
        """
        return self.capability.support == "unavailable" and self.present_count > 0


@dataclass(frozen=True)
class DatasetTaskCoverage:
    """One recorded task, its original observation date and unmodified errors."""

    key: str
    status: str
    cached: bool
    fetched_at: datetime | None
    errors: tuple[DatasetIssue, ...] = ()


@dataclass(frozen=True)
class DatasetTableCoverage:
    """Selected table size and relevant recorded tasks, including prerequisites.

    task_status is complete, partial, failed, pending or unknown. unknown means
    the metadata has no relevant evidence. A complete task set with zero rows
    is distinguishable from failed/pending tasks; neither proves exhaustive
    provider coverage. Dependencies can appear in more than one table.
    """

    table: str
    row_count: int
    task_keys: tuple[str, ...]
    task_status: str


@dataclass(frozen=True)
class DatasetCoverageReport:
    """Adapter contracts, existing row counts and recorded download outcomes.

    complete retains the dataset's overall task result, including uninspected
    tables. Per-table task_status is separate from non-null field presence.
    The report makes no source request, infers no missing rows and changes no
    normalized values or snapshot schema. Recompute it after opening a snapshot.
    """

    metadata: DatasetMetadata
    complete: bool
    tables: tuple[DatasetTableCoverage, ...]
    fields: tuple[DatasetFieldCoverage, ...]
    tasks: tuple[DatasetTaskCoverage, ...]
    errors: tuple[DatasetIssue, ...]
    validation: DatasetValidationReport
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        """Versioned JSON-compatible report, preserving source scope and dates."""
        document = json.loads(json.dumps(asdict(self), default=lambda value: value.isoformat(), allow_nan=False))
        document.update(format="easysoccerdata-coverage", format_version=1)
        for result, row in zip(document["fields"], self.fields):
            result.update(status=row.status, present_ratio=row.present_ratio, unmapped_values=row.unmapped_values)
        return document

    def to_dataframe(self):
        """Field counts with nullable types. Only this method requires pandas."""
        try:
            import pandas as pd
        except ModuleNotFoundError as exc:
            if exc.name != "pandas":
                raise
            raise ImportError("Coverage report DataFrames require EasySoccerData[pandas].") from exc
        rows = []
        for row in self.fields:
            value = asdict(row.capability)
            value["notes"] = " ".join(row.capability.notes)
            value.update(row_count=row.row_count, present_count=row.present_count, missing_count=row.missing_count,
                         zero_count=row.zero_count, true_count=row.true_count, false_count=row.false_count, blank_count=row.blank_count,
                         present_ratio=row.present_ratio, status=row.status, unmapped_values=row.unmapped_values)
            rows.append(value)
        dtypes = dict.fromkeys(("source", "table", "field", "dtype", "support", "unit", "model", "coordinate_system", "notes", "status"), "string")
        dtypes.update(dict.fromkeys(("row_count", "present_count", "missing_count", "zero_count", "true_count", "false_count", "blank_count"), "Int64"))
        dtypes.update(present_ratio="Float64", unmapped_values="boolean")
        return pd.DataFrame(rows, columns=list(dtypes)).astype(dtypes)


def _task_steps(source, table, metadata):
    if source == "transfermarkt":
        return {table}
    if source == "goaloo":
        return {"season"}
    if source == "understat":
        return {"player_stats"} if table == "player_stats" else {"season", "shots"} if table == "shots" else {"season"}
    if source in ("fbref", "promiedos", "besoccer"):
        return {"standings"} if table == "standings" else {"matches"}
    if table == "standings":
        return {"standings"}
    if source == "espn":
        if metadata.coverage_scope == "match_ids":
            return {"match_details", "match_stats"} if table in ("matches", "teams", "match_stats") else {"match_details"}
        return {"calendar", "matches"}
    if source == "sofascore":
        if table in ("matches", "teams"):
            return {"matches", "match"}
        return {"match", "lineups" if table in ("lineups", "player_match_stats") else table}
    if table in ("matches", "teams"):
        return {"matches", "lineups", "match_events", "match_stats"}
    if table in ("lineups", "player_match_stats"):
        return {"lineups"}
    return {"lineups", "match_events"} if table == "match_events" else {table}


def _tasks(dataset):
    metadata = dataset.metadata
    expected, successful = list(metadata.expected_tasks), set(metadata.successful_tasks)
    issues = defaultdict(list)
    for issue in dataset.errors:
        issues[f"{issue.step}:{issue.target}"].append(issue)
    # ESPN season downloads predate expected_tasks; retain their calendar flags.
    if metadata.source == "espn" and not expected:
        if metadata.calendar_loaded:
            key = f"calendar:{metadata.season}"
            expected.append(key)
            successful.add(key)
        expected.extend(f"matches:{day}" for day in metadata.calendar_dates)
        successful.update(f"matches:{day}" for day in metadata.successful_dates)
        if metadata.standings_loaded:
            key = f"standings:{metadata.season}"
            expected.append(key)
            successful.add(key)
    timestamps = dict(metadata.response_fetched_at)
    keys = dict.fromkeys([*expected, *sorted(successful), *timestamps, *issues])
    return tuple(DatasetTaskCoverage(
        key, "failed" if key in issues else "successful" if key in successful else "pending",
        key in metadata.cached_tasks, datetime.fromisoformat(timestamps[key]) if key in timestamps else None,
        tuple(issues[key]),
    ) for key in keys)


def _task_status(tasks):
    statuses = {task.status for task in tasks}
    if not statuses:
        return "unknown"
    if statuses == {"successful"}:
        return "complete"
    if statuses == {"failed"}:
        return "failed"
    return "pending" if statuses == {"pending"} else "partial"


def _table_task_status(source, table, relevant, metadata):
    primary = relevant
    # A context read alone cannot turn a failed detail endpoint into partial data.
    if source == "sofascore" and table not in ("matches", "teams", "standings"):
        primary = tuple(task for task in relevant if not task.key.startswith("match:"))
        if not primary:
            return "unknown"
    if source == "understat" and table == "shots" and metadata.requested_match_ids:
        primary = tuple(task for task in relevant if task.key.startswith("shots:"))
    if metadata.requested_match_ids and (metadata.coverage_scope == "match_ids" or source == "understat" and table == "shots"):
        recorded_ids = {task.key.split(":", 1)[1] for task in primary}
        if not set(metadata.requested_match_ids) <= recorded_ids:
            return "partial" if primary else "unknown"
    status = _task_status(primary)
    if status == "complete" and any(task.status != "successful" for task in relevant):
        return "partial"
    return status


def inspect_dataset_coverage(dataset: SoccerDataset, *, tables: Sequence[str] | None = None) -> DatasetCoverageReport:
    """Inspect selected normalized tables without HTTP, writes or optional imports.

    None inspects every selected table. An explicit nonempty sequence must name
    tables present in the dataset. Unsupported source/table pairs and invalid
    datasets raise ValueError; non-dataset inputs raise TypeError. Warnings,
    partial downloads and successful empty tables remain reportable.

    Counts use normalized values: None is missing, numeric zero is present,
    and boolean False is counted separately. Adapter defaults or manual edits
    cannot be distinguished from source observations without raw provenance.
    Tasks retain recorded errors/cache dates and source-specific prerequisites.
    Unknown metadata stays unknown, even if rows exist or complete is True.
    """
    if not isinstance(dataset, SoccerDataset):
        raise TypeError("Expected a SoccerDataset")
    validation = validate_dataset(dataset)
    if not validation.valid:
        raise ValueError("Coverage requires a valid dataset: " + ", ".join(dict.fromkeys(issue.code for issue in validation.errors)))
    if tables is None:
        selected = dataset.metadata.tables
    elif (not isinstance(tables, Sequence) or isinstance(tables, (str, bytes)) or not tables
          or any(not isinstance(table, str) or table not in dataset.metadata.tables for table in tables)):
        raise ValueError("tables must be a nonempty sequence of tables selected in the dataset")
    else:
        selected = tuple(dict.fromkeys(tables))
    tasks = _tasks(dataset)
    table_results, field_results = [], []
    for table in selected:
        capabilities = get_dataset_field_capabilities(dataset.metadata.source, table)
        records = getattr(dataset, _RECORDS[table])
        steps = _task_steps(dataset.metadata.source, table, dataset.metadata)
        relevant = tuple(task for task in tasks if ":" in task.key and task.key.split(":", 1)[0] in steps)
        table_results.append(DatasetTableCoverage(table, len(records), tuple(task.key for task in relevant),
                                                  _table_task_status(dataset.metadata.source, table, relevant, dataset.metadata)))
        for capability in capabilities.values():
            numeric, boolean = capability.dtype in ("Int64", "Float64"), capability.dtype == "boolean"
            strings = capability.dtype == "string"
            present = zeros = trues = falses = blanks = 0
            for row in records:
                value = getattr(row, capability.field)
                if value is not None:
                    present += 1
                    if numeric and value == 0:
                        zeros += 1
                    elif boolean:
                        trues += value is True
                        falses += value is False
                    elif strings and not value.strip():
                        blanks += 1
            field_results.append(DatasetFieldCoverage(capability, len(records), present, len(records) - present,
                                                       zeros if numeric else None, trues if boolean else None,
                                                       falses if boolean else None, blanks if strings else None))
    return DatasetCoverageReport(dataset.metadata, dataset.complete, tuple(table_results), tuple(field_results), tasks,
                                 tuple(dataset.errors), validation, (
                                     "Field presence counts non-null normalized values, including blank strings, not raw source availability; parser defaults cannot be recovered.",
                                     "Task completion does not prove complete league, fixture, player or attempt coverage.",
                                     "Contracts describe current dataset adapters; source-specific metrics, coordinates and native IDs retain their semantics.",
                                 ))
