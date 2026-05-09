"""
This module contains the client class for interacting with the FBref website.
"""

from __future__ import annotations

from .service import FBrefService
from .types import Match, MatchDetails


class FBrefClient:
    """
    A class to represent the client for interacting with the FBref website.
    """

    def __init__(self, language: str = "en", proxies: dict = None) -> None:
        """
        Initializes the Sofascore client.
        """
        self.__service = FBrefService(language=language, proxies=proxies)

    def get_matchs(self, date: str = None) -> list[Match]:
        """
        Get the scheduled matchs.

        Args:
            date (str): The date of the matchs in the format "YYYY-MM-DD".

        Returns:
            list[Match]: The scheduled matchs.
        """
        return self.__service.get_matchs(date)

    def get_match_details(self, match_id: str) -> MatchDetails:
        """
        Get the match report.

        Args:
            match_id (str): The match id.

        Returns:
            MatchDetails: The match details.
        """
        return self.__service.get_match_details(match_id)
