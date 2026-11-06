"""
Endpoints for Understat.
"""

from __future__ import annotations

from urllib.parse import quote


class UnderstatEndpoints:
    """
    Endpoints for the Understat AJAX API.
    """

    def __init__(self, base_url: str = "https://understat.com") -> None:
        self.base_url = base_url.rstrip("/")

    def league_data(self, league: str, season: int | str) -> str:
        """
        Return the league data endpoint (e.g. ``EPL``, ``La_liga``, ``Serie_A``,
        ``Bundesliga``, ``Ligue_1``).
        """
        return f"{self.base_url}/getLeagueData/{quote(str(league))}/{season}"

    def match_data(self, match_id: int | str) -> str:
        """
        Return the match data endpoint (shots and roster).
        """
        return f"{self.base_url}/getMatchData/{match_id}"

    def team_data(self, team: str, season: int | str) -> str:
        """
        Return the team data endpoint.
        """
        return f"{self.base_url}/getTeamData/{quote(str(team))}/{season}"

    def player_data(self, player_id: int | str) -> str:
        """
        Return the player data endpoint.
        """
        return f"{self.base_url}/getPlayerData/{player_id}"
