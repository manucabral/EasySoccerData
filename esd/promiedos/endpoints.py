"""
Promiedos event, match and tournament URLs.
"""

from datetime import datetime


class PromiedosEndpoints:
    """
    URL builders for Promiedos requests.
    """

    def __init__(self, base_url: str = "https://api.promiedos.com.ar/") -> None:
        self.base_url = base_url

    @property
    def events_endpoint(self) -> str:
        """
        Get the events endpoint.
        """
        return self.base_url + "games/{date}"

    def events_url(self, date: str) -> str:
        """Accept an ISO date or relative day and format the source's date path."""
        if date not in ("today", "yesterday", "tomorrow"):
            date = datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y")
        return self.events_endpoint.format(date=date)

    @property
    def match_endpoint(self) -> str:
        """
        Get the match endpoint.
        """
        return self.base_url + "gamecenter/{id}"

    @property
    def tournament_endpoint(self) -> str:
        """
        Get the tournament endpoint.
        """
        return self.base_url + "league/tables_and_fixtures/{id}"

    @property
    def tournament_matchs_endpoint(self) -> str:
        """
        Get the tournament matches endpoint.
        """
        return self.base_url + "league/games/{id}/{stage_id}"
