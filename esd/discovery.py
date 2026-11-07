"""Competition and season discovery with source-native identifiers and query scope."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from os import PathLike
from urllib.parse import unquote, urlsplit

from ._response_reader import ResponseReader
from .cache import CachePolicy, ResponseCache
from .espn.endpoints import ESPNEndpoints
from .exceptions import ESDException, SourceError
from .goaloo.endpoints import GoalooEndpoints
from .promiedos.endpoints import PromiedosEndpoints
from .promiedos.service import _PROMIEDOS_HEADERS
from .scores365.endpoints import Scores365Endpoints
from .sofascore.endpoints import SofascoreEndpoints
from .utils import get_api_json


class DiscoveryNotSupported(ESDException):
    """This discovery operation has no implemented adapter; selection is manual."""


@dataclass(frozen=True)
class CompetitionInfo:
    """competition_id selects datasets. native_id also retains ESPN's numeric ID."""

    source: str
    competition_id: str
    name: str
    native_id: str


@dataclass(frozen=True)
class SeasonInfo:
    """Native season ID and labels, without deriving a caller year from the name.

    year is populated only by ESPN's explicit season-year index. source_season
    retains Goaloo's selection string or Sofascore's native year/period label.
    Dataset loaders still require their documented provider-specific arguments.
    """

    source: str
    competition_id: str
    season_id: str
    name: str | None = None
    year: int | None = None
    source_season: str | None = None


@dataclass(frozen=True)
class DiscoveryCapabilities:
    """Implemented query modes. None means manual selection for this operation."""

    source: str
    competitions: str | None = None
    seasons: str | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class DiscoveryResult:
    """Immutable records and the scope/original fetch time of one source request.

    Scope describes a source listing, search, category, date or season response.
    No result asserts that every competition or historical season is included.
    cached reports reuse of the original response, not a new source observation.
    """

    source: str
    scope: str
    fetched_at: datetime
    cached: bool
    competitions: tuple[CompetitionInfo, ...] = ()
    seasons: tuple[SeasonInfo, ...] = ()
    competition_id: str | None = None
    query: str | None = None
    category_id: str | None = None
    date: str | None = None
    notes: tuple[str, ...] = ()


_CAPABILITIES = {
    "espn": DiscoveryCapabilities("espn", "listing", "index", (
        "Competition listing uses ESPN's soccer dropdown; competition_id is its slug, native_id its numeric ID.",
        "Season index entries are native years, not inferred start/end ranges.",
    )),
    "scores365": DiscoveryCapabilities("scores365", "search", "competition_response", (
        "Competition search requires query and filters to football sportId=1.",
        "Competition details may include only the current season; no complete history is asserted.",
    )),
    "sofascore": DiscoveryCapabilities("sofascore", "category", "index", (
        "A football category_id is required for competitions; all returned groups are inspected.",
        "Source blocks are propagated without launching a browser.",
    )),
    "goaloo": DiscoveryCapabilities("goaloo", seasons="index", notes=(
        "Choose the competition ID manually; season strings are returned exactly as listed.",
    )),
    "promiedos": DiscoveryCapabilities("promiedos", "date", notes=(
        "Explicit date required; only leagues listed on that source day are returned.",
        "No historical season index is implemented.",
    )),
    **{source: DiscoveryCapabilities(source, notes=(
        "No verified competition/season discovery adapter is implemented; use manual selection.",
    )) for source in ("fbref", "understat", "besoccer", "transfermarkt")},
}


def get_discovery_capabilities(source: str | None = None) -> DiscoveryCapabilities | dict[str, DiscoveryCapabilities]:
    """Inspect all nine adapter contracts without network or optional imports."""
    if source is None:
        return dict(_CAPABILITIES)
    if not isinstance(source, str) or source not in _CAPABILITIES:
        raise ValueError(f"Unknown source: {source}")
    return _CAPABILITIES[source]


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise SourceError(f"Discovery response is missing {field}")
    return value


def _id(value):
    if type(value) is int:
        return str(value)
    return _text(value, "native ID")


def _numeric(value, field):
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).isascii() or not str(value).isdigit() or int(value) < 1:
        raise ValueError(f"{field} must be a positive native numeric ID")
    return str(int(value))


def _rows(data, key):
    if not isinstance(data, dict) or not isinstance(data.get(key), list):
        raise SourceError(f"Discovery response is missing its {key} list")
    return data[key]


def _unique(rows, field):
    result = {}
    for row in rows:
        key = getattr(row, field)
        if key in result and result[key] != row:
            raise SourceError(f"Conflicting discovery entries for {field}={key}")
        result[key] = row
    return tuple(result.values())


def _competitions(data, source):
    if source == "espn":
        return _unique((CompetitionInfo(source, _text(row.get("slug"), "league slug"),
                                        _text(row.get("name"), "name"), _id(row.get("id")))
                        for row in _rows(data, "leagues")), "competition_id")
    if source == "scores365":
        rows = _rows(data, "competitions")
        if any(type(row.get("sportId")) is not int for row in rows):
            raise SourceError("Competition search is missing sportId")
        return _unique((CompetitionInfo(source, _id(row.get("id")), _text(row.get("name"), "name"), _id(row.get("id")))
                        for row in rows if row["sportId"] == 1), "competition_id")
    if source == "sofascore":
        rows = [row for group in _rows(data, "groups") for row in _rows(group, "uniqueTournaments")]
    else:
        rows = _rows(data, "leagues")
    return _unique((CompetitionInfo(source, _id(row.get("id")), _text(row.get("name"), "name"), _id(row.get("id")))
                    for row in rows), "competition_id")


def _seasons(data, source, competition):
    if source == "goaloo":
        return _unique((SeasonInfo(source, competition, _text(value, "season"), value, source_season=value)
                        for value in _rows(data, "SeasonList")), "season_id")
    if source == "espn":
        rows = _rows(data, "items")
        if (type(data.get("pageCount")) is not int or data["pageCount"] not in (0, 1)
                or type(data.get("count")) is not int or data["count"] != len(rows)):
            raise SourceError("ESPN season index is incomplete or paginated")
        result = []
        for row in rows:
            ref = urlsplit(_text(row.get("$ref"), "season reference"))
            parts = ref.path.rstrip("/").split("/")
            if (ref.hostname != "sports.core.api.espn.com" or ref.scheme not in ("http", "https")
                    or len(parts) != 8 or parts[:5] != ["", "v2", "sports", "soccer", "leagues"]
                    or unquote(parts[5]) != competition or parts[6] != "seasons"):
                raise SourceError("ESPN season reference does not belong to the selected competition")
            year = unquote(parts[-1])
            if len(year) != 4 or not year.isascii() or not year.isdigit() or int(year) < 1000:
                raise SourceError("ESPN season index has an invalid native year")
            result.append(SeasonInfo(source, competition, year, year=int(year)))
        return _unique(result, "season_id")
    if source == "scores365":
        competitions = [row for row in _rows(data, "competitions") if _id(row.get("id")) == competition]
        if len(competitions) != 1 or type(competitions[0].get("sportId")) is not int or competitions[0]["sportId"] != 1:
            raise SourceError("365Scores did not return the selected football competition")
        return _unique((SeasonInfo(source, competition, _id(row.get("num")), _text(row.get("name"), "season name"))
                        for row in _rows(competitions[0], "seasons")), "season_id")
    return _unique((SeasonInfo(source, competition, _id(row.get("id")), _text(row.get("name"), "season name"),
                              source_season=_id(row["year"]) if row.get("year") is not None else None)
                    for row in _rows(data, "seasons")), "season_id")


def _read(source, url, parse, cache_dir, cache_policy, refresh, proxies):
    policy = cache_policy if cache_policy is not None else CachePolicy()
    if not isinstance(policy, CachePolicy):
        raise TypeError("cache_policy must be a CachePolicy")
    cache = ResponseCache(cache_dir) if cache_dir is not None else None
    headers = _PROMIEDOS_HEADERS if source == "promiedos" else None
    reader = ResponseReader(lambda address: get_api_json(address, proxies=proxies, headers=headers),
                            cache=cache, refresh=refresh)

    def validate(data):
        try:
            return parse(data)
        except (TypeError, AttributeError, KeyError, ValueError) as exc:
            raise SourceError(f"Invalid discovery response: {exc}") from exc

    data = reader.read(url, ttl=policy.calendar_ttl, validate=validate)
    return validate(data), datetime.fromtimestamp(reader.last_response.fetched_at, timezone.utc), reader.last_response.cached


def list_competitions(
    source: str, *, query: str | None = None, category_id: int | str | None = None,
    date: str | None = None, cache_dir: str | PathLike | None = None,
    cache_policy: CachePolicy | None = None, refresh: bool = False, proxies: dict | None = None,
) -> DiscoveryResult:
    """List a provider's competitions with explicit listing/search/category/date scope.

    ESPN uses its soccer dropdown. 365Scores requires query. Sofascore requires a
    football category_id, such as 1 for England. Promiedos requires an ISO source
    date. query filters returned names locally except on 365Scores, where it is
    sent to search. Other adapters raise DiscoveryNotSupported before I/O.
    """
    if not isinstance(source, str):
        raise ValueError("source must be a provider name")
    capability = get_discovery_capabilities(source)
    if capability.competitions is None:
        raise DiscoveryNotSupported(f"{source} competition discovery is not implemented; choose its ID manually")
    if query is not None and (not isinstance(query, str) or not query.strip()):
        raise ValueError("query must be nonempty text")
    if category_id is not None and source != "sofascore":
        raise ValueError("category_id is supported only for Sofascore discovery")
    if date is not None and source != "promiedos":
        raise ValueError("date is supported only for Promiedos discovery")
    category = None
    if source == "scores365":
        if query is None:
            raise ValueError("365Scores competition discovery requires query")
        url = Scores365Endpoints().search(query)
    elif source == "sofascore":
        category = _numeric(category_id, "category_id")
        url = SofascoreEndpoints().tournaments_endpoint(int(category))
    elif source == "promiedos":
        if not isinstance(date, str) or datetime.strptime(date, "%Y-%m-%d").date().isoformat() != date:
            raise ValueError("Promiedos discovery requires an explicit YYYY-MM-DD date")
        url = PromiedosEndpoints().events_url(date)
    else:
        url = ESPNEndpoints().competitions()
    rows, fetched, cached = _read(source, url, lambda data: _competitions(data, source), cache_dir, cache_policy, refresh, proxies)
    if query is not None and source != "scores365":
        rows = tuple(row for row in rows if query.casefold() in row.name.casefold())
    return DiscoveryResult(source, capability.competitions, fetched, cached, competitions=rows,
                           query=query, category_id=category, date=date, notes=capability.notes)


def list_seasons(
    source: str, competition_id: int | str, *, cache_dir: str | PathLike | None = None,
    cache_policy: CachePolicy | None = None, refresh: bool = False, proxies: dict | None = None,
) -> DiscoveryResult:
    """List native seasons without guessing years from names or filling absent history.

    ESPN uses a slug and native year index. Sofascore IDs select season_id;
    Goaloo strings select source_season. 365Scores returns only seasons included
    in its competition response, which may omit history. Each call fetches one
    response; paginated ESPN results raise instead of returning a partial index.
    """
    if not isinstance(source, str):
        raise ValueError("source must be a provider name")
    capability = get_discovery_capabilities(source)
    if capability.seasons is None:
        raise DiscoveryNotSupported(f"{source} season discovery is not implemented; choose its selection manually")
    if source == "espn":
        if not isinstance(competition_id, str) or not competition_id.strip():
            raise ValueError("ESPN competition_id must be its league slug")
        competition = competition_id
        url = ESPNEndpoints().seasons(competition)
    else:
        competition = _numeric(competition_id, "competition_id")
        if source == "goaloo":
            url = GoalooEndpoints().seasons_endpoint(int(competition))
        elif source == "scores365":
            url = Scores365Endpoints().competition_seasons(int(competition))
        else:
            url = SofascoreEndpoints().tournament_seasons_endpoint(int(competition))
    rows, fetched, cached = _read(source, url, lambda data: _seasons(data, source, competition), cache_dir, cache_policy, refresh, proxies)
    return DiscoveryResult(source, capability.seasons, fetched, cached, seasons=rows,
                           competition_id=competition, notes=capability.notes)
