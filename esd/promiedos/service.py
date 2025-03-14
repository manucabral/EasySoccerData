"""
Promiedos service module.
"""

from __future__ import annotations
from ..utils import get_json, is_available_date
from .endpoints import PromiedosEndpoints
from .exceptions import InvalidDate
from .types import Event, parse_events, parse_match, parse_league, parse_players


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
            data = get_json(url)["leagues"]
            return parse_events(date, data)
        except Exception as exc:
            raise exc

    def get_match(self, match_id: int) -> dict:
        """
        Get the match for the given slug and match ID.

        Args:
            match_id (int): The ID of the match.

        Returns:
            dict: The match for the given slug and match ID.
        """
        try:
            url = self.endpoints.match_endpoint.format(id=match_id)
            data = get_json(url)["game"]
            match = parse_match(data)
            match.league = parse_league(data["league"])
            match.players = parse_players(data.get("players", []))
            return match
        except Exception as exc:
            raise exc
