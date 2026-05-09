"""
Promiedos service module.
"""

from __future__ import annotations

from ..utils import get_json, is_available_date
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


class PromiedosService:
    """
    A class to represent the Promiedos service.
    """

    def __init__(self):
        """
        Initializes the Promiedos service.
        """
        self.endpoints = PromiedosEndpoints()

    def get_events(self, date: str = "today") -> list[Event]:
        """
        Get the events for the given date.

        Args:
            date (str): The date to get the events. Defaults to "today".

        Returns:
            list[Event]: The events for the given date.
        """
        available_dates = ["today", "yesterday", "tomorrow"]
        if date not in available_dates:
            try:
                is_available_date(date, r"\d{4}-\d{2}-\d{2}")
            except Exception as exc:
                raise InvalidDate(
                    "Invalid date format. Use DD-MM-YYYY or today, yesterday, or tomorrow."
                ) from exc
        try:
            url = self.endpoints.events_endpoint.format(date=date)
            data = get_json(None, url)["leagues"]
            return parse_events(date, data)
        except Exception as exc:
            raise exc

    def get_match(self, match_id: int) -> Match:
        """
        Get the match for the given slug and match ID.

        Args:
            match_id (int): The ID of the match.

        Returns:
            Match: The match data.
        """
        try:
            url = self.endpoints.match_endpoint.format(id=match_id)
            data = get_json(None, url)["game"]
            match = parse_match(data)
            match.league = parse_league(data["league"])
            if data.get("statistics"):
                match.stats = parse_match_stats(data["statistics"])
            match.players = parse_players(data.get("players", []))
            return match
        except Exception as exc:
            raise exc

    def get_tournament(self, tournament_id: str) -> Tournament:
        """
        Get the matches for the given tournament ID.

        Args:
            tournament_id (str): The tournament ID. E.g. "dss".

        Returns:
            Tournament: The tournament data.
        """
        try:
            url = self.endpoints.tournament_endpoint.format(id=tournament_id)
            data = get_json(None, url)
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
            data = get_json(None, url)["games"]
            return [parse_match(match) for match in data]
        except Exception as exc:
            raise exc
