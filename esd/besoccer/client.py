"""
Client for interacting with BeSoccer.
"""

from __future__ import annotations

from .service import BeSoccerService
from .types import BeSoccerMatch, BeSoccerStandingRow


class BeSoccerClient:
    """
    Client for fetching live matches, fixtures and competition standings
    from BeSoccer.
    """

    def __init__(self, proxies: dict | None = None) -> None:
        """
        Initialize the BeSoccer client.

        Args:
            proxies: Optional proxy dictionary.
        """
        self.__service = BeSoccerService(proxies=proxies)

    def get_matches(self, date: str = "today") -> list[BeSoccerMatch]:
        """
        Get matches for the given date (``"today"`` or ``"YYYY-MM-DD"``).
        """
        return self.__service.get_matches(date=date)

    def get_standings(
        self, competition_slug: str = "torneo_final", season: int | str | None = None
    ) -> list[BeSoccerStandingRow]:
        """
        Get standings rows for a competition slug (e.g. ``"torneo_final"``)
        and optional season year.
        """
        return self.__service.get_standings(
            competition_slug=competition_slug, season=season
        )
