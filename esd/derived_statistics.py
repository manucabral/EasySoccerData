"""Row-level calculations from normalized observations, without source requests."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass

from .normalized import NormalizedMatchStats, NormalizedPlayerMatchStats, NormalizedPlayerStats
from .normalized.schema import PLAYER_MATCH_COUNT_METRICS

_MODELS = {
    NormalizedPlayerMatchStats: "player_match_stats",
    NormalizedPlayerStats: "player_stats",
    NormalizedMatchStats: "match_stats",
}
_SEASON_METRICS = (
    "goals", "assists", "shots", "key_passes", "yellow_cards", "red_cards",
    "xg", "xa", "npxg", "xg_chain", "xg_buildup",
)


@dataclass(frozen=True)
class DerivedMetric:
    """One formula and its observed inputs. Missing results retain a reason.

    value = numerator / denominator * scale. A percentage uses scale 100.
    model identifies the provider for expected-value metrics, without claiming
    a model version or equivalence with another provider.
    """

    name: str
    numerator_field: str
    denominator_field: str
    numerator: int | float | None
    denominator: int | float | None
    scale: float
    unit: str
    value: float | None
    status: str
    model: str | None = None


@dataclass(frozen=True)
class DerivedStatistics:
    """Derived metrics alongside the unchanged, source-scoped input record.

    Results describe this row only. They do not establish complete minutes or
    provider coverage. Per-90 values are rates, not a forecast for a full match.
    """

    record: NormalizedPlayerMatchStats | NormalizedPlayerStats | NormalizedMatchStats
    table: str
    metrics: tuple[DerivedMetric, ...]

    def to_dict(self):
        """Return JSON-compatible inputs, definitions, values and null reasons."""
        return {"format": "easysoccerdata-derived-statistics", "format_version": 1,
                "table": self.table, "record": asdict(self.record),
                "metrics": [asdict(metric) for metric in self.metrics]}


def _number(value, field):
    if value is None:
        return None
    try:
        valid = type(value) in (int, float) and value >= 0 and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"{field} must be a finite nonnegative number or None")
    return value


def _metric(record, name, numerator_field, denominator_field, scale, unit, *, subset=False):
    numerator = _number(getattr(record, numerator_field), numerator_field)
    denominator = _number(getattr(record, denominator_field), denominator_field)
    value = None
    if numerator is None:
        status = "missing_numerator"
    elif denominator is None:
        status = "missing_denominator"
    elif denominator == 0:
        status = "zero_denominator"
    elif subset and numerator > denominator:
        status = "inconsistent_inputs"
    else:
        value = numerator / denominator * scale
        status = "calculated" if math.isfinite(value) else "nonfinite_result"
        if status != "calculated":
            value = None
    model = record.source if numerator_field.rsplit("_", 1)[-1] in ("xg", "xa") or numerator_field in ("npxg", "xg_chain", "xg_buildup") else None
    return DerivedMetric(name, numerator_field, denominator_field, numerator, denominator,
                         scale, unit, value, status, model)


def derive_statistics(record) -> DerivedStatistics:
    """Calculate per-90 rates and accuracy ratios from a single normalized statistics record.

    Accepts ``NormalizedPlayerMatchStats``, ``NormalizedPlayerStats``, or
    ``NormalizedMatchStats``. Player records use their own reported ``minutes``
    field for per-90 rates; missing or zero denominators return ``value=None``
    with an explicit diagnostic ``status`` (``"missing_denominator"``,
    ``"zero_denominator"``, or ``"inconsistent_inputs"``).

    Args:
        record (NormalizedPlayerMatchStats | NormalizedPlayerStats | NormalizedMatchStats):
            A normalized statistics record instance.

    Returns:
        DerivedStatistics: Container holding the original ``record``, ``table``
            name, and tuple of ``DerivedMetric`` items.

    Raises:
        TypeError: If ``record`` is not one of the three supported normalized
            statistics models.
        ValueError: If ``record.source`` is blank or any numeric operand is
            negative, non-finite, or invalid.
    """
    table = _MODELS.get(type(record))
    if table is None:
        raise TypeError("Expected normalized player-match, player-season or match statistics")
    if not isinstance(record.source, str) or not record.source.strip():
        raise ValueError("Record source is required")
    result = []
    if table != "match_stats":
        names = _SEASON_METRICS if table == "player_stats" else (
            *(name for name in PLAYER_MATCH_COUNT_METRICS if name not in ("minutes", "appearances")),
            "xg", "xa",
        )
        for name in names:
            result.append(_metric(record, f"{name}_per90", name, "minutes", 90.0, "per90"))
    for side in (("home_", "away_") if table == "match_stats" else ("",)):
        if table != "player_stats":
            for name, numerator, denominator in (
                ("pass_accuracy_pct", "accurate_passes", "passes"),
                ("shot_accuracy_pct", "shots_on_target", "shots"),
            ):
                result.append(_metric(record, side + name, side + numerator, side + denominator,
                                      100.0, "percentage_points", subset=True))
        result.append(_metric(record, side + "xg_per_shot", side + "xg", side + "shots", 1.0, "xg/shot"))
    return DerivedStatistics(record, table, tuple(result))


def derived_statistics_to_dataframe(results: Iterable[DerivedStatistics]):
    """Convert an iterable of ``DerivedStatistics`` objects into a pandas DataFrame.

    Requires ``EasySoccerData[pandas]``.

    Args:
        results: Iterable of ``DerivedStatistics`` records produced by
            ``derive_statistics``.

    Returns:
        frame (pandas.DataFrame): A DataFrame with one row per derived metric
            and nullable string/float dtypes.

    Raises:
        ImportError: If ``pandas`` is not installed.
        TypeError: If any element in ``results`` is not a ``DerivedStatistics``.
    """
    try:
        import pandas as pd
    except ModuleNotFoundError as exc:
        if exc.name != "pandas" and not (exc.name or "").startswith("pandas."):
            raise
        raise ImportError('Install EasySoccerData[pandas] to display derived statistics.') from exc
    context = ("source", "match_id", "team_id", "player_id", "source_athlete_id", "competition_id", "season", "source_period")
    strings = (*context, "table", "name", "numerator_field", "denominator_field", "unit", "status", "model")
    numeric = ("numerator", "denominator", "scale", "value")
    rows = []
    for result in results:
        if not isinstance(result, DerivedStatistics):
            raise TypeError("Expected DerivedStatistics results")
        values = {field: getattr(result.record, field, None) for field in context}
        for metric in result.metrics:
            rows.append({**values, "table": result.table, **asdict(metric)})
    frame = pd.DataFrame(rows, columns=(*strings, *numeric))
    return frame.astype({**dict.fromkeys(strings, "string"),
                         **dict.fromkeys(numeric, "Float64")})
