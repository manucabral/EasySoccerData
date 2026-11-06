"""
ESPN service module.
"""

from __future__ import annotations

from datetime import datetime

from ..utils import TTLCache, get_api_json
from .endpoints import ESPNEndpoints
from .types import (
    ESPNMatch,
    ESPNMatchSummary,
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

    def __init__(self, proxies: dict | None = None) -> None:
        self.proxies = proxies
        self.endpoints = ESPNEndpoints()
        self._cache = TTLCache(ttl=30.0)

    def _fetch(self, url: str) -> dict:
        cached = self._cache.get(url)
        if cached is not None:
            return cached
        data = get_api_json(url, proxies=self.proxies)
        self._cache.set(url, data)
        return data

    def get_scoreboard(
        self, league: str = "arg.1", date: str = "today"
    ) -> list[ESPNMatch]:
        """
        Get matches from the scoreboard for a league and date.
        """
        dates = _normalize_espn_date(date)
        url = self.endpoints.scoreboard(league=league, dates=dates)
        return parse_scoreboard(self._fetch(url))

    def get_match_summary(
        self, event_id: int | str, league: str = "all"
    ) -> ESPNMatchSummary:
        """
        Get detailed match summary (stats, rosters, key events, commentary).
        """
        url = self.endpoints.summary(event_id=event_id, league=league)
        return parse_summary(self._fetch(url))

    def get_standings(
        self, league: str = "arg.1", season: int | str | None = None
    ) -> list[ESPNStandingTable]:
        """
        Get league standings tables.
        """
        url = self.endpoints.standings(league=league, season=season)
        return parse_standings(self._fetch(url))

    def get_teams(self, league: str = "arg.1") -> list[ESPNTeam]:
        """
        Get all teams registered in a league.
        """
        url = self.endpoints.teams(league=league)
        return parse_teams(self._fetch(url))
