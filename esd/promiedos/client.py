"""
Promiedos client for matches and tournaments.
"""

from __future__ import annotations

from ..logger import get_logger
from .exceptions import NotMatchIdProvided
from .service import PromiedosService
from .types import Event, Match, Tournament

_logger = get_logger("promiedos.client")


class PromiedosClient:
    """
    Fetch daily events, match details and tournament stages from Promiedos.
    """

    def __init__(self, proxies: dict = None) -> None:
        """
        Initializes the Promiedos client.

        Args:
            proxies: Optional proxy dict.
        """
        self.__service = PromiedosService(proxies=proxies)

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
        """Get match details by source ID or an existing Match.

        Args:
            match_id: Promiedos match ID, for example "ediecji".
            match: A Match whose ID is used when supplied. Takes precedence over match_id.

        Raises:
            NotMatchIdProvided: Neither argument was supplied.
        """
        if not match_id and not match:
            raise NotMatchIdProvided(
                "No match ID provided OR no match object provided."
            )
        if match:
            return self.__service.get_match(match.id)
        return self.__service.get_match(match_id)

    def get_tournament(self, tournament_id: str) -> Tournament:
        """Get league metadata and available stages for a tournament ID."""
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
