"""
This module contains the client class for interacting with the Promiedos API.
"""

from __future__ import annotations
from .exceptions import NotMatchIdProvided
from .service import PromiedosService
from .types import Event, Match


class PromiedosClient:
    """
    A class to represent the client for interacting with the Promiedos API.
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

    def get_match(self, match_id: int = None, match: Match = None) -> Match:
        """
        Get the match for the given slug and match ID.

        Args:
            match_id (int): The ID of the match.
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
