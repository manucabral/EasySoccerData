"""
365Scores service module.
"""

from __future__ import annotations

from datetime import datetime

from ..logger import get_logger
from ..utils import TTLCache, get_api_json
from .endpoints import Scores365Endpoints
from .types import (
    Game,
    GameStatItem,
    SearchResult,
    StandingTable,
    parse_game,
    parse_game_stats,
    parse_games,
    parse_search,
    parse_standings,
)

_logger = get_logger("scores365.service")


def _normalize_date(date: str | None) -> str | None:
    """
    Convert ``"today"`` or ``"YYYY-MM-DD"`` into ``"DD/MM/YYYY"`` for 365Scores.
    """
    if not date or date.lower() == "today":
        return None
    if "-" in date:
        dt = datetime.strptime(date, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    datetime.strptime(date, "%d/%m/%Y")
    return date


class Scores365Service:
    """
    Service layer for fetching and parsing 365Scores API data.
    """

    def __init__(
        self,
        proxies: dict | None = None,
        lang_id: int = 14,
        timezone_name: str = "America/Argentina/Buenos_Aires",
        country_id: int = 31,
    ) -> None:
        self.proxies = proxies
        self.endpoints = Scores365Endpoints(
            lang_id=lang_id,
            timezone_name=timezone_name,
            country_id=country_id,
        )
        self._cache = TTLCache(ttl=30.0)

    def _fetch(self, url: str) -> dict:
        cached = self._cache.get(url)
        if cached is not None:
            return cached
        data = get_api_json(url, proxies=self.proxies)
        self._cache.set(url, data)
        return data

    def get_games(
        self,
        date: str = "today",
        competition_id: int | None = None,
    ) -> list[Game]:
        """
        Get matches for a date (``"today"``, ``"YYYY-MM-DD"`` or ``"DD/MM/YYYY"``)
        and optional competition ID.
        """
        formatted = _normalize_date(date)
        url = self.endpoints.games_allscores(
            start_date=formatted,
            end_date=formatted,
            competition_id=competition_id,
        )
        data = self._fetch(url)
        return parse_games(data)

    def get_live_games(self, competition_id: int | None = None) -> list[Game]:
        """
        Get currently active (live) games.
        """
        games = self.get_games(date="today", competition_id=competition_id)
        return [g for g in games if g.status_group == 3]

    def get_game(self, game_id: int) -> Game:
        """
        Get full match details (including events and lineups) by game ID.
        """
        url = self.endpoints.game_detail(game_id)
        data = self._fetch(url)
        return parse_game(data.get("game") or {})

    def get_game_stats(self, game_id: int) -> list[GameStatItem]:
        """
        Get match team statistics by game ID.
        """
        url = self.endpoints.game_stats(game_id)
        data = self._fetch(url)
        return parse_game_stats(data)

    def get_standings(self, competition_id: int) -> list[StandingTable]:
        """
        Get standings tables for a competition ID.
        """
        url = self.endpoints.standings(competition_id)
        data = self._fetch(url)
        return parse_standings(data)

    def search(self, query: str) -> SearchResult:
        """
        Search for teams, competitions and athletes.
        """
        url = self.endpoints.search(query)
        data = self._fetch(url)
        return parse_search(data)
