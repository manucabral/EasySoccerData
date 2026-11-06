"""
Client for interacting with 365Scores.
"""

from __future__ import annotations

from .service import Scores365Service
from .types import Game, GameStatItem, SearchResult, StandingTable


class Scores365Client:
    """
    Client for interacting with the 365Scores API.
    """

    def __init__(
        self,
        proxies: dict | None = None,
        lang_id: int = 14,
        timezone_name: str = "America/Argentina/Buenos_Aires",
        country_id: int = 31,
    ) -> None:
        """
        Initialize the 365Scores client.

        Args:
            proxies: Optional proxy dictionary.
            lang_id: Language ID (default 14 for Spanish, 1 for English).
            timezone_name: IANA timezone name.
            country_id: Country ID (default 31).
        """
        self.__service = Scores365Service(
            proxies=proxies,
            lang_id=lang_id,
            timezone_name=timezone_name,
            country_id=country_id,
        )

    def get_games(
        self,
        date: str = "today",
        competition_id: int | None = None,
    ) -> list[Game]:
        """
        Get games for the given date (``"today"``, ``"YYYY-MM-DD"`` or ``"DD/MM/YYYY"``).
        """
        return self.__service.get_games(date=date, competition_id=competition_id)

    def get_live_games(self, competition_id: int | None = None) -> list[Game]:
        """
        Get currently live games.
        """
        return self.__service.get_live_games(competition_id=competition_id)

    def get_game(self, game_id: int) -> Game:
        """
        Get detailed information (events, lineups, player stats) for a match.
        """
        return self.__service.get_game(game_id)

    def get_game_stats(self, game_id: int) -> list[GameStatItem]:
        """
        Get team match statistics for a game.
        """
        return self.__service.get_game_stats(game_id)

    def get_standings(self, competition_id: int) -> list[StandingTable]:
        """
        Get standings tables for a competition (e.g. ``72`` for Liga Profesional).
        """
        return self.__service.get_standings(competition_id)

    def search(self, query: str) -> SearchResult:
        """
        Search for teams, competitions and players.
        """
        return self.__service.search(query)
