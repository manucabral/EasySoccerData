"""Explicit competition/team identities with source evidence and native selectors."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from .compatibility import EntityAlias, IdentityMap
from .dataset_capabilities import get_dataset_capabilities
from .discovery import DiscoveryResult, SeasonInfo, list_seasons


def _text(value):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError("Catalog names, IDs and versions require nonblank, trimmed strings")
    return value


def _key(value):
    if not isinstance(value, str):
        raise ValueError("Catalog lookup keys require text")
    return " ".join(_text(value.strip()).casefold().split())


@dataclass(frozen=True)
class CatalogReference:
    """One reviewed provider ID. source_id selects datasets; native_id is separate.

    For ESPN competitions, source_id is the league slug and native_id the numeric
    ID. source_url and verified_at record the review evidence, not live uptime.
    """

    source: str
    source_id: str
    source_url: str
    verified_at: datetime
    native_id: str | None = None

    def __post_init__(self):
        get_dataset_capabilities(_text(self.source))
        _text(self.source_id)
        if self.native_id is not None:
            _text(self.native_id)
        url = urlsplit(_text(self.source_url))
        if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password:
            raise ValueError("Catalog evidence requires an HTTP(S) URL without credentials")
        if not isinstance(self.verified_at, datetime) or self.verified_at.tzinfo is None or self.verified_at.utcoffset() is None:
            raise ValueError("Catalog verification timestamps require a timezone")
        object.__setattr__(self, "verified_at", self.verified_at.astimezone(timezone.utc))


def _entity(entity):
    _text(entity.canonical_id)
    _text(entity.name)
    if isinstance(entity.references, (str, bytes)) or isinstance(entity.aliases, (str, bytes)):
        raise ValueError("Catalog references and aliases require sequences")
    references, aliases = tuple(entity.references), tuple(entity.aliases)
    if not references or any(not isinstance(ref, CatalogReference) for ref in references):
        raise ValueError("A catalog entity requires reviewed CatalogReference entries")
    if len({ref.source for ref in references}) != len(references):
        raise ValueError("An entity can have only one reference per source")
    for alias in aliases:
        _text(alias)
    object.__setattr__(entity, "references", references)
    object.__setattr__(entity, "aliases", aliases)


def _reference(entity, source):
    get_dataset_capabilities(_text(source))
    for reference in entity.references:
        if reference.source == source:
            return reference
    raise ValueError(f"No reviewed {source} ID for {entity.canonical_id}")


@dataclass(frozen=True)
class CatalogCompetition:
    """A named competition with explicit source IDs and curated lookup aliases."""

    canonical_id: str
    name: str
    references: tuple[CatalogReference, ...]
    aliases: tuple[str, ...] = ()

    def __post_init__(self):
        _entity(self)

    def for_source(self, source: str) -> CatalogReference:
        """Get a reviewed dataset selector, or raise without guessing an ID."""
        return _reference(self, source)


@dataclass(frozen=True)
class CatalogTeam:
    """One club identity. Entries do not assert membership in a season or squad."""

    canonical_id: str
    name: str
    references: tuple[CatalogReference, ...]
    aliases: tuple[str, ...] = ()

    def __post_init__(self):
        _entity(self)

    def for_source(self, source: str) -> CatalogReference:
        """Get a reviewed native team ID, keeping the source namespace."""
        return _reference(self, source)


def _validate_entities(entries, model, kind):
    names, native = {}, {}
    for entity in entries:
        if not isinstance(entity, model):
            raise ValueError(f"Expected {model.__name__} entries")
        for name in (entity.canonical_id, entity.name, *entity.aliases):
            key = _key(name)
            if key in names and names[key] != entity.canonical_id:
                raise ValueError(f"Conflicting {kind} lookup name: {name}")
            names[key] = entity.canonical_id
        for reference in entity.references:
            key = (reference.source, reference.source_id)
            if key in native and native[key] != entity.canonical_id:
                raise ValueError(f"Conflicting {kind} native ID: {key}")
            native[key] = entity.canonical_id
    if len({entry.canonical_id for entry in entries}) != len(entries):
        raise ValueError(f"Repeated {kind} canonical ID")


def _find(entries, name):
    key = _key(name)
    for entry in entries:
        if any(_key(candidate) == key for candidate in (entry.canonical_id, entry.name, *entry.aliases)):
            return entry
    raise ValueError(f"Unknown catalog identity: {name}")


def _merge(existing, additions):
    result = {entry.canonical_id: entry for entry in existing}
    for entry in additions:
        previous = result.get(entry.canonical_id)
        if previous is None:
            result[entry.canonical_id] = entry
            continue
        if type(previous) is not type(entry) or previous.name != entry.name:
            raise ValueError(f"Conflicting catalog entity: {entry.canonical_id}")
        references = {ref.source: ref for ref in previous.references}
        for ref in entry.references:
            if ref.source in references and references[ref.source] != ref:
                raise ValueError(f"Conflicting reference: {entry.canonical_id}/{ref.source}")
            references[ref.source] = ref
        result[entry.canonical_id] = replace(previous, references=tuple(references.values()),
                                             aliases=tuple(dict.fromkeys((*previous.aliases, *entry.aliases))))
    return tuple(result.values())


@dataclass(frozen=True)
class FootballCatalog:
    """Immutable reviewed identities, independently versioned from dataset schemas.

    Lookups match only canonical IDs, names and declared aliases, ignoring case
    and whitespace. No fuzzy matching, roster/history inference
    or provider fallback is performed. Network access occurs only in list_seasons.
    """

    competitions: tuple[CatalogCompetition, ...] = ()
    teams: tuple[CatalogTeam, ...] = ()
    version: str = "custom"

    def __post_init__(self):
        _text(self.version)
        competitions, teams = tuple(self.competitions), tuple(self.teams)
        _validate_entities(competitions, CatalogCompetition, "competition")
        _validate_entities(teams, CatalogTeam, "team")
        object.__setattr__(self, "competitions", competitions)
        object.__setattr__(self, "teams", teams)

    def competition(self, name: str) -> CatalogCompetition:
        """Resolve a declared competition key without network access."""
        return _find(self.competitions, name)

    def team(self, name: str) -> CatalogTeam:
        """Resolve a declared team key without inferring season membership."""
        return _find(self.teams, name)

    def identities(self) -> IdentityMap:
        """Build an independent IdentityMap for the existing match linker."""
        return IdentityMap(EntityAlias(kind, entity.canonical_id, ref.source, ref.source_id)
                           for kind, entries in (("competition", self.competitions), ("team", self.teams))
                           for entity in entries for ref in entity.references)

    def with_entries(self, *, competitions=(), teams=(), version: str | None = None) -> FootballCatalog:
        """Extend identities/references without modifying this catalog or replacing IDs.

        Conflicting names, source IDs or review metadata raise ValueError. Use a
        new complete catalog to replace references deliberately.
        """
        competitions, teams = tuple(competitions), tuple(teams)
        if any(not isinstance(entry, CatalogCompetition) for entry in competitions) or any(not isinstance(entry, CatalogTeam) for entry in teams):
            raise ValueError("Extensions require CatalogCompetition/CatalogTeam entries")
        return FootballCatalog(_merge(self.competitions, competitions), _merge(self.teams, teams),
                               version if version is not None else f"{self.version}+custom")

    def list_seasons(self, competition: str, source: str, *, cache_dir=None, cache_policy=None,
                     refresh=False, proxies=None) -> DiscoveryResult:
        """Make one explicit discovery call using the reviewed native selector.

        Discovery preserves source limits, cached response dates and unavailable
        operations. No seasons or source years are embedded in the catalog.
        """
        reference = self.competition(competition).for_source(source)
        options = {"competition_url": reference.source_url} if source == "transfermarkt" else {}
        return list_seasons(source, reference.source_id, cache_dir=cache_dir, cache_policy=cache_policy,
                            refresh=refresh, proxies=proxies, **options)

    def dataset_options(self, competition: str, season: SeasonInfo, *, year: int | None = None) -> dict:
        """Return load_dataset keyword arguments from an explicitly selected season.

        ESPN/BeSoccer use their reported year. Other supported adapters require a
        caller year label, retaining native season_id/source_season separately.
        Labels are never parsed into years. No source requests or downloads occur.
        Transfermarkt histories/profiles do not support historical season selection.
        """
        if not isinstance(season, SeasonInfo):
            raise TypeError("Choose a SeasonInfo returned by season discovery")
        if year is not None and type(year) is not int:
            raise ValueError("Caller year must be an integer")
        reference = self.competition(competition).for_source(season.source)
        if season.competition_id != reference.source_id:
            raise ValueError("Season competition differs from the catalog source selector")
        _text(season.season_id)
        if season.source in ("espn", "besoccer"):
            if type(season.year) is not int or year is not None and year != season.year:
                raise ValueError("Use the explicit native year returned by this source")
            if season.season_id != str(season.year):
                raise ValueError("Season ID conflicts with its native year")
            year = season.year
        if type(year) is not int or not 1000 <= year <= 9999:
            raise ValueError("A four-digit caller year is required; labels are not parsed")
        options = {"source": season.source, "league": reference.source_id, "season": year}
        if season.source in ("scores365", "sofascore"):
            if not season.season_id.isascii() or not season.season_id.isdigit() or int(season.season_id) < 1:
                raise ValueError("This source requires a positive native season ID")
            options["season_id"] = season.season_id
        elif season.source == "goaloo":
            options["source_season"] = _text(season.source_season)
            if season.source_season != season.season_id:
                raise ValueError("Source season conflicts with its native selection")
        elif season.source not in ("espn", "besoccer"):
            raise ValueError("This source has no historical season selection supported by the catalog")
        return options

    def to_dict(self) -> dict:
        """Return JSON-compatible records with review provenance and format version 1."""
        def entries(rows):
            result = []
            for row in rows:
                data = asdict(row)
                data["aliases"] = list(row.aliases)
                data["references"] = [{**asdict(ref), "verified_at": ref.verified_at.isoformat()} for ref in row.references]
                result.append(data)
            return result
        return {"format": "easysoccerdata-catalog", "format_version": 1, "version": self.version,
                "competitions": entries(self.competitions), "teams": entries(self.teams)}

    @classmethod
    def from_dict(cls, data: dict) -> FootballCatalog:
        """Validate a catalog document; unknown fields/versions and conflicts raise."""
        try:
            if (set(data) != {"format", "format_version", "version", "competitions", "teams"}
                    or data["format"] != "easysoccerdata-catalog" or type(data["format_version"]) is not int
                    or data["format_version"] != 1):
                raise ValueError("Unsupported catalog format/version or fields")

            def entries(rows, model):
                if not isinstance(rows, list):
                    raise ValueError("Catalog entities must be lists")
                result = []
                for row in rows:
                    if not isinstance(row, dict) or not isinstance(row.get("references"), list) or not isinstance(row.get("aliases"), list):
                        raise ValueError("Invalid catalog entity")
                    references = []
                    for ref in row["references"]:
                        raw = ref["verified_at"]
                        if not isinstance(raw, str):
                            raise ValueError("Verification dates must be ISO timestamps")
                        stamp = datetime.fromisoformat(raw[:-1] + "+00:00" if raw.endswith("Z") else raw)
                        references.append(CatalogReference(**{**ref, "verified_at": stamp}))
                    result.append(model(**{**row, "references": tuple(references), "aliases": tuple(row["aliases"])}))
                return tuple(result)
            return cls(entries(data["competitions"], CatalogCompetition), entries(data["teams"], CatalogTeam), data["version"])
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise ValueError(f"Invalid catalog: {exc}") from exc

    def save_json(self, path) -> Path:
        """Stage a catalog document and publish to a new path without overwriting."""
        destination = Path(path).expanduser().absolute()
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"Catalog destination already exists: {destination}")
        document = json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n"
        destination.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix=".esd-catalog-", dir=destination.parent) as temporary:
            staging = Path(temporary) / "catalog.json"
            staging.write_text(document, encoding="utf-8")
            # A hard link publishes a complete file and fails if another writer
            # has already created the requested destination.
            os.link(staging, destination)
        return destination


@lru_cache(maxsize=1)
def get_catalog() -> FootballCatalog:
    """Read the bundled catalog lazily, without HTTP, pandas or PyArrow.

    The bundled sample covers three competitions and reviewed team identities
    from ESPN/365Scores. It does not assert full league/season coverage or uptime.
    """
    return FootballCatalog.from_dict(json.loads(files("esd").joinpath("data/catalog.json").read_text(encoding="utf-8")))


def open_catalog(path) -> FootballCatalog:
    """Read a caller-selected catalog file, validating its format and identities."""
    return FootballCatalog.from_dict(json.loads(Path(path).expanduser().read_text(encoding="utf-8")))
