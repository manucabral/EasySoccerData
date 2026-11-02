"""
This module contains the endpoints to interact with the Goaloo data API.

Goaloo serves its league data as static JSON under ``/jsData`` on the
``football.goaloo.com`` host. The same data powers the public schedule,
standings and odds pages, so no anti-bot layer is involved.
"""


class GoalooEndpoints:
    """
    A class to represent the endpoints to interact with the Goaloo API.
    """

    def __init__(self, base_url: str = "https://football.goaloo.com") -> None:
        self.base_url = base_url

    def data_endpoint(self, league_id: int, season: str, lang: str = "en") -> str:
        """
        Returns the URL of the league JSON payload (schedule + standings).

        Args:
            league_id (int): The Goaloo competition id (e.g. 36 for Premier League).
            season (str): The season string (e.g. "2026-2027").
            lang (str): Language suffix (default "en").

        Returns:
            str: The JSON data URL.
        """
        return f"{self.base_url}/jsData/matchResult/json/{season}/s{league_id}_{lang}.json"

    def seasons_endpoint(self, league_id: int) -> str:
        """
        Returns the URL of the available seasons for a competition.

        Args:
            league_id (int): The Goaloo competition id.

        Returns:
            str: The seasons JSON URL.
        """
        return f"{self.base_url}/jsData/leagueSeason/sea{league_id}.json"

    def h2h_endpoint(self, match_id: int) -> str:
        """
        Returns the URL of the head-to-head page for a match.

        The path segment before ``h2h-{id}`` is a placeholder: Goaloo resolves
        the page by match id only.

        Args:
            match_id (int): The Goaloo match id.

        Returns:
            str: The H2H page URL.
        """
        return f"https://www.goaloo.com/football/match/h2h-{match_id}"
