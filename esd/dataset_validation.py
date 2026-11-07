"""Read-only checks of normalized records, references and download coverage."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ._dataset_storage import _RECORDS, _metadata, _metadata_json, _validate_records
from .datasets import DatasetIssue, DatasetMetadata, SoccerDataset
from .normalized.schema import MATCH_COUNT_METRICS


@dataclass(frozen=True)
class DatasetValidationIssue:
    """A diagnostic code with an optional table, zero-based row and field."""

    severity: str
    code: str
    message: str
    table: str | None = None
    row_index: int | None = None
    field: str | None = None


@dataclass(frozen=True)
class DatasetValidationReport:
    """Immutable diagnostics. valid means no errors; warnings may still exist.

    A valid report does not establish complete provider coverage or equivalent
    status/score conventions across sources. Empty and partial datasets can be valid.
    """

    issues: tuple[DatasetValidationIssue, ...] = ()

    @property
    def errors(self) -> tuple[DatasetValidationIssue, ...]:
        """Diagnostics that make valid False."""
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[DatasetValidationIssue, ...]:
        """Diagnostics that require review without making valid False."""
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def valid(self) -> bool:
        """True when no diagnostic has error severity."""
        return not self.errors


_KEYS = {
    "matches": ("match_id",), "teams": ("team_id",), "match_stats": ("match_id",),
    "shots": ("shot_id",), "players": ("player_id",), "transfers": ("transfer_id",),
    "player_stats": ("competition_id", "season", "player_id"),
    "standings": ("competition_id", "season", "source_season_id", "table_id", "table_name",
                  "stage_id", "group_id", "team_id"),
    "market_values": ("player_id", "source_date", "team_id", "source_season_id"),
}
_PRIMARY_IDS = {
    "matches": "match_id", "teams": "team_id", "match_stats": "match_id", "shots": "shot_id",
    "players": "player_id", "transfers": "transfer_id", "player_stats": "player_id",
    "standings": "team_id", "market_values": "player_id",
}


def _date(value):
    parsed = datetime.strptime(value, "%Y-%m-%d").date()
    if parsed.isoformat() != value:
        raise ValueError("Dates must use YYYY-MM-DD")
    return parsed


def _coverage(dataset, add):
    meta = dataset.metadata
    if meta.coverage_scope == "match_ids" and not meta.requested_match_ids:
        add("error", "missing_match_selection", "Match-ID coverage requires explicit requested_match_ids")
    successful = set(meta.successful_tasks)
    if not isinstance(dataset.errors, (tuple, list)):
        add("error", "invalid_download_issues", "Dataset errors must be a sequence of DatasetIssue records")
        return
    for index, issue in enumerate(dataset.errors):
        if not isinstance(issue, DatasetIssue) or any(not isinstance(getattr(issue, item.name), str)
                                                     for item in fields(DatasetIssue)):
            add("error", "invalid_download_issue", f"Invalid download issue at index {index}")
            continue
        key = f"{issue.step}:{issue.target}"
        if (key in successful or (issue.step == "matches" and issue.target in meta.successful_dates)
                or (issue.step == "calendar" and meta.calendar_loaded)
                or (issue.step == "standings" and meta.standings_loaded)):
            add("error", "task_success_with_error", f"Task {key} is marked successful and failed")
        add("warning", "source_failure", f"{key}: {issue.error_type}: {issue.message}")
    if meta.expected_tasks and not set(meta.cached_tasks) <= successful:
        add("error", "cached_task_not_successful", "Cached tasks must also be successful tasks")
    if not dataset.complete:
        add("warning", "incomplete_coverage", "Not every requested download task completed successfully")


def _date_bounds(meta, add):
    if meta.start_date is None and meta.end_date is None:
        if meta.coverage_scope == "date_range" and any(table in meta.tables for table in ("matches", "match_stats")):
            add("error", "missing_date_bounds", "Date-range match queries require start_date and end_date")
        return None
    try:
        start, end = _date(meta.start_date), _date(meta.end_date)
        if end < start:
            raise ValueError("end_date precedes start_date")
    except (TypeError, ValueError) as exc:
        add("error", "invalid_date_bounds", str(exc))
        return None
    # Dated pages select source-local days. Other dated queries select UTC days.
    zone = timezone.utc
    if meta.source in ("fbref", "promiedos", "besoccer"):
        if meta.source_timezone is None and meta.source != "besoccer":
            add("warning", "unknown_date_timezone", "Source-local date bounds cannot be checked without source_timezone")
            return None
        if meta.source_timezone not in (None, "UTC"):
            try:
                zone = ZoneInfo(meta.source_timezone)
            except (ZoneInfoNotFoundError, ValueError) as exc:
                add("warning", "unavailable_date_timezone", f"Cannot check source-local bounds: {exc}")
                return None
    return start, end, zone


def validate_dataset(dataset: SoccerDataset) -> DatasetValidationReport:
    """Check records and metadata without network, writes or optional dependencies.

    Errors include malformed schemas/types, duplicate record keys, negative match
    scores, invalid date bounds and contradictory task coverage. Unknown scores
    remain allowed. Missing identifiers/kickoffs, incomplete downloads and unresolved
    references produce warnings. Only selected tables are used for reference checks.

    Standings keys include table/stage/group context. Valuation keys include player,
    source date, club and source season. Historical club references and native date
    strings are not treated as current roster membership or parsed into UTC dates.
    Dated pages use source_timezone for range checks when available. Native statuses
    and points are not interpreted. Unsupported input types raise TypeError.
    """
    if not isinstance(dataset, SoccerDataset):
        raise TypeError("Expected a SoccerDataset")
    issues = []

    def add(severity, code, message, table=None, row_index=None, field=None):
        issues.append(DatasetValidationIssue(severity, code, message, table, row_index, field))

    meta = dataset.metadata
    if not isinstance(meta, DatasetMetadata):
        add("error", "invalid_metadata", "Expected DatasetMetadata")
        return DatasetValidationReport(tuple(issues))
    try:
        _metadata(_metadata_json(meta))
    except (TypeError, ValueError, KeyError, AttributeError, OverflowError) as exc:
        add("error", "invalid_metadata", str(exc))
        metadata_valid = False
    else:
        metadata_valid = True
    selected = meta.tables if isinstance(meta.tables, (tuple, list)) and all(isinstance(item, str) for item in meta.tables) else ()
    bounds = None
    if metadata_valid:
        _coverage(dataset, add)
        bounds = _date_bounds(meta, add)
    rows = {}
    for table, attribute in _RECORDS.items():
        records = getattr(dataset, attribute)
        rows[table] = []
        if not isinstance(records, (tuple, list)):
            add("error", "invalid_table", "Records must be a tuple or list", table)
            continue
        if records and table not in selected:
            add("error", "unselected_table", "Table contains records but was not selected", table)
        seen = {}
        for index, row in enumerate(records):
            try:
                _validate_records((row,), table)
            except (ValueError, TypeError, AttributeError, OverflowError) as exc:
                add("error", "invalid_record", str(exc), table, index)
                continue
            rows[table].append((index, row))
            if not row.source or row.source != meta.source:
                add("error", "source_mismatch", "Record source must match dataset source", table, index, "source")
            for item in fields(row):
                value = getattr(row, item.name)
                if item.name.endswith("_id") and isinstance(value, str) and not value.strip():
                    add("error", "empty_identifier", "Identifiers cannot be blank strings", table, index, item.name)
            primary = _PRIMARY_IDS[table]
            if getattr(row, primary) is None:
                add("warning", "missing_identifier", "Record has no native identifier", table, index, primary)
            else:
                key = (row.source, *(getattr(row, name) for name in _KEYS[table]))
                if table != "market_values" or row.source_date is not None:
                    if key in seen:
                        add("error", "duplicate_key", f"Record key repeats row {seen[key]}", table, index, primary)
                    seen[key] = index
            if hasattr(row, "competition_id") and row.competition_id is not None and row.competition_id != meta.league:
                add("error", "competition_mismatch", "Record competition differs from dataset league", table, index, "competition_id")
            if hasattr(row, "season") and row.season is not None and row.season != str(meta.season):
                add("error", "season_label_mismatch", "Record caller season label differs from metadata", table, index, "season")
            if (meta.coverage_scope == "match_ids" and table in ("matches", "match_stats")
                    and row.match_id not in meta.requested_match_ids):
                add("error", "unrequested_match", "Record match ID is outside the explicit selection", table, index, "match_id")
            if table == "matches":
                for field in ("home_score", "away_score"):
                    if getattr(row, field) is not None and getattr(row, field) < 0:
                        add("error", "negative_score", "Match scores must be nonnegative or None", table, index, field)
                if row.home_team_id is not None and row.home_team_id == row.away_team_id:
                    add("error", "same_match_teams", "Home and away team IDs must differ", table, index)
                if row.kickoff is None:
                    add("warning", "missing_kickoff", "Match has no kickoff time", table, index, "kickoff")
                else:
                    if row.kickoff.utcoffset() != timedelta(0):
                        add("warning", "non_utc_kickoff", "Normalized kickoff uses an offset other than UTC", table, index, "kickoff")
                    if bounds is not None and not bounds[0] <= row.kickoff.astimezone(bounds[2]).date() <= bounds[1]:
                        add("error", "kickoff_outside_range", "Kickoff is outside the selected date range", table, index, "kickoff")
            if table == "match_stats":
                for side in ("home", "away"):
                    for metric in (*MATCH_COUNT_METRICS, "xg", "possession_pct"):
                        name = f"{side}_{metric}"
                        value = getattr(row, name)
                        if value is not None and (value < 0 or metric == "possession_pct" and value > 100):
                            add("error", "invalid_match_metric", "Counts/xG must be nonnegative; possession must be 0 to 100", table, index, name)
    team_ids = {(row.source, row.team_id) for _, row in rows["teams"] if row.team_id is not None}
    match_ids = {(row.source, row.match_id) for _, row in rows["matches"] if row.match_id is not None}
    for table in ("matches", "standings", "match_stats", "shots"):
        for index, row in rows[table]:
            references = (("home_team_id", "away_team_id") if table == "matches" else
                          ("team_id",) if table == "standings" else ("match_id",))
            target = "teams" if table in ("matches", "standings") else "matches"
            if target not in selected:
                continue
            known = team_ids if target == "teams" else match_ids
            for field in references:
                identifier = getattr(row, field)
                if identifier is None or (row.source, identifier) not in known:
                    add("warning", "unresolved_reference", f"{field} is absent from the selected {target} table", table, index, field)
    return DatasetValidationReport(tuple(issues))
