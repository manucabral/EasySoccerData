"""
This module contains the client class for interacting with Goaloo.
"""

from __future__ import annotations

from .service import GoalooService
from .types import League, Match, Standing


class GoalooClient:
    """
    Client for interacting with Goaloo.

    This class provides methods to access and retrieve football data
    (leagues, schedules and standings) from Goaloo.
    """

    def __init__(self, proxies: dict = None) -> None:
        """
        Initializes the Goaloo client.

        Args:
            proxies: Optional proxy dict.
        """
        self.__service = GoalooService(proxies=proxies)

    def get_league(self, league_id: int, season: str = None) -> League:
        """
        Get a competition's metadata and team list.

        Args:
            league_id (int): The Goaloo competition id (e.g. 36 for Premier League).
            season (str): The season (e.g. "2026-2027"). Defaults to current.

        Returns:
            League: The competition metadata.
        """
        return self.__service.get_league(league_id, season)

    def get_matches(self, league_id: int, season: str = None) -> list[Match]:
        """
        Get all matches of a competition for a season.

        Args:
            league_id (int): The Goaloo competition id.
            season (str): The season (e.g. "2026-2027"). Defaults to current.

        Returns:
            list[Match]: The matches of the competition.
        """
        return self.__service.get_matches(league_id, season)

    def get_standings(self, league_id: int, season: str = None) -> list[Standing]:
        """
        Get the standings of a competition for a season.

        Args:
            league_id (int): The Goaloo competition id.
            season (str): The season (e.g. "2026-2027"). Defaults to current.

        Returns:
            list[Standing]: The standings of the competition.
        """
        return self.__service.get_standings(league_id, season)

    def get_seasons(self, league_id: int) -> list[str]:
        """
        Get the available seasons for a competition.

        Args:
            league_id (int): The Goaloo competition id.

        Returns:
            list[str]: The available seasons.
        """
        return self.__service.get_seasons(league_id)
