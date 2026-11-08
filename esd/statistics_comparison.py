"""Read-only differences between explicitly linked match statistics."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from decimal import Decimal

from ._dataset_storage import _metadata, _metadata_json
from .compatibility import IdentityMap, MatchLinkResult, link_dataset_matches
from .dataset_validation import DatasetValidationReport, validate_dataset
from .datasets import DatasetIssue, DatasetMetadata, SoccerDataset
from .normalized.schema import MATCH_COUNT_METRICS
from .utils import to_dataframe

_METRICS = tuple(f"{side}_{metric}" for metric in (*MATCH_COUNT_METRICS, "possession_pct", "xg")
                 for side in ("home", "away")) + ("forecast_win", "forecast_draw", "forecast_loss")
_PERIODS = {
    ("espn", "boxscore"): "source_total", ("scores365", "-1"): "source_total",
    ("sofascore", "ALL"): "source_total", ("sofascore", "1ST"): "first_half",
    ("sofascore", "2ND"): "second_half",
}


@dataclass(frozen=True)
class MatchStatisticComparison:
    """One linked match/metric. delta is right minus left when comparison is allowed.

    equal includes the caller's absolute tolerance. Missing records/values,
    unknown or different periods and cross-source xG/forecasts have no delta.
    Fetch times come only from exact statistic/detail task keys, never loader times.
    """

    left_source: str
    left_match_id: str
    right_source: str
    right_match_id: str
    metric: str
    unit: str
    left_value: int | float | None
    right_value: int | float | None
    delta: int | float | None
    status: str
    tolerance: float
    left_period: str | None
    right_period: str | None
    left_fetched_at: datetime | None
    right_fetched_at: datetime | None
    left_statistics_available: bool
    right_statistics_available: bool


@dataclass(frozen=True)
class MatchStatisticsReport:
    """Metric rows, linkage decisions, validation and source download provenance.

    Differences describe observations. They do not select a correct provider or
    establish that equally named statistics have identical collection rules.
    """

    linkage: MatchLinkResult
    rows: tuple[MatchStatisticComparison, ...]
    left_metadata: DatasetMetadata
    right_metadata: DatasetMetadata
    left_errors: tuple[DatasetIssue, ...]
    right_errors: tuple[DatasetIssue, ...]
    left_validation: DatasetValidationReport
    right_validation: DatasetValidationReport
    left_complete: bool
    right_complete: bool
    notes: tuple[str, ...] = ()

    @property
    def differences(self) -> tuple[MatchStatisticComparison, ...]:
        """Comparable numeric observations outside the requested tolerance."""
        return tuple(row for row in self.rows if row.status == "different")

    @property
    def unresolved(self) -> tuple[MatchStatisticComparison, ...]:
        """Rows missing records/values or lacking compatible period/model scope."""
        return tuple(row for row in self.rows if row.status not in ("equal", "different"))

    def to_dataframe(self):
        """Export metric rows with optional pandas, including fixed empty columns.

        Numeric value/delta columns use Float64 to accommodate counts and metrics.
        The record tuples retain integer counts. Timestamps use aware UTC.
        """
        dates = {"left_fetched_at": None, "right_fetched_at": None}
        numeric = {"left_value", "right_value", "delta", "tolerance"}
        flags = {"left_statistics_available", "right_statistics_available"}
        types = {item.name: "Float64" if item.name in numeric else "boolean" if item.name in flags else "string"
                 for item in fields(MatchStatisticComparison) if item.name not in dates}
        frame = to_dataframe(list(self.rows), dtypes=types, datetime_columns=dates)
        for name in dates:
            frame[name] = frame[name].astype("datetime64[ns, UTC]")
        frame = frame[[item.name for item in fields(MatchStatisticComparison)]]
        frame.attrs.update(report="match_statistics", report_version="1")
        return frame


def _unit(metric):
    if metric.endswith("possession_pct"):
        return "percentage_points"
    if metric.endswith("_xg"):
        return "expected_goals"
    return "probability" if metric.startswith("forecast_") else "count"


def _period(source, value):
    return _PERIODS.get((source, value))


def _status(first, second, metric, tolerance):
    if first is None or second is None:
        return ("record_missing_both" if first is second is None else
                "record_missing_left" if first is None else "record_missing_right"), None
    left, right = getattr(first, metric), getattr(second, metric)
    if left is None or right is None:
        return ("missing_both" if left is right is None else
                "missing_left" if left is None else "missing_right"), None
    if first.source != second.source and (metric.endswith("_xg") or metric.startswith("forecast_")):
        return "source_specific", None
    left_period, right_period = _period(first.source, first.source_period), _period(second.source, second.source_period)
    same_native_period = (first.source == second.source and first.source_period is not None
                          and first.source_period == second.source_period)
    if not same_native_period:
        if left_period is None or right_period is None:
            return "period_unknown", None
        if left_period != right_period:
            return "period_mismatch", None
    # Decimal text avoids marking 51.5 vs 51.6 outside a 0.1-point tolerance
    # solely because of binary floating-point subtraction.
    difference = Decimal(str(right)) - Decimal(str(left))
    delta = right - left if type(left) is type(right) is int else float(difference)
    if not math.isfinite(delta):
        raise ValueError("Statistic difference exceeds finite numeric range")
    return "equal" if abs(difference) <= Decimal(str(tolerance)) else "different", delta


def _index_statistics(dataset):
    matches = {row.match_id for row in dataset.match_records}
    result = {}
    for row in dataset.match_stat_records:
        if row.match_id is None or row.match_id not in matches:
            raise ValueError(f"{dataset.metadata.source} statistics require a matching native match ID")
        result[row.match_id] = row
    return result


def _fetched(timestamps, identifier):
    value = timestamps.get(f"match_stats:{identifier}", timestamps.get(f"match_details:{identifier}"))
    return datetime.fromisoformat(value).astimezone(timezone.utc) if value is not None else None


def compare_match_statistics(
    left: SoccerDataset, right: SoccerDataset, *, identities: IdentityMap | None = None,
    metrics: Sequence[str] | None = None, tolerances: Mapping[str, float] | None = None,
    tolerance_seconds: float = 300,
) -> MatchStatisticsReport:
    """Compare observations for one-to-one linked matches without fetching or writing.

    Both datasets must select matches and match_stats and pass validation without
    errors. Partial downloads and warnings are retained. Identity mapping and
    ambiguity handling reuse link_dataset_matches; names and scores are not keys.

    metrics selects normalized numeric fields, defaulting to counts, possession,
    xG and forecasts. tolerances supplies per-field absolute differences (default
    zero), in count units or percentage points. Unknown metrics/options raise.

    Known ESPN boxscore, 365Scores -1 and Sofascore ALL selectors describe source
    totals. Their differences are diagnostic; regulation/extra-time equivalence
    is not asserted. Missing/unknown/different periods have no numeric delta.
    Cross-source xG and forecasts remain source_specific, even if values agree.
    Same-source observations can use identical, explicit native period labels.
    """
    if not isinstance(left, SoccerDataset) or not isinstance(right, SoccerDataset):
        raise TypeError("Expected two SoccerDataset objects")
    if type(tolerance_seconds) not in (int, float) or not math.isfinite(tolerance_seconds) or tolerance_seconds < 0:
        raise ValueError("tolerance_seconds must be finite and nonnegative")
    selected = _METRICS if metrics is None else metrics
    if (not isinstance(selected, Sequence) or isinstance(selected, (str, bytes)) or not selected
            or any(not isinstance(name, str) or name not in _METRICS for name in selected)):
        raise ValueError("metrics must select normalized numeric match-statistic fields")
    selected = tuple(dict.fromkeys(selected))
    if tolerances is not None and not isinstance(tolerances, Mapping):
        raise ValueError("tolerances must map selected metric names to absolute numeric differences")
    limits = dict(tolerances) if tolerances is not None else {}
    if any(name not in selected or type(value) not in (int, float) or not math.isfinite(value) or value < 0
           for name, value in limits.items()):
        raise ValueError("Tolerances require selected metric names and finite nonnegative numbers")
    validations = tuple(validate_dataset(dataset) for dataset in (left, right))
    for side, validation in zip(("left", "right"), validations):
        if not validation.valid:
            raise ValueError(f"Invalid {side} dataset: {validation.errors[0].code}: {validation.errors[0].message}")
    for dataset in (left, right):
        if not {"matches", "match_stats"} <= set(dataset.metadata.tables):
            raise ValueError("Both datasets must select matches and match_stats")
    linkage = link_dataset_matches(left, right, identities=identities, tolerance_seconds=tolerance_seconds)
    left_rows, right_rows = _index_statistics(left), _index_statistics(right)
    metadata = tuple(_metadata(_metadata_json(dataset.metadata)) for dataset in (left, right))
    timestamps = tuple(dict(item.response_fetched_at) for item in metadata)
    rows = []
    for link in linkage.links:
        first, second = left_rows.get(link.left_match_id), right_rows.get(link.right_match_id)
        fetched_left, fetched_right = _fetched(timestamps[0], link.left_match_id), _fetched(timestamps[1], link.right_match_id)
        for metric in selected:
            tolerance = limits.get(metric, 0)
            status, delta = _status(first, second, metric, tolerance)
            rows.append(MatchStatisticComparison(
                link.left_source, link.left_match_id, link.right_source, link.right_match_id,
                metric, _unit(metric), getattr(first, metric) if first else None,
                getattr(second, metric) if second else None, delta, status, float(tolerance),
                first.source_period if first else None, second.source_period if second else None,
                fetched_left, fetched_right,
                first is not None, second is not None,
            ))
    return MatchStatisticsReport(
        linkage, tuple(rows), *metadata, tuple(left.errors), tuple(right.errors), *validations,
        left.complete, right.complete, (
            "Numeric differences describe source observations, not verified metric equivalence or a preferred source.",
            "Source totals can include different extra-time or collection conventions; native periods remain visible.",
            "Cross-source xG and forecast values stay separate without a delta.",
            "Per-row fetch times require exact match_stats or shared match_details task keys; metadata retains all source timestamps.",
        ),
    )
