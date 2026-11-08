"""Explicit entity aliases and match linkage using IDs and kickoff times."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlsplit

from .normalized import SCHEMA_VERSION


@dataclass(frozen=True)
class EntityAlias:
    """Explicit identity, optionally scoped to a player's native team and UTC time.

    valid_from is inclusive and valid_until exclusive. Scoped player aliases
    require the corresponding context to resolve; absent context is not a match.
    Evidence is optional caller provenance, never an inferred confidence score.
    """

    kind: str
    canonical_id: str
    source: str
    source_id: str
    team_id: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    source_url: str | None = None
    verified_at: datetime | None = None


def _alias_time(value):
    if value is not None:
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Identity timestamps require aware datetimes")
        return value.astimezone(timezone.utc)
    return None


def _overlap(first, second):
    if first.team_id is not None and second.team_id is not None and first.team_id != second.team_id:
        return False
    return not (first.valid_until is not None and second.valid_from is not None and first.valid_until <= second.valid_from
                or second.valid_until is not None and first.valid_from is not None and second.valid_until <= first.valid_from)


@dataclass(frozen=True)
class IdentityResolution:
    """Identity decision with applicable evidence or an explicit context failure."""

    canonical_id: str | None
    status: str
    aliases: tuple[EntityAlias, ...] = ()


class IdentityMap:
    """Caller-supplied competition/team/player aliases, without name matching.

    Player source_id is the ID used by the normalized record. For 365Scores
    events it is the member ID, not the separate athlete ID. The catalog does
    not supply player aliases. Callers must review those equivalences.
    """

    def __init__(self, aliases=()):
        self._aliases = defaultdict(list)
        entries = []
        for alias in aliases:
            if not isinstance(alias, EntityAlias) or alias.kind not in ("competition", "team", "player"):
                raise ValueError("IdentityMap requires competition/team/player EntityAlias entries")
            if any(
                not isinstance(value, str) or not value
                for value in (alias.canonical_id, alias.source, alias.source_id)
            ):
                raise ValueError("Alias IDs and source must be nonempty strings")
            if alias.kind != "player" and any(value is not None for value in (alias.team_id, alias.valid_from, alias.valid_until)):
                raise ValueError("Only player aliases support team/date scope")
            if alias.team_id is not None and (not isinstance(alias.team_id, str) or not alias.team_id.strip() or alias.team_id != alias.team_id.strip()):
                raise ValueError("Scoped team_id must be a nonblank native string")
            for value in (alias.valid_from, alias.valid_until, alias.verified_at):
                _alias_time(value)
            if alias.valid_from is not None and alias.valid_until is not None and alias.valid_from >= alias.valid_until:
                raise ValueError("Player identity validity must have positive duration")
            if alias.source_url is not None:
                if not isinstance(alias.source_url, str):
                    raise ValueError("Identity evidence requires an HTTP(S) URL")
                url = urlsplit(alias.source_url)
                if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password:
                    raise ValueError("Identity evidence requires an HTTP(S) URL without credentials")
            key = (alias.kind, alias.source, alias.source_id)
            if any(other.canonical_id != alias.canonical_id and _overlap(other, alias) for other in self._aliases[key]):
                raise ValueError(f"Conflicting identity for {key}")
            if alias not in self._aliases[key]:
                self._aliases[key].append(alias)
                entries.append(alias)
        self._entries = tuple(entries)

    def resolve(self, kind, source, source_id, *, team_id=None, at=None):
        """Resolve an explicit alias with sufficient team/time context, or None."""
        return self.lookup(kind, source, source_id, team_id=team_id, at=at).canonical_id

    def lookup(self, kind, source, source_id, *, team_id=None, at=None) -> IdentityResolution:
        """Explain resolved, unmapped, context_required, out_of_scope or ambiguous."""
        at = _alias_time(at)
        candidates = self._aliases.get((kind, source, str(source_id)), ()) if source_id is not None else ()
        matching, missing = [], False
        for alias in candidates:
            if alias.team_id is not None and team_id is not None and alias.team_id != str(team_id):
                continue
            if at is not None and (alias.valid_from is not None and at < alias.valid_from
                                   or alias.valid_until is not None and at >= alias.valid_until):
                continue
            if (alias.team_id is not None and team_id is None
                    or at is None and (alias.valid_from is not None or alias.valid_until is not None)):
                missing = True
                continue
            matching.append(alias)
        identities = {alias.canonical_id for alias in matching}
        if len(identities) == 1:
            return IdentityResolution(next(iter(identities)), "resolved", tuple(matching))
        status = "ambiguous" if identities else "context_required" if missing else "out_of_scope" if candidates else "unmapped"
        return IdentityResolution(None, status, tuple(matching) if matching else tuple(candidates))

    @property
    def aliases(self) -> tuple[EntityAlias, ...]:
        """Immutable entries suitable for saving or extending this map."""
        return self._entries

    def to_dict(self) -> dict:
        """Versioned JSON-compatible aliases, preserving scope and review evidence."""
        from dataclasses import asdict

        entries = []
        for alias in self.aliases:
            row = asdict(alias)
            for field in ("valid_from", "valid_until", "verified_at"):
                row[field] = row[field].isoformat() if row[field] is not None else None
            entries.append(row)
        return {"format": "easysoccerdata-identities", "format_version": 1, "aliases": entries}

    @classmethod
    def from_dict(cls, data) -> IdentityMap:
        """Read versioned identities or an older JSON list of EntityAlias entries."""
        if isinstance(data, dict):
            if (set(data) != {"format", "format_version", "aliases"} or data["format"] != "easysoccerdata-identities"
                    or type(data["format_version"]) is not int or data["format_version"] != 1):
                raise ValueError("Invalid identity format/version")
            data = data["aliases"]
        if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
            raise ValueError("Identity aliases require a JSON list")
        entries = []
        try:
            for item in data:
                row = dict(item)
                for field in ("valid_from", "valid_until", "verified_at"):
                    value = row.get(field)
                    if value is not None:
                        if not isinstance(value, str):
                            raise ValueError("Identity dates require ISO timestamps")
                        row[field] = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
                entries.append(EntityAlias(**row))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid identity entry: {exc}") from exc
        return cls(entries)

    def with_aliases(self, aliases) -> IdentityMap:
        """Return an independent extended map, rejecting conflicting native IDs."""
        return IdentityMap((*self.aliases, *aliases))


@dataclass(frozen=True)
class DatasetCompatibility:
    """Schema validity, explicit identity coverage and diagnostic messages.

    identity_compatible checks competition and team mappings, not player
    identities or metric equivalence. issues also includes informational notes
    about partial coverage and source semantics; a nonempty issues tuple does
    not necessarily mean schema_compatible is false.
    """

    shared_tables: tuple[str, ...]
    schema_compatible: bool
    identity_compatible: bool
    issues: tuple[str, ...]

    @property
    def can_match(self):
        """Whether schemas, match selection and identity coverage permit linkage.

        Matching also depends on the records:
        kickoff times can be absent, outside tolerance or ambiguous. The linker
        can still produce partial links with incomplete identity coverage.
        """
        return (
            self.schema_compatible and self.identity_compatible and "matches" in self.shared_tables
        )


def _resolve(identities, kind, source, source_id, same_source, *, team_id=None, at=None):
    if source_id is None:
        return None
    if same_source:
        return (source, str(source_id))
    return identities.resolve(kind, source, source_id, team_id=team_id, at=at) if identities is not None else None


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
    """Check schema validity and competition/team identity coverage across two datasets.

    Args:
        left (SoccerDataset): First ``SoccerDataset`` to inspect.
        right (SoccerDataset): Second ``SoccerDataset`` to inspect.
        identities: Optional ``IdentityMap`` providing canonical competition
            and team mappings when comparing different providers.

    Returns:
        DatasetCompatibility: Report detailing shared tables, schema validity,
            identity coverage, and diagnostic notes.

    Raises:
        TypeError: If ``left`` or ``right`` is not a ``SoccerDataset``.
        ValueError: If ``identities`` is not an ``IdentityMap`` or ``None``.
    """
    from ._dataset_storage import _RECORDS, _validate_records
    from .datasets import SoccerDataset
    from .normalized.schema import TABLE_MODELS

    if not isinstance(left, SoccerDataset) or not isinstance(right, SoccerDataset):
        raise TypeError("Expected two SoccerDataset objects")
    if identities is not None and not isinstance(identities, IdentityMap):
        raise ValueError("identities must be an IdentityMap")
    shared = tuple(
        table
        for table in TABLE_MODELS
        if table in left.metadata.tables and table in right.metadata.tables
    )
    issues = []
    valid = left.metadata.schema_version == right.metadata.schema_version == SCHEMA_VERSION
    if not valid:
        issues.append("Unsupported or different schema versions")
    attributes = _RECORDS
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
    """Link one-to-one matches between two datasets by mapped competition, teams, and UTC kickoff.

    Args:
        left (SoccerDataset): First ``SoccerDataset`` containing ``matches``.
        right (SoccerDataset): Second ``SoccerDataset`` containing ``matches``.
        identities: ``IdentityMap`` mapping competition and team IDs across
            providers (optional when both datasets share the same ``source``).
        tolerance_seconds: Maximum allowed absolute difference in seconds
            between UTC kickoffs for a candidate pair (default ``300``).

    Returns:
        MatchLinkResult: One-to-one ``links`` alongside ``unmatched_left``,
            ``unmatched_right``, ``ambiguous_left``, and ``ambiguous_right``.

    Raises:
        TypeError: If ``left`` or ``right`` is not a ``SoccerDataset``.
        ValueError: If ``tolerance_seconds`` is invalid or either dataset
            lacks valid ``matches`` tables.
    """
    if (
        type(tolerance_seconds) not in (int, float)
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
