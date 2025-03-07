"""
Sofascore service module
"""

from ..utils import get_json, get_today
from .endpoints import SofascoreEndpoints
from .types import Event, parse_events, parse_team_ex


class SofascoreService:
    """
    A class to represent the SofaScore service.
    """

    def __init__(self):
        """
        Initializes the SofaScore service.
        """
        self.endpoints = SofascoreEndpoints()

    def get_events(self, date: str = None) -> list[Event]:
        """
        Get the scheduled events.

        Args:
            date (str): The date of the events in the format "YYYY-MM-DD".

        Returns:
            dict: The scheduled events.
        """
        if not date:
            date = get_today()
        try:
            url = self.endpoints.events_endpoint.format(date=date)
            return parse_events(get_json(url)["events"])
        except Exception as exc:
            raise exc

    def get_live_events(self) -> list[Event]:
        """
        Get the live events.

        Returns:
            list[Event]: The live events.
        """
        try:
            url = self.endpoints.live_events_endpoint
            return parse_events(get_json(url)["events"])
        except Exception as exc:
            raise exc

    def get_team(self, team_id: int) -> dict:
        """
        Get the team information.

        Args:
            team_id (int): The team id.

        Returns:
            dict: The team information.
        """
        try:
            url = f"{self.endpoints.base_url}/team/{team_id}"
            data = get_json(url)["team"]
            return parse_team_ex(data)
        except Exception as exc:
            raise exc
