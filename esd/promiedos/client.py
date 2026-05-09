"""
This module contains the client class for interacting with the Promiedos.
"""

from __future__ import annotations

from .exceptions import NotMatchIdProvided
from .service import PromiedosService
from .types import Event, Match, Tournament


class PromiedosClient:
    """
    Client for interacting with the Promiedos website.
    This class provides methods to access and retrieve data from Promiedos.
    """

    def __init__(self) -> None:
        """
        Initializes the Promiedos client.
        """
        self.__service = PromiedosService()

    def get_events(self, date: str = "today") -> list[Event]:
        """
        Get the events for the given date.

        Args:
            date (str): The date to get the events. Defaults to "today".

        Returns:
            list[Event]: The events for the given date.
        """
        return self.__service.get_events(date)

    def get_match(self, match_id: str = None, match: Match = None) -> Match:
        """
        Get the match for the given slug and match ID.

        Args:
            match_id (str): The match ID. E.g. "ediecji".
            Match (Match): The match object.

        Returns:
            Match: The match for the given slug and match ID.
        """
        if not match_id and not match:
            raise NotMatchIdProvided(
                "No match ID provided OR no match object provided."
            )
        if match:
            return self.__service.get_match(match.id)
        return self.__service.get_match(match_id)

    def get_tournament(self, tournament_id: str) -> Tournament:
        """
        Get the matches for the given tournament ID.

        Args:
            tournament_id (str): The tournament ID. E.g. "hc".

        Returns:
            Tournament: The tournament for the given tournament ID.
        """
        return self.__service.get_tournament(tournament_id)

    def get_tournament_matchs(
        self, tournament_id: str, stage_id: str = None
    ) -> list[Match]:
        """
        Get the matches for the given tournament ID using the stage ID.

        Args:
            tournament_id (str): The tournament ID. E.g. "hc".
            stage_id (str): The stage ID.
        Returns:
            list[Match]: The matches for the given tournament ID.
        """
        return self.__service.get_tournament_matchs(tournament_id, stage_id)
