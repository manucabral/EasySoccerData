"""Diagnostic comparisons of explicitly identified ESPN/365Scores match events."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone

from ._dataset_storage import _metadata, _metadata_json
from .compatibility import IdentityMap, MatchLinkResult, _resolve, link_dataset_matches
from .dataset_validation import DatasetValidationReport, validate_dataset
from .datasets import DatasetIssue, DatasetMetadata, SoccerDataset
from .normalized import NormalizedMatchEvent

_FAMILIES = {
    "goal": "score", "own_goal": "score", "penalty_scored": "score", "penalty_missed": "score",
    "yellow_card": "card", "red_card": "card", "second_yellow_card": "card", "substitution": "substitution",
}
_PERIODS = {
    ("espn", "1"): "first_half", ("espn", "2"): "second_half",
    ("espn", "3"): "extra_first_half", ("espn", "4"): "extra_second_half", ("espn", "5"): "shootout",
    ("scores365", "7"): "first_half", ("scores365", "9"): "second_half", ("scores365", "11"): "shootout",
}


@dataclass(frozen=True)
class MatchEventCoverage:
    """Exact event-task success and original fetch time, separate from row count."""

    source: str
    match_id: str
    successful: bool
    record_count: int
    fetched_at: datetime | None


@dataclass(frozen=True)
class MatchEventComparison:
    """A paired observation or one unresolved native event.

    equal means equal observed comparable values. unknown_fields names absent
    evidence, including unknown annulments; equal never confirms those values.
    Candidate keys are id:VALUE/order:VALUE scoped to the opposite source/match.
    Native records are retained in full, without replacing their identifiers.
    """

    left_source: str
    left_match_id: str | None
    right_source: str
    right_match_id: str | None
    left_event: NormalizedMatchEvent | None
    right_event: NormalizedMatchEvent | None
    status: str
    reason: str | None = None
    differences: tuple[str, ...] = ()
    unknown_fields: tuple[str, ...] = ()
    candidate_keys: tuple[str, ...] = ()
    left_fetched_at: datetime | None = None
    right_fetched_at: datetime | None = None


@dataclass(frozen=True)
class MatchEventsReport:
    """Native observations, one-to-one decisions, coverage and source provenance."""

    linkage: MatchLinkResult
    rows: tuple[MatchEventComparison, ...]
    left_metadata: DatasetMetadata
    right_metadata: DatasetMetadata
    left_errors: tuple[DatasetIssue, ...]
    right_errors: tuple[DatasetIssue, ...]
    left_validation: DatasetValidationReport
    right_validation: DatasetValidationReport
    left_complete: bool
    right_complete: bool
    left_coverage: tuple[MatchEventCoverage, ...]
    right_coverage: tuple[MatchEventCoverage, ...]
    excluded_left: tuple[NormalizedMatchEvent, ...]
    excluded_right: tuple[NormalizedMatchEvent, ...]
    minute_tolerance: int
    kickoff_tolerance_seconds: float
    period_aliases: tuple[tuple[str, str, str], ...]
    event_types: tuple[str, ...]
    notes: tuple[str, ...] = ()

    @property
    def differences(self) -> tuple[MatchEventComparison, ...]:
        """Uniquely paired events with differing known comparable observations."""
        return tuple(row for row in self.rows if row.status == "different")

    @property
    def unresolved(self) -> tuple[MatchEventComparison, ...]:
        """Unpaired events, including missing identities, scope and ambiguity."""
        return tuple(row for row in self.rows if row.status not in ("equal", "different"))

    def to_dataframe(self):
        """Flatten report rows with lazy pandas, fixed empty columns and UTC dates."""
        try:
            import pandas as pd
        except ModuleNotFoundError as exc:
            if exc.name != "pandas":
                raise
            raise ImportError('Event report DataFrames require EasySoccerData[pandas].') from exc
        event_fields = ("event_id", "source_order", "event_type", "source_period", "minute", "added_minute",
                        "is_shootout", "rescinded", "team_id", "player_id", "related_player_id")
        columns = ["left_source", "left_match_id", "right_source", "right_match_id", "status", "reason",
                   "differences", "unknown_fields", "candidate_keys", "left_fetched_at", "right_fetched_at",
                   *(f"{side}_{field}" for side in ("left", "right") for field in event_fields)]
        values = []
        for row in self.rows:
            value = {name: getattr(row, name) for name in columns[:11]}
            for name in ("differences", "unknown_fields", "candidate_keys"):
                value[name] = json.dumps(value[name])
            for side in ("left", "right"):
                event = getattr(row, f"{side}_event")
                for field in event_fields:
                    value[f"{side}_{field}"] = getattr(event, field) if event is not None else None
            values.append(value)
        dates = {"left_fetched_at": None, "right_fetched_at": None}
        types = {name: "Int64" if name.endswith(("_minute", "_source_order")) else
                 "boolean" if name.endswith(("_is_shootout", "_rescinded")) else "string"
                 for name in columns if name not in dates}
        frame = pd.DataFrame(values, columns=columns).astype(types)
        for name in dates:
            frame[name] = pd.to_datetime(frame[name], utc=True, errors="raise", format="mixed").astype("datetime64[ns, UTC]")
        frame = frame[columns]
        frame.attrs.update(report="match_events", report_version="1")
        return frame


def _task_keys(source, identifier):
    return ((f"match_details:{identifier}",) if source == "espn" else
            (f"match_events:{identifier}", f"lineups:{identifier}"))


def _coverage(dataset):
    times = dict(dataset.metadata.response_fetched_at)
    counts = defaultdict(int)
    for row in dataset.match_event_records:
        counts[row.match_id] += 1
    result = []
    identifiers = dict.fromkeys([*(row.match_id for row in dataset.match_records), *dataset.metadata.requested_match_ids])
    for identifier in identifiers:
        keys = _task_keys(dataset.metadata.source, identifier)
        observed = {times[key] for key in keys if key in times}
        fetched = datetime.fromisoformat(observed.pop()).astimezone(timezone.utc) if len(observed) == 1 else None
        result.append(MatchEventCoverage(dataset.metadata.source, identifier,
                                        any(key in dataset.metadata.successful_tasks for key in keys),
                                        counts[identifier], fetched))
    return tuple(result)


def _period(row, periods, same_source):
    if row.source_period is None:
        return None
    return periods.get((row.source, row.source_period), (row.source, row.source_period) if same_source else None)


def _identity(row, kind, field, identities, same_source):
    return _resolve(identities, kind, row.source, getattr(row, field), same_source)


def _signature(row, identities, periods, same_source):
    player = _identity(row, "player", "player_id", identities, same_source)
    if player is None:
        return None, "player_identity_unknown"
    if _identity(row, "team", "team_id", identities, same_source) is None:
        return None, "team_identity_unknown"
    if row.is_shootout is None:
        return None, "shootout_unknown"
    period = _period(row, periods, same_source)
    if period is None:
        return None, "period_unknown"
    outgoing = None
    if row.event_type == "substitution":
        if (row.player_role, row.related_player_role) != ("incoming", "outgoing"):
            return None, "substitution_roles_unknown"
        outgoing = _identity(row, "player", "related_player_id", identities, same_source)
        if outgoing is None:
            return None, "related_player_identity_unknown"
    if not row.is_shootout and row.minute is None:
        return None, "minute_unknown"
    return (_FAMILIES[row.event_type], player, outgoing, row.is_shootout, period), None


def _near(first, second, limit):
    if first.is_shootout:
        return True
    if abs(first.minute - second.minute) > limit:
        return False
    if first.added_minute is not None and second.added_minute is not None:
        return abs((first.minute + first.added_minute) - (second.minute + second.added_minute)) <= limit
    return True


def _compare(first, second, identities, periods, same_source):
    different, unknown = [], []
    values = [(name, getattr(first, name), getattr(second, name)) for name in
              ("event_type", "is_shootout", "rescinded")]
    values += [("source_period", _period(first, periods, same_source), _period(second, periods, same_source))]
    for name, kind in (("team_id", "team"), ("player_id", "player")):
        values.append((name, _identity(first, kind, name, identities, same_source),
                       _identity(second, kind, name, identities, same_source)))
    if not first.is_shootout and not second.is_shootout:
        values.extend((name, getattr(first, name), getattr(second, name)) for name in ("minute", "added_minute"))
    if first.event_type == "substitution" or second.event_type == "substitution":
        for name in ("player_role", "related_player_role"):
            values.append((name, getattr(first, name), getattr(second, name)))
        values.append(("related_player_id", _identity(first, "player", "related_player_id", identities, same_source),
                       _identity(second, "player", "related_player_id", identities, same_source)))
    for name, left, right in values:
        if left is None or right is None:
            unknown.append(name)
        elif left != right:
            different.append(name)
    return tuple(different), tuple(unknown)


def _reference(row):
    return f"id:{row.event_id}" if row.event_id is not None else f"order:{row.source_order}"


def compare_match_events(
    left: SoccerDataset, right: SoccerDataset, *, identities: IdentityMap | None = None,
    minute_tolerance: int = 1, tolerance_seconds: float = 300,
    event_types: Sequence[str] | None = None,
    period_aliases: Mapping[tuple[str, str], str] | None = None,
) -> MatchEventsReport:
    """Compare selected ESPN/365Scores events without HTTP, writes or name matching.

    Matches reuse the ID/kickoff linker. Cross-source events require mapped
    players/teams, explicit shootout state and known/explicitly mapped periods.
    Non-shootout candidates also need observed minutes within minute_tolerance.
    Missing added time is never zero. Substitutions require both mapped players
    in incoming/outgoing roles. Shootouts use player/period, never match minutes.
    Only candidates unique in both directions are paired; no nearest-event or
    list-position assignment resolves ambiguity. Within one source/match, an
    identical native event ID anchors revisions even when observed fields differ.

    The minute tolerance selects candidates; any known minute difference remains
    a reported difference. equal describes observed fields only. Unknown fields
    stay visible, notably nullable annulments. Every selected event occurs in one
    report row; unselected/other types remain in excluded_left/excluded_right.
    period_aliases extends/overrides the explicit native period map and is saved
    in the report. This version supports ESPN/365Scores, including same-source
    comparisons. It does not assert equivalent source collection rules.
    """
    if not isinstance(left, SoccerDataset) or not isinstance(right, SoccerDataset):
        raise TypeError("Expected two SoccerDataset objects")
    if type(minute_tolerance) is not int or minute_tolerance < 0:
        raise ValueError("minute_tolerance must be a nonnegative integer")
    if type(tolerance_seconds) not in (int, float) or not math.isfinite(tolerance_seconds) or tolerance_seconds < 0:
        raise ValueError("tolerance_seconds must be finite and nonnegative")
    selected = tuple(_FAMILIES) if event_types is None else event_types
    if (not isinstance(selected, Sequence) or isinstance(selected, (str, bytes)) or not selected
            or any(not isinstance(item, str) or item not in _FAMILIES for item in selected)):
        raise ValueError("event_types must select normalized scoring, card or substitution types")
    selected = tuple(dict.fromkeys(selected))
    periods = dict(_PERIODS)
    if period_aliases is not None:
        if not isinstance(period_aliases, Mapping):
            raise ValueError("period_aliases must map (source, native period) to canonical period")
        for key, value in period_aliases.items():
            if (not isinstance(key, tuple) or len(key) != 2 or key[0] not in ("espn", "scores365")
                    or not all(isinstance(item, str) and item.strip() for item in (*key, value))):
                raise ValueError("Invalid explicit period alias")
            periods[key] = value
    validations = tuple(validate_dataset(dataset) for dataset in (left, right))
    for dataset, validation in zip((left, right), validations):
        if not validation.valid:
            raise ValueError(f"Invalid event dataset: {validation.errors[0].code}")
        if dataset.metadata.source not in ("espn", "scores365"):
            raise ValueError("Event comparison currently supports ESPN and 365Scores")
        if not {"matches", "match_events"} <= set(dataset.metadata.tables):
            raise ValueError("Both datasets must select matches and match_events")
        identifiers = {row.match_id for row in dataset.match_records}
        if any(row.match_id is None or row.match_id not in identifiers for row in dataset.match_event_records):
            raise ValueError("Events require a matching native match ID")
    linkage = link_dataset_matches(left, right, identities=identities, tolerance_seconds=tolerance_seconds)
    metadata = tuple(_metadata(_metadata_json(dataset.metadata)) for dataset in (left, right))
    coverage = tuple(_coverage(dataset) for dataset in (left, right))
    times = [{row.match_id: row.fetched_at for row in side} for side in coverage]
    chosen = [tuple(row for row in dataset.match_event_records if row.event_type in selected) for dataset in (left, right)]
    excluded = [tuple(row for row in dataset.match_event_records if row.event_type not in selected) for dataset in (left, right)]
    grouped = [defaultdict(list), defaultdict(list)]
    for side, records in enumerate(chosen):
        for row in records:
            grouped[side][row.match_id].append(row)
    rows = []
    same_source = metadata[0].source == metadata[1].source

    def append(first, second, left_id, right_id, status, reason=None, candidates=()):
        different, unknown = _compare(first, second, identities, periods, same_source) if first is not None and second is not None else ((), ())
        if first is not None and second is not None:
            status = "different" if different else "equal"
        rows.append(MatchEventComparison(metadata[0].source, left_id, metadata[1].source, right_id,
                                         first, second, status, reason, different, unknown, tuple(candidates),
                                         times[0].get(left_id), times[1].get(right_id)))

    for link in linkage.links:
        firsts, seconds = grouped[0][link.left_match_id], grouped[1][link.right_match_id]
        used_first, used_second = set(), set()
        if same_source and link.left_match_id == link.right_match_id:
            native = {row.event_id: index for index, row in enumerate(seconds) if row.event_id is not None}
            for index, row in enumerate(firsts):
                if row.event_id is not None and row.event_id in native:
                    other = native[row.event_id]
                    append(row, seconds[other], link.left_match_id, link.right_match_id, "equal", "native_event_id")
                    used_first.add(index)
                    used_second.add(other)
        signatures = [{i: _signature(row, identities, periods, same_source) for i, row in enumerate(side) if i not in used}
                      for side, used in ((firsts, used_first), (seconds, used_second))]
        candidates, reverse = defaultdict(list), defaultdict(list)
        right_by_signature = defaultdict(list)
        for j, (signature, _) in signatures[1].items():
            if signature is not None:
                right_by_signature[signature].append(j)
        for i, (signature, _) in signatures[0].items():
            if signature is None:
                continue
            for j in right_by_signature[signature]:
                if same_source and firsts[i].event_id is not None and seconds[j].event_id is not None:
                    continue
                if _near(firsts[i], seconds[j], minute_tolerance):
                    candidates[i].append(j)
                    reverse[j].append(i)
        for i, possible in candidates.items():
            if len(possible) == 1 and len(reverse[possible[0]]) == 1:
                j = possible[0]
                append(firsts[i], seconds[j], link.left_match_id, link.right_match_id, "equal")
                used_first.add(i)
                used_second.add(j)
        for side, (records, used, choices) in enumerate(((firsts, used_first, candidates), (seconds, used_second, reverse))):
            for i, row in enumerate(records):
                if i in used:
                    continue
                _, reason = signatures[side][i]
                possible = choices[i]
                status = "unresolved" if reason else "ambiguous" if possible else "unmatched"
                others = seconds if side == 0 else firsts
                append(row if side == 0 else None, row if side == 1 else None,
                       link.left_match_id, link.right_match_id, f"{status}_{'left' if side == 0 else 'right'}",
                       reason or ("multiple_candidates" if possible else "no_candidate"),
                       (_reference(others[j]) for j in possible))
    linked = ({item.left_match_id for item in linkage.links}, {item.right_match_id for item in linkage.links})
    for side, records in enumerate(chosen):
        ambiguous = linkage.ambiguous_left if side == 0 else linkage.ambiguous_right
        for row in records:
            if row.match_id not in linked[side]:
                append(row if side == 0 else None, row if side == 1 else None,
                       row.match_id if side == 0 else None, row.match_id if side == 1 else None,
                       f"unresolved_{'left' if side == 0 else 'right'}",
                       "match_ambiguous" if row.match_id in ambiguous else "match_unlinked")
    return MatchEventsReport(
        linkage, tuple(rows), *metadata, tuple(left.errors), tuple(right.errors), *validations,
        left.complete, right.complete, *coverage, *excluded, minute_tolerance, float(tolerance_seconds),
        tuple((source, native, canonical) for (source, native), canonical in sorted(periods.items())), selected, (
            "Equal means agreement of known comparable fields; unknown fields remain unverified.",
            "No names, list positions, nearest-event choices or separate athlete IDs establish cross-source player identity.",
            "Only explicit event-task timestamps are used; multiple conflicting timestamps leave row provenance unknown.",
            "Unmatched events do not prove source absence: collections and partial-task coverage can differ.",
            "Shootouts use explicit player/period identity; repeated attempts by one player remain ambiguous.",
        ),
    )
