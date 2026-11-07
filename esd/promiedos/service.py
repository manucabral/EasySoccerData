"""
Promiedos service module.
"""

from __future__ import annotations

from ..logger import get_logger
from ..utils import TTLCache, get_api_json, is_available_date
from .endpoints import PromiedosEndpoints
from .exceptions import InvalidDate
from .types import (
    Event,
    Match,
    Tournament,
    parse_events,
    parse_league,
    parse_match,
    parse_match_stats,
    parse_players,
    parse_tournament,
)

_logger = get_logger("promiedos.service")

_PROMIEDOS_HEADERS = {"X-VER": "1.11.7.5"}

_CACHE_TTL = 30.0


class PromiedosService:
    """
    Fetch and parse Promiedos responses.
    """

    def __init__(self, proxies: dict = None):
        """
        Initializes the Promiedos service.
        """
        self.proxies = proxies
        self.endpoints = PromiedosEndpoints()
        self._cache = TTLCache(ttl=_CACHE_TTL, maxsize=256)

    def _get_json(self, url: str) -> dict:
        """
        Fetch JSON from a Promiedos endpoint.
        """
        cached = self._cache.get(url)
        if cached is not None:
            return cached
        data = get_api_json(url, headers=_PROMIEDOS_HEADERS, proxies=self.proxies)
        if data:
            self._cache.set(url, data)
        return data

    def get_events(self, date: str = "today") -> list[Event]:
        """
        Get the events for the given date.
        """
        _logger.debug("get_events(date=%s)", date)
        available_dates = ["today", "yesterday", "tomorrow"]
        if date not in available_dates:
            try:
                is_available_date(date, r"\d{4}-\d{2}-\d{2}")
            except Exception as exc:
                raise InvalidDate(
                    "Invalid date format. Use YYYY-MM-DD or today, yesterday, or tomorrow."
                ) from exc
        try:
            url = self.endpoints.events_url(date)
            data = self._get_json(url).get("leagues", [])
            return parse_events(date, data)
        except Exception as exc:
            raise exc

    def get_match(self, match_id: int) -> Match:
        """Get match details for a Promiedos match ID."""
        _logger.debug("get_match(match_id=%s)", match_id)
        try:
            url = self.endpoints.match_endpoint.format(id=match_id)
            data = self._get_json(url)["game"]
            match = parse_match(data)
            match.league = parse_league(data["league"])
            if data.get("statistics"):
                match.stats = parse_match_stats(data["statistics"])
            match.players = parse_players(data.get("players", []))
            return match
        except Exception as exc:
            raise exc

    def get_tournament(self, tournament_id: str) -> Tournament:
        """Get league metadata and available stages for a tournament ID."""
        try:
            url = self.endpoints.tournament_endpoint.format(id=tournament_id)
            data = self._get_json(url)
            return parse_tournament(data)
        except Exception as exc:
            raise exc

    def get_tournament_matchs(
        self, tournament_id: str, stage_id: str = None
    ) -> list[Match]:
        """
        Get the matches for the given tournament ID.

        Args:
            tournament_id (str): The tournament ID. E.g. "dss".
            stage_id (str): The stage ID.

        Returns:
            list[Match]: The matches for the given tournament ID.
        """
        try:
            url = self.endpoints.tournament_matchs_endpoint.format(
                id=tournament_id, stage_id=stage_id
            )
            data = self._get_json(url).get("games", [])
            return [parse_match(match) for match in data]
        except Exception as exc:
            raise exc
