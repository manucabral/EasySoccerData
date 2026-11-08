"""Competition and season discovery with source-native identifiers and query scope."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from os import PathLike
from urllib.parse import unquote, urlsplit

from ._discovery_html import html_seasons, transfermarkt_competitions
from ._response_reader import ResponseReader
from .besoccer.endpoints import BeSoccerEndpoints
from .cache import CachePolicy, ResponseCache
from .espn.endpoints import ESPNEndpoints
from .exceptions import ESDException, SourceError
from .goaloo.endpoints import GoalooEndpoints
from .promiedos.endpoints import PromiedosEndpoints
from .promiedos.service import _PROMIEDOS_HEADERS
from .scores365.endpoints import Scores365Endpoints
from .sofascore.endpoints import SofascoreEndpoints
from .transfermarkt.endpoints import TransfermarktEndpoints
from .utils import get_api_json, get_text


class DiscoveryNotSupported(ESDException):
    """This discovery operation has no implemented adapter; selection is manual."""


@dataclass(frozen=True)
class CompetitionInfo:
    """competition_id selects datasets. native_id also retains ESPN's numeric ID.

    Transfermarkt's source_url retains the link needed for season discovery.
    """

    source: str
    competition_id: str
    name: str
    native_id: str
    source_url: str | None = None


@dataclass(frozen=True)
class SeasonInfo:
    """Native season ID and labels, without deriving a caller year from the name.

    year is populated by ESPN's year index or BeSoccer's native year selector. source_season
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

    Scope describes a source listing, search page, category, date or season response.
    No result asserts that every competition or historical season is included.
    cached reports reuse of the original response, not a new source observation.
    source_url identifies the requested route. page is populated for Transfermarkt search.
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
    page: int | None = None
    source_url: str | None = None


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
    "besoccer": DiscoveryCapabilities("besoccer", seasons="selector", notes=(
        "Native season option values select standings years; a 2026-27 label may use 2027.",
        "Competition discovery remains manual: the listing can omit its content or return a challenge.",
    )),
    "transfermarkt": DiscoveryCapabilities("transfermarkt", "search_page", "selector", (
        "query is required; page selects one competition results page, not the full search catalogue.",
        "Seasons require competition_url from CompetitionInfo.source_url to preserve the native league/cup route.",
        "Season discovery does not make entity datasets historical: profiles remain current and histories unfiltered.",
    )),
    "fbref": DiscoveryCapabilities("fbref", notes=(
        "Competition/history pages were blocked during adapter verification; selection remains manual.",
    )),
    "understat": DiscoveryCapabilities("understat", notes=(
        "League pages returned maintenance HTML during adapter verification; selection remains manual.",
    )),
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


def _competitions(data, source, page=None):
    if source == "transfermarkt":
        return _unique((CompetitionInfo(source, row["id"], row["name"], row["id"], row["source_url"])
                        for row in _rows(transfermarkt_competitions(data, page), "competitions")), "competition_id")
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
    if source in ("besoccer", "transfermarkt"):
        return _unique((SeasonInfo(source, competition, row["id"], row["name"],
                                  year=int(row["id"]) if source == "besoccer" else None)
                        for row in _rows(html_seasons(data, source, competition), "seasons")), "season_id")
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
    if type(refresh) is not bool:
        raise ValueError("refresh must be a boolean")
    if cache_policy is not None and not isinstance(cache_policy, CachePolicy):
        raise ValueError("cache_policy must be a CachePolicy")
    if cache_policy is not None and cache_dir is None:
        raise ValueError("cache_policy requires cache_dir")
    policy = cache_policy if cache_policy is not None else CachePolicy()
    cache = ResponseCache(cache_dir) if cache_dir is not None else None
    headers = _PROMIEDOS_HEADERS if source == "promiedos" else None

    def fetch(address):
        if source in ("besoccer", "transfermarkt"):
            return {"html": get_text(address, proxies=proxies,
                                     impersonate="safari17_0" if source == "besoccer" else "chrome")}
        return get_api_json(address, proxies=proxies, headers=headers)

    reader = ResponseReader(fetch,
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
    page: int | None = None,
) -> DiscoveryResult:
    """List a provider's competitions with explicit listing/search/category/date scope.

    ESPN uses its soccer dropdown. 365Scores and Transfermarkt require query.
    Transfermarkt's page selects one search page. Sofascore requires a
    football category_id, such as 1 for England. Promiedos requires an ISO source
    date. query is sent to search on 365Scores and Transfermarkt and filters names
    locally on other listings. Other adapters raise DiscoveryNotSupported before I/O.
    """
    if not isinstance(source, str):
        raise ValueError("source must be a provider name")
    capability = get_discovery_capabilities(source)
    if capability.competitions is None:
        raise DiscoveryNotSupported(f"{source} competition discovery is not implemented; choose its ID manually")
    if page is not None and (source != "transfermarkt" or type(page) is not int or page < 1):
        raise ValueError("page must be a positive integer and is supported only for Transfermarkt search")
    if query is not None and (not isinstance(query, str) or not query.strip()):
        raise ValueError("query must be nonempty text")
    if category_id is not None and source != "sofascore":
        raise ValueError("category_id is supported only for Sofascore discovery")
    if date is not None and source != "promiedos":
        raise ValueError("date is supported only for Promiedos discovery")
    category = None
    if source in ("scores365", "transfermarkt"):
        if query is None:
            raise ValueError(f"{source} competition discovery requires query")
        if source == "transfermarkt":
            page = page if page is not None else 1
            url = TransfermarktEndpoints().search(query, page=page)
        else:
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
    rows, fetched, cached = _read(source, url, lambda data: _competitions(data, source, page), cache_dir, cache_policy, refresh, proxies)
    if query is not None and source not in ("scores365", "transfermarkt"):
        rows = tuple(row for row in rows if query.casefold() in row.name.casefold())
    return DiscoveryResult(source, capability.competitions, fetched, cached, competitions=rows,
                           query=query, category_id=category, date=date, notes=capability.notes, page=page,
                           source_url=url)


def list_seasons(
    source: str, competition_id: int | str, *, cache_dir: str | PathLike | None = None,
    cache_policy: CachePolicy | None = None, refresh: bool = False, proxies: dict | None = None,
    competition_url: str | None = None,
) -> DiscoveryResult:
    """List native seasons without guessing years from names or filling absent history.

    ESPN uses a slug and native year index. Sofascore IDs select season_id;
    Goaloo strings select source_season. 365Scores returns only seasons included
    in its competition response, which may omit history. Each call fetches one
    response; paginated ESPN results raise instead of returning a partial index.
    BeSoccer preserves its explicit standings year selector. Transfermarkt needs
    competition_url from a competition result and returns native season options;
    its entity datasets still use current profiles and unfiltered histories.
    """
    if not isinstance(source, str):
        raise ValueError("source must be a provider name")
    capability = get_discovery_capabilities(source)
    if capability.seasons is None:
        raise DiscoveryNotSupported(f"{source} season discovery is not implemented; choose its selection manually")
    if competition_url is not None and source != "transfermarkt":
        raise ValueError("competition_url is supported only for Transfermarkt discovery")
    if source == "espn":
        if not isinstance(competition_id, str) or not competition_id.strip():
            raise ValueError("ESPN competition_id must be its league slug")
        competition = competition_id
        url = ESPNEndpoints().seasons(competition)
    elif source in ("besoccer", "transfermarkt"):
        pattern = r"[A-Za-z0-9_-]+" if source == "besoccer" else r"[A-Za-z0-9]+"
        if not isinstance(competition_id, str) or re.fullmatch(pattern, competition_id) is None:
            raise ValueError(f"{source} competition_id must be its native slug or code")
        competition = competition_id
        url = (BeSoccerEndpoints().standings(competition) if source == "besoccer"
               else TransfermarktEndpoints().competition_seasons(competition, competition_url))
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
                           competition_id=competition, notes=capability.notes, source_url=url)
