"""
ESPN service module.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .._response_reader import ResponseReader
from ..cache import CachePolicy, ResponseCache, ResponseInfo
from ..exceptions import SourceError
from ..utils import get_api_json
from .endpoints import ESPNEndpoints
from .types import (
    ESPNMatch,
    ESPNMatchSummary,
    ESPNSeasonCalendar,
    ESPNStandingTable,
    ESPNTeam,
    parse_scoreboard,
    parse_standings,
    parse_summary,
    parse_teams,
)


def _normalize_espn_date(date: str | None) -> str | None:
    """
    Convert ``"today"``, ``"YYYY-MM-DD"`` or ``"YYYYMMDD"`` to ``"YYYYMMDD"``.
    """
    if not date or date.lower() == "today":
        return None
    if "-" in date:
        dt = datetime.strptime(date, "%Y-%m-%d")
        return dt.strftime("%Y%m%d")
    datetime.strptime(date, "%Y%m%d")
    return date


class ESPNService:
    """
    Service layer for fetching and parsing ESPN Soccer API data.
    """

    def __init__(
        self, proxies: dict | None = None, *, response_cache: ResponseCache | None = None,
        cache_policy: CachePolicy | None = None, refresh: bool = False, request_delay: float = 0.0,
    ) -> None:
        self.proxies = proxies
        self.endpoints = ESPNEndpoints()
        self.response_cache = response_cache
        self.cache_policy = cache_policy or CachePolicy()
        self.refresh = refresh
        self.request_delay = request_delay
        self._reader = ResponseReader(
            lambda url: get_api_json(url, proxies=self.proxies), cache=response_cache,
            refresh=refresh, request_delay=request_delay,
        )

    @property
    def last_response(self) -> ResponseInfo | None:
        return self._reader.last_response

    def _fetch(self, url: str, *, ttl=30.0, validate=None) -> dict:
        return self._reader.read(url, ttl=ttl, validate=validate)

    def get_scoreboard(
        self, league: str = "arg.1", date: str = "today", *, expected_season: int | None = None
    ) -> list[ESPNMatch]:
        """
        Get matches from the scoreboard for a league and date.
        """
        dates = _normalize_espn_date(date)
        limit = 1000 if expected_season is not None else None
        url = self.endpoints.scoreboard(league=league, dates=dates, limit=limit)

        def parse(data):
            if expected_season is not None:
                self._validate_season(data, league, expected_season)
                if not isinstance(data.get("events"), list):
                    raise SourceError("ESPN scoreboard is missing its events list")
                if len(data["events"]) >= limit:
                    raise SourceError("ESPN scoreboard reached its limit and may be truncated")
                for event in data["events"]:
                    if not event.get("id"):
                        raise SourceError("ESPN scoreboard includes an event without an ID")
                    event_season = (event.get("season") or {}).get("year")
                    if event_season is not None and event_season != expected_season:
                        raise SourceError("ESPN scoreboard includes an event from another season")
                    if event.get("date"):
                        kickoff = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
                        if kickoff.tzinfo is None or kickoff.utcoffset() is None:
                            raise SourceError("ESPN scoreboard includes a kickoff without a timezone")
            return parse_scoreboard(data)

        def ttl(data):
            day = dates or datetime.now(timezone.utc).strftime("%Y%m%d")
            return self.cache_policy.scoreboard_ttl(day, data)

        return parse(self._fetch(url, ttl=ttl, validate=parse))

    @staticmethod
    def _validate_season(data: dict, league: str, season: int) -> dict:
        leagues = data.get("leagues") if isinstance(data, dict) else None
        if not isinstance(leagues, list):
            raise SourceError("ESPN response is missing league metadata")
        selected = next((item for item in leagues
                         if isinstance(item, dict) and item.get("slug") == league), None)
        if selected is None or (selected.get("season") or {}).get("year") != season:
            raise SourceError(f"ESPN did not return season {season} for {league}")
        return selected

    def get_season_calendar(
        self, league: str, season: int, *, anchor_date: str | None = None
    ) -> ESPNSeasonCalendar:
        """Discover ESPN's calendar, rejecting missing or mismatched seasons.

        July 1 is the default lookup date. Supply another date inside the desired
        season if the source selects a different season for this league. Daily
        calendars supply match dates. Stage calendars are expanded to inclusive
        date ranges and can include days without matches.
        """
        date = _normalize_espn_date(anchor_date or f"{season}-07-01")
        url = self.endpoints.scoreboard(league, date, limit=1000)
        def parse(data):
            return self._parse_calendar(data, league, season)

        return parse(self._fetch(url, ttl=self.cache_policy.calendar_ttl, validate=parse))

    def _parse_calendar(self, data, league, season):
        selected = self._validate_season(data, league, season)
        calendar = selected.get("calendar")
        kind = selected.get("calendarType")
        if kind not in ("day", "list") or not isinstance(calendar, list) or not calendar:
            raise SourceError("ESPN did not return a supported nonempty calendar")
        try:
            if kind == "day":
                if any(not isinstance(value, str) for value in calendar):
                    raise ValueError("Calendar dates must be strings")
                date_set = {datetime.strptime(value[:10], "%Y-%m-%d").date() for value in calendar}
            else:
                date_set = set()
                for group in calendar:
                    for entry in group["entries"]:
                        start = datetime.strptime(entry["startDate"][:10], "%Y-%m-%d").date()
                        end = datetime.strptime(entry["endDate"][:10], "%Y-%m-%d").date()
                        length = (end - start).days
                        if not 0 <= length <= 730:
                            raise ValueError("Invalid calendar range")
                        date_set.update(start + timedelta(days=offset) for offset in range(length + 1))
                if not date_set:
                    raise ValueError("Calendar has no stage dates")
            dates = tuple(date.isoformat() for date in sorted(date_set))
        except (KeyError, TypeError, ValueError) as exc:
            raise SourceError("ESPN returned an invalid calendar date") from exc
        meta = selected["season"]
        return ESPNSeasonCalendar(
            league=league, season=season, dates=dates, name=meta.get("displayName"),
            start_date=meta.get("startDate"), end_date=meta.get("endDate"), calendar_type=kind,
        )

    def get_match_summary(
        self, event_id: int | str, league: str = "all"
    ) -> ESPNMatchSummary:
        """
        Get detailed match summary (stats, rosters, key events, commentary).
        """
        url = self.endpoints.summary(event_id=event_id, league=league)
        return parse_summary(self._fetch(url))

    def get_standings(
        self, league: str = "arg.1", season: int | str | None = None, *, strict: bool = False
    ) -> list[ESPNStandingTable]:
        """
        Get league standings tables.
        """
        url = self.endpoints.standings(league=league, season=season)

        def parse(data):
            if strict:
                if not isinstance(data, dict) or not (
                    isinstance(data.get("children"), list) or isinstance(data.get("standings"), dict)
                ):
                    raise SourceError("ESPN response is missing standings")
                if (data.get("season") or {}).get("year") != int(season):
                    raise SourceError(f"ESPN did not return standings for season {season}")
            return parse_standings(data)

        return parse(self._fetch(url, ttl=self.cache_policy.standings_ttl, validate=parse))

    def get_teams(self, league: str = "arg.1") -> list[ESPNTeam]:
        """
        Get all teams registered in a league.
        """
        url = self.endpoints.teams(league=league)
        return parse_teams(self._fetch(url))
