"""Explicit source identity mappings and conservative match linkage; no pandas."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

from .normalized import SCHEMA_VERSION


@dataclass(frozen=True)
class EntityAlias:
    """One native competition/team ID linked to a caller-defined identity."""

    kind: str
    canonical_id: str
    source: str
    source_id: str


class IdentityMap:
    """Caller-owned equivalences. Names are never used as identity evidence."""

    def __init__(self, aliases=()):
        self._aliases = {}
        for alias in aliases:
            if not isinstance(alias, EntityAlias) or alias.kind not in ("competition", "team"):
                raise ValueError("IdentityMap requires competition/team EntityAlias entries")
            if any(
                not isinstance(value, str) or not value
                for value in (alias.canonical_id, alias.source, alias.source_id)
            ):
                raise ValueError("Alias IDs and source must be nonempty strings")
            key = (alias.kind, alias.source, alias.source_id)
            if key in self._aliases and self._aliases[key] != alias.canonical_id:
                raise ValueError(f"Conflicting identity for {key}")
            self._aliases[key] = alias.canonical_id

    def resolve(self, kind, source, source_id):
        return self._aliases.get((kind, source, str(source_id))) if source_id is not None else None


@dataclass(frozen=True)
class DatasetCompatibility:
    """Schema compatibility is distinct from verified source identities."""

    shared_tables: tuple[str, ...]
    schema_compatible: bool
    identity_compatible: bool
    issues: tuple[str, ...]

    @property
    def can_match(self):
        return (
            self.schema_compatible and self.identity_compatible and "matches" in self.shared_tables
        )


def _resolve(identities, kind, source, source_id, same_source):
    if source_id is None:
        return None
    if same_source:
        return (source, str(source_id))
    return identities.resolve(kind, source, source_id) if identities is not None else None


def _record_key(row, dataset, identities, same_source):
    comp = _resolve(
        identities,
        "competition",
        row.source,
        row.competition_id or dataset.metadata.league,
        same_source,
    )
    home = _resolve(identities, "team", row.source, row.home_team_id, same_source)
    away = _resolve(identities, "team", row.source, row.away_team_id, same_source)
    return (comp, home, away) if all(value is not None for value in (comp, home, away)) else None


def check_dataset_compatibility(
    left, right, *, identities: IdentityMap | None = None
) -> DatasetCompatibility:
    """Inspect schemas, selected tables and explicit competition/team mappings.

    complete is download coverage, not proof that two source calendars coincide.
    Unknown identities, missing kickoff times and provider-specific metrics are
    reported. No names, scores, statuses or xG values establish equivalence.
    """
    from ._dataset_storage import _validate_records
    from .datasets import SoccerDataset
    from .normalized.schema import TABLE_MODELS

    if not isinstance(left, SoccerDataset) or not isinstance(right, SoccerDataset):
        raise TypeError("Expected two SoccerDataset objects")
    if identities is not None and not isinstance(identities, IdentityMap):
        raise TypeError("identities must be an IdentityMap")
    shared = tuple(
        table
        for table in TABLE_MODELS
        if table in left.metadata.tables and table in right.metadata.tables
    )
    issues = []
    valid = left.metadata.schema_version == right.metadata.schema_version == SCHEMA_VERSION
    if not valid:
        issues.append("Unsupported or different schema versions")
    attributes = {
        "matches": "match_records",
        "teams": "team_records",
        "standings": "standing_records",
        "match_stats": "match_stat_records",
        "shots": "shot_records",
        "player_stats": "player_stat_records",
        "players": "player_records",
        "market_values": "market_value_records",
        "transfers": "transfer_records",
    }
    for dataset in (left, right):
        try:
            if any(table not in attributes for table in dataset.metadata.tables):
                raise ValueError("Unknown selected table")
            for table, attribute in attributes.items():
                records = getattr(dataset, attribute)
                if records and table not in dataset.metadata.tables:
                    raise ValueError(f"Unselected table {table} contains records")
                _validate_records(records, table)
                if any(row.source != dataset.metadata.source for row in records):
                    raise ValueError("Record source conflicts with dataset metadata")
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            valid = False
            issues.append(f"Invalid {dataset.metadata.source} records: {exc}")
    if not valid:
        return DatasetCompatibility(shared, False, False, tuple(issues))
    same_source = left.metadata.source == right.metadata.source
    comp_left, comp_right = (
        _resolve(
            identities, "competition", dataset.metadata.source, dataset.metadata.league, same_source
        )
        for dataset in (left, right)
    )
    identity_ok = comp_left is not None and comp_left == comp_right
    if not identity_ok:
        issues.append("Competition identities are missing or differ")
    if not shared:
        issues.append("No selected tables in common")
    if "matches" not in shared:
        issues.append("Match linkage requires matches in both datasets")
    if left.metadata.season != right.metadata.season:
        issues.append(
            "Caller season labels differ; labels alone do not establish native season equivalence"
        )
    for dataset in (left, right):
        if not dataset.complete:
            issues.append(f"{dataset.metadata.source} has incomplete download coverage")
        team_ids = [row.team_id for row in (*dataset.team_records, *dataset.standing_records)]
        if any(
            _resolve(identities, "team", dataset.metadata.source, team_id, same_source) is None
            for team_id in team_ids
        ):
            identity_ok = False
            issues.append(f"{dataset.metadata.source} has unmapped teams in team/standings tables")
        if "matches" in dataset.metadata.tables and not dataset.match_records:
            issues.append(f"{dataset.metadata.source} has no matches to link")
        if any(
            _record_key(row, dataset, identities, same_source) is None
            for row in dataset.match_records
        ):
            identity_ok = False
            issues.append(f"{dataset.metadata.source} has unmapped competition/team identities")
        if any(row.kickoff is None for row in dataset.match_records):
            issues.append(f"{dataset.metadata.source} has matches without kickoff times")
        match_ids = [row.match_id for row in dataset.match_records]
        if None in match_ids or len(match_ids) != len(set(match_ids)):
            valid = False
            issues.append(f"{dataset.metadata.source} has missing or duplicate match IDs")
    if not same_source:
        issues.append(
            "Status codes, score conventions, xG models and shot coordinates retain source semantics"
        )
    return DatasetCompatibility(shared, valid, identity_ok, tuple(issues))


@dataclass(frozen=True)
class MatchLink:
    left_source: str
    left_match_id: str
    right_source: str
    right_match_id: str
    kickoff_difference_seconds: float


@dataclass(frozen=True)
class MatchLinkResult:
    compatibility: DatasetCompatibility
    links: tuple[MatchLink, ...]
    unmatched_left: tuple[str, ...]
    unmatched_right: tuple[str, ...]
    ambiguous_left: tuple[str, ...]
    ambiguous_right: tuple[str, ...]


def link_dataset_matches(
    left, right, *, identities: IdentityMap | None = None, tolerance_seconds: float = 300
) -> MatchLinkResult:
    """Link one-to-one matches using mapped competition, ordered teams and UTC time.

    Rescheduled games outside the tolerance remain unmatched. A candidate is
    linked only if both sides have exactly one candidate. Input records and
    source IDs remain unchanged. Partial mappings may yield partial links.
    """
    if (
        isinstance(tolerance_seconds, bool)
        or not math.isfinite(tolerance_seconds)
        or tolerance_seconds < 0
    ):
        raise ValueError("tolerance_seconds must be finite and nonnegative")
    report = check_dataset_compatibility(left, right, identities=identities)
    if not report.schema_compatible or "matches" not in report.shared_tables:
        raise ValueError("Match linkage requires valid schemas and selected match tables")
    same_source = left.metadata.source == right.metadata.source
    right_by_key = defaultdict(list)
    for row in right.match_records:
        key = _record_key(row, right, identities, same_source)
        if key is not None and row.kickoff is not None:
            right_by_key[key].append(row)
    candidates, reverse = defaultdict(list), defaultdict(list)
    for row in left.match_records:
        key = _record_key(row, left, identities, same_source)
        if key is None or row.kickoff is None:
            continue
        for other in right_by_key.get(key, ()):
            difference = abs((row.kickoff - other.kickoff).total_seconds())
            if difference <= tolerance_seconds:
                candidates[row.match_id].append((other.match_id, difference))
                reverse[other.match_id].append(row.match_id)
    links = tuple(
        MatchLink(left.metadata.source, match_id, right.metadata.source, values[0][0], values[0][1])
        for match_id, values in candidates.items()
        if len(values) == 1 and len(reverse[values[0][0]]) == 1
    )
    linked_left, linked_right = (
        {link.left_match_id for link in links},
        {link.right_match_id for link in links},
    )
    ambiguous_left = tuple(
        row.match_id
        for row in left.match_records
        if len(candidates[row.match_id]) > 1
        or any(len(reverse[item[0]]) > 1 for item in candidates[row.match_id])
    )
    ambiguous_right = tuple(
        row.match_id
        for row in right.match_records
        if len(reverse[row.match_id]) > 1
        or any(len(candidates[item]) > 1 for item in reverse[row.match_id])
    )
    return MatchLinkResult(
        report,
        links,
        tuple(
            row.match_id
            for row in left.match_records
            if row.match_id not in linked_left and row.match_id not in ambiguous_left
        ),
        tuple(
            row.match_id
            for row in right.match_records
            if row.match_id not in linked_right and row.match_id not in ambiguous_right
        ),
        ambiguous_left,
        ambiguous_right,
    )
