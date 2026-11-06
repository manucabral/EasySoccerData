"""
BeSoccer service module.
"""

from __future__ import annotations

from ..utils import TTLCache, get_text, is_available_date
from .endpoints import BeSoccerEndpoints
from .types import (
    BeSoccerMatch,
    BeSoccerStandingRow,
    parse_livescore_html,
    parse_standings_html,
)


class BeSoccerService:
    """
    Service layer for fetching and parsing BeSoccer pages.
    """

    def __init__(self, proxies: dict | None = None) -> None:
        self.proxies = proxies
        self.endpoints = BeSoccerEndpoints()
        self._cache = TTLCache(ttl=30.0)

    def _fetch(self, url: str) -> str:
        cached = self._cache.get(url)
        if cached is not None:
            return cached
        html_text = get_text(url, proxies=self.proxies, impersonate="safari17_0")
        if "<title>Client Challenge</title>" in html_text[:1500]:
            html_text = get_text(url, proxies=self.proxies, impersonate="chrome")
        self._cache.set(url, html_text)
        return html_text

    def get_matches(self, date: str = "today") -> list[BeSoccerMatch]:
        """
        Get matches for a date (``"today"`` or ``"YYYY-MM-DD"``).
        """
        if date and date.lower() != "today":
            is_available_date(date, r"\d{4}-\d{2}-\d{2}")
        url = self.endpoints.livescore(date)
        return parse_livescore_html(self._fetch(url))

    def get_standings(
        self, competition_slug: str = "torneo_final", season: int | str | None = None
    ) -> list[BeSoccerStandingRow]:
        """
        Get standings rows for a competition slug (e.g. ``"torneo_final"``,
        ``"primera_division"``, ``"premier_league"``).
        """
        url = self.endpoints.standings(competition_slug, season=season)
        return parse_standings_html(self._fetch(url))
