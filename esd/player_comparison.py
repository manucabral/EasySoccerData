"""Compare listed players and their observed match statistics without downloads."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from decimal import Decimal

from ._dataset_storage import _metadata, _metadata_json
from .compatibility import EntityAlias, IdentityMap, MatchLinkResult, _resolve, link_dataset_matches
from .dataset_validation import DatasetValidationReport, validate_dataset
from .datasets import DatasetIssue, DatasetMetadata, SoccerDataset
from .normalized.models import NormalizedLineup, NormalizedPlayerMatchStats
from .normalized.schema import PLAYER_MATCH_COUNT_METRICS
from .utils import to_dataframe

_METRICS = (*PLAYER_MATCH_COUNT_METRICS, "xg", "xa", "source_rating")
_LINEUP_FIELDS = ("team_id", "home_away", "starter", "captain", "jersey_number", "position", "formation", "confirmed")


@dataclass(frozen=True)
class MatchPlayerCoverage:
    """Exact player-detail task coverage, including successful empty responses."""

    source: str
    match_id: str
    successful: bool
    lineup_count: int
    statistics_count: int
    statistics_selected: bool
    fetched_at: datetime | None


@dataclass(frozen=True)
class MatchPlayerComparison:
    """One paired or unresolved player, retaining both native records unchanged.

    equal covers known comparable lineup fields only. Unknown position mappings
    and nullable flags remain in unknown_fields. candidate_keys are native IDs
    on the opposite side, scoped to this row's linked match.
    """

    left_source: str
    left_match_id: str | None
    right_source: str
    right_match_id: str | None
    left_lineup: NormalizedLineup | None
    right_lineup: NormalizedLineup | None
    left_statistics: NormalizedPlayerMatchStats | None
    right_statistics: NormalizedPlayerMatchStats | None
    status: str
    reason: str | None
    differences: tuple[str, ...]
    unknown_fields: tuple[str, ...]
    candidate_keys: tuple[str, ...]
    left_fetched_at: datetime | None
    right_fetched_at: datetime | None


@dataclass(frozen=True)
class PlayerMatchStatisticComparison:
    """One player metric. delta is right minus left only for comparable values."""

    left_source: str
    left_match_id: str | None
    left_team_id: str | None
    left_player_id: str | None
    right_source: str
    right_match_id: str | None
    right_team_id: str | None
    right_player_id: str | None
    metric: str
    unit: str
    left_value: int | float | None
    right_value: int | float | None
    delta: int | float | None
    tolerance: float
    status: str
    left_fetched_at: datetime | None
    right_fetched_at: datetime | None


@dataclass(frozen=True)
class MatchPlayersReport:
    """Lineup decisions, metric observations and original download provenance.

    All listed players occur once in rows. Statistics must reference a selected
    lineup and remain attached even when player identity is unresolved. Unmatched
    players do not establish absence, nonparticipation or zero match minutes.
    """

    linkage: MatchLinkResult
    rows: tuple[MatchPlayerComparison, ...]
    statistics: tuple[PlayerMatchStatisticComparison, ...]
    left_metadata: DatasetMetadata
    right_metadata: DatasetMetadata
    left_errors: tuple[DatasetIssue, ...]
    right_errors: tuple[DatasetIssue, ...]
    left_validation: DatasetValidationReport
    right_validation: DatasetValidationReport
    left_complete: bool
    right_complete: bool
    left_coverage: tuple[MatchPlayerCoverage, ...]
    right_coverage: tuple[MatchPlayerCoverage, ...]
    metrics: tuple[str, ...]
    tolerances: tuple[tuple[str, float], ...]
    position_aliases: tuple[tuple[str, str, str], ...]
    kickoff_tolerance_seconds: float
    notes: tuple[str, ...] = ()
    identity_aliases: tuple[EntityAlias, ...] = ()

    @property
    def differences(self) -> tuple[MatchPlayerComparison, ...]:
        """Paired players whose known comparable lineup fields differ."""
        return tuple(row for row in self.rows if row.status == "different")

    @property
    def unresolved(self) -> tuple[MatchPlayerComparison, ...]:
        """Unpaired players, including ambiguous aliases and unlinked matches."""
        return tuple(row for row in self.rows if row.status not in ("equal", "different"))

    @property
    def statistic_differences(self) -> tuple[PlayerMatchStatisticComparison, ...]:
        """Comparable numeric observations outside the requested tolerance."""
        return tuple(row for row in self.statistics if row.status == "different")

    @property
    def unresolved_statistics(self) -> tuple[PlayerMatchStatisticComparison, ...]:
        """Missing values, unselected tables, unresolved players and source models."""
        return tuple(row for row in self.statistics if row.status not in ("equal", "different"))

    def to_dataframe(self, table: str = "lineups"):
        """Export lineups or statistics with optional pandas and fixed empty types.

        Lineup diagnostic tuples become JSON strings. Numeric statistics use
        nullable Float64; original records retain integer counts. Dates use UTC.
        """
        dates = {"left_fetched_at": None, "right_fetched_at": None}
        if table == "statistics":
            numeric = {"left_value", "right_value", "delta", "tolerance"}
            types = {field.name: "Float64" if field.name in numeric else "string"
                     for field in fields(PlayerMatchStatisticComparison) if field.name not in dates}
            frame = to_dataframe(list(self.statistics), dtypes=types, datetime_columns=dates)
            columns = [field.name for field in fields(PlayerMatchStatisticComparison)]
        elif table == "lineups":
            try:
                import pandas as pd
            except ModuleNotFoundError as exc:
                if exc.name != "pandas":
                    raise
                raise ImportError("Player report DataFrames require EasySoccerData[pandas].") from exc
            native = ("team_id", "player_id", "source_athlete_id", *_LINEUP_FIELDS[1:])
            columns = ["left_source", "left_match_id", "right_source", "right_match_id", "status", "reason",
                       "differences", "unknown_fields", "candidate_keys", *dates,
                       *(f"{side}_{name}" for side in ("left", "right") for name in native)]
            values = []
            for row in self.rows:
                item = {name: getattr(row, name) for name in columns[:11]}
                for name in ("differences", "unknown_fields", "candidate_keys"):
                    item[name] = json.dumps(item[name])
                for side in ("left", "right"):
                    record = getattr(row, f"{side}_lineup")
                    item.update({f"{side}_{name}": getattr(record, name) if record else None for name in native})
                values.append(item)
            types = {name: "boolean" if name.endswith(("_starter", "_captain", "_confirmed")) else "string"
                     for name in columns if name not in dates}
            frame = pd.DataFrame(values, columns=columns).astype(types)
            for name in dates:
                frame[name] = pd.to_datetime(frame[name], utc=True, format="mixed", errors="raise")
        else:
            raise ValueError("table must be lineups or statistics")
        for name in dates:
            frame[name] = frame[name].astype("datetime64[ns, UTC]")
        frame = frame[columns]
        frame.attrs.update(report="match_players", report_table=table, report_version="1")
        return frame


def _key(row):
    return row.match_id, row.team_id, row.player_id


def _coverage(dataset):
    lineups, statistics = defaultdict(int), defaultdict(int)
    for row in dataset.lineup_records:
        lineups[row.match_id] += 1
    for row in dataset.player_match_stat_records:
        statistics[row.match_id] += 1
    times = dict(dataset.metadata.response_fetched_at)
    result = []
    for identifier in dict.fromkeys([*(row.match_id for row in dataset.match_records), *dataset.metadata.requested_match_ids]):
        task = f"{'match_details' if dataset.metadata.source == 'espn' else 'lineups'}:{identifier}"
        fetched = datetime.fromisoformat(times[task]).astimezone(timezone.utc) if task in times else None
        result.append(MatchPlayerCoverage(dataset.metadata.source, identifier, task in dataset.metadata.successful_tasks,
                                          lineups[identifier], statistics[identifier],
                                          "player_match_stats" in dataset.metadata.tables, fetched))
    return tuple(result)


def _lineup_values(first, second, identities, positions, same_source):
    different, unknown = [], []
    for field in _LINEUP_FIELDS:
        values = [getattr(row, field) for row in (first, second)]
        if field == "team_id":
            values = [_resolve(identities, "team", row.source, row.team_id, same_source) for row in (first, second)]
        elif field == "position" and not same_source:
            values = [positions.get((row.source, row.position)) for row in (first, second)]
        if any(value is None for value in values):
            unknown.append(field)
        elif values[0] != values[1]:
            different.append(field)
    return tuple(different), tuple(unknown)


def _statistic(row, metric, tolerance, selected):
    first, second = row.left_statistics, row.right_statistics
    left, right = getattr(first, metric) if first else None, getattr(second, metric) if second else None
    status, delta = row.status, None
    if status in ("equal", "different"):
        if not all(selected):
            status = "table_unselected_both" if not any(selected) else "table_unselected_left" if not selected[0] else "table_unselected_right"
        elif first is None or second is None:
            status = "record_missing_both" if first is second is None else "record_missing_left" if first is None else "record_missing_right"
        elif left is None or right is None:
            status = "missing_both" if left is right is None else "missing_left" if left is None else "missing_right"
        elif first.source != second.source and metric in ("xg", "xa", "source_rating"):
            status = "source_specific"
        else:
            difference = Decimal(str(right)) - Decimal(str(left))
            delta = right - left if type(left) is type(right) is int else float(difference)
            if not math.isfinite(delta):
                raise ValueError("Player statistic difference exceeds finite numeric range")
            status = "equal" if abs(difference) <= Decimal(str(tolerance)) else "different"
    return PlayerMatchStatisticComparison(
        row.left_source, row.left_match_id, row.left_lineup.team_id if row.left_lineup else None,
        row.left_lineup.player_id if row.left_lineup else None,
        row.right_source, row.right_match_id, row.right_lineup.team_id if row.right_lineup else None,
        row.right_lineup.player_id if row.right_lineup else None,
        metric, "minutes" if metric == "minutes" else "expected_goals" if metric == "xg" else
        "expected_assists" if metric == "xa" else "source_rating" if metric == "source_rating" else "count",
        left, right, delta, float(tolerance), status, row.left_fetched_at, row.right_fetched_at,
    )


def compare_match_players(
    left: SoccerDataset, right: SoccerDataset, *, identities: IdentityMap | None = None,
    metrics: Sequence[str] | None = None, tolerances: Mapping[str, float] | None = None,
    position_aliases: Mapping[tuple[str, str], str] | None = None, tolerance_seconds: float = 300,
) -> MatchPlayersReport:
    """Compare lineups and optional player-match statistics across linked matches.

    Both datasets must belong to ``"espn"``, ``"scores365"``, or ``"sofascore"``,
    select ``matches`` and ``lineups``, and pass ``validate_dataset`` without
    errors. Cross-source comparisons require explicit ``EntityAlias("player", ...)``
    entries in ``identities``.

    Args:
        left: Left ``SoccerDataset`` selecting ``matches`` and ``lineups``
            (and optionally ``player_match_stats``).
        right: Right ``SoccerDataset`` selecting ``matches`` and ``lineups``
            (and optionally ``player_match_stats``).
        identities: ``IdentityMap`` with competition, team, and player aliases.
        metrics: Optional subset of numeric ``NormalizedPlayerMatchStats``
            field names to compare.
        tolerances: Optional mapping of metric name to maximum absolute numeric
            difference treated as ``"equal"`` (defaults to ``0``).
        position_aliases: Optional mapping of ``(source, native_position)`` to
            canonical position code used when comparing lineup positions across
            providers.
        tolerance_seconds: Maximum UTC kickoff difference in seconds for match
            linkage (default ``300``).

    Returns:
        MatchPlayersReport: Lineup comparisons, player statistic comparisons,
            match linkage details, and DataFrame export methods.

    Raises:
        TypeError: If ``left`` or ``right`` is not a ``SoccerDataset``.
        ValueError: If options are invalid, required tables are missing, or
            either dataset fails validation.
    """
    if not isinstance(left, SoccerDataset) or not isinstance(right, SoccerDataset):
        raise TypeError("Expected two SoccerDataset objects")
    if type(tolerance_seconds) not in (int, float) or not math.isfinite(tolerance_seconds) or tolerance_seconds < 0:
        raise ValueError("tolerance_seconds must be finite and nonnegative")
    selected = _METRICS if metrics is None else metrics
    if (not isinstance(selected, Sequence) or isinstance(selected, (str, bytes)) or not selected
            or any(not isinstance(name, str) or name not in _METRICS for name in selected)):
        raise ValueError("metrics must select normalized player-match numeric fields")
    selected = tuple(dict.fromkeys(selected))
    if tolerances is not None and not isinstance(tolerances, Mapping):
        raise ValueError("tolerances must map selected metrics to absolute differences")
    limits = dict(tolerances) if tolerances is not None else {}
    if any(name not in selected or type(value) not in (int, float) or not math.isfinite(value) or value < 0
           for name, value in limits.items()):
        raise ValueError("Tolerances require selected metrics and finite nonnegative numbers")
    positions = {}
    if position_aliases is not None:
        if not isinstance(position_aliases, Mapping):
            raise ValueError("position_aliases must map (source, native label) to canonical position")
        for key, value in position_aliases.items():
            if (not isinstance(key, tuple) or len(key) != 2 or key[0] not in ("espn", "scores365", "sofascore")
                    or not all(isinstance(item, str) and item.strip() for item in (*key, value))):
                raise ValueError("Invalid explicit position alias")
            positions[key] = value
    validations = tuple(validate_dataset(dataset) for dataset in (left, right))
    for dataset, validation in zip((left, right), validations):
        if not validation.valid:
            raise ValueError(f"Invalid player dataset: {validation.errors[0].code}")
        if dataset.metadata.source not in ("espn", "scores365", "sofascore"):
            raise ValueError("Player comparison supports ESPN, 365Scores and Sofascore")
        if not {"matches", "lineups"} <= set(dataset.metadata.tables):
            raise ValueError("Both datasets must select matches and lineups")
        matches = {row.match_id for row in dataset.match_records}
        if any(row.match_id is None or row.match_id not in matches for row in dataset.lineup_records):
            raise ValueError("Lineups require matching native match IDs")
        keys = {_key(row) for row in dataset.lineup_records}
        if any(_key(row) not in keys for row in dataset.player_match_stat_records):
            raise ValueError("Player statistics require matching lineup records")
    linkage = link_dataset_matches(left, right, identities=identities, tolerance_seconds=tolerance_seconds)
    metadata = tuple(_metadata(_metadata_json(dataset.metadata)) for dataset in (left, right))
    coverage = tuple(_coverage(dataset) for dataset in (left, right))
    times = [{row.match_id: row.fetched_at for row in side} for side in coverage]
    statistics = [{_key(row): row for row in dataset.player_match_stat_records} for dataset in (left, right)]
    grouped = [defaultdict(list), defaultdict(list)]
    for side, dataset in enumerate((left, right)):
        for row in dataset.lineup_records:
            grouped[side][row.match_id].append(row)
    same_source = metadata[0].source == metadata[1].source
    kickoffs = {(row.source, row.match_id): row.kickoff for dataset in (left, right) for row in dataset.match_records}
    rows = []

    def player_identity(row):
        return _resolve(identities, "player", row.source, row.player_id, same_source,
                        team_id=row.team_id, at=kickoffs.get((row.source, row.match_id)))

    def append(first, second, left_id, right_id, status, reason=None, candidates=()):
        different, unknown = _lineup_values(first, second, identities, positions, same_source) if first and second else ((), ())
        rows.append(MatchPlayerComparison(
            metadata[0].source, left_id, metadata[1].source, right_id, first, second,
            statistics[0].get(_key(first)) if first else None, statistics[1].get(_key(second)) if second else None,
            "different" if different else "equal" if first and second else status,
            reason, different, unknown, tuple(candidates), times[0].get(left_id), times[1].get(right_id),
        ))

    for link in linkage.links:
        sides = (grouped[0][link.left_match_id], grouped[1][link.right_match_id])
        indexes = [defaultdict(list), defaultdict(list)]
        for side, records in enumerate(sides):
            for i, row in enumerate(records):
                identity = player_identity(row)
                if identity is not None:
                    indexes[side][identity].append(i)
        paired = [set(), set()]
        for identity, firsts in indexes[0].items():
            seconds = indexes[1].get(identity, ())
            if len(firsts) == len(seconds) == 1:
                i, j = firsts[0], seconds[0]
                append(sides[0][i], sides[1][j], link.left_match_id, link.right_match_id, "equal")
                paired[0].add(i)
                paired[1].add(j)
        for side, records in enumerate(sides):
            for i, row in enumerate(records):
                if i in paired[side]:
                    continue
                identity = player_identity(row)
                own, other = indexes[side].get(identity, ()), indexes[1 - side].get(identity, ())
                status = "unresolved" if identity is None else "ambiguous" if len(own) > 1 or len(other) > 1 else "unmatched"
                reason = "player_identity_unknown" if identity is None else "multiple_candidates" if status == "ambiguous" else "no_candidate"
                if identity is None and identities is not None and not same_source:
                    decision = identities.lookup("player", row.source, row.player_id, team_id=row.team_id,
                                                 at=kickoffs.get((row.source, row.match_id)))
                    if decision.status in ("context_required", "out_of_scope"):
                        reason = f"player_identity_{decision.status}"
                append(row if side == 0 else None, row if side == 1 else None,
                       link.left_match_id, link.right_match_id, f"{status}_{'left' if side == 0 else 'right'}", reason,
                       (sides[1 - side][j].player_id for j in other))
    linked = ({link.left_match_id for link in linkage.links}, {link.right_match_id for link in linkage.links})
    for side, dataset in enumerate((left, right)):
        ambiguous = linkage.ambiguous_left if side == 0 else linkage.ambiguous_right
        for row in dataset.lineup_records:
            if row.match_id not in linked[side]:
                append(row if side == 0 else None, row if side == 1 else None,
                       row.match_id if side == 0 else None, row.match_id if side == 1 else None,
                       f"unresolved_{'left' if side == 0 else 'right'}",
                       "match_ambiguous" if row.match_id in ambiguous else "match_unlinked")
    tables = tuple("player_match_stats" in dataset.metadata.tables for dataset in (left, right))
    metrics_rows = tuple(_statistic(row, metric, limits.get(metric, 0), tables) for row in rows for metric in selected) if any(tables) else ()
    return MatchPlayersReport(
        linkage, tuple(rows), metrics_rows, *metadata, tuple(left.errors), tuple(right.errors), *validations,
        left.complete, right.complete, *coverage, selected, tuple((name, float(limits.get(name, 0))) for name in selected),
        tuple((source, native, value) for (source, native), value in sorted(positions.items())), float(tolerance_seconds), (
            "Equal describes known comparable observations, not verified collection equivalence.",
            "Positions require explicit cross-source aliases; source role/status codes remain native.",
            "Listed players need not have participated; missing minutes and absent statistics are not zero.",
            "Cross-source xG, xA and ratings retain their models without numeric deltas.",
            "Player metrics are source totals without a period breakdown or inferred stoppage-time convention.",
            "Only exact player-detail tasks establish row timestamps and successful-empty coverage.",
        ),
        identity_aliases=identities.aliases if identities is not None else (),
    )
