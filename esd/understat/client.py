"""
Client for interacting with Understat.
"""

from __future__ import annotations

from .service import UnderstatService
from .types import (
    UnderstatMatch,
    UnderstatPlayerStat,
    UnderstatShot,
    UnderstatTeam,
)


class UnderstatClient:
    """
    Client for fetching Expected Goals (xG), Expected Points (xPTS) and shotmaps
    from Understat.
    """

    def __init__(self, proxies: dict | None = None) -> None:
        """
        Initialize the Understat client.

        Args:
            proxies: Optional proxy dictionary.
        """
        self.__service = UnderstatService(proxies=proxies)

    def get_league_matches(
        self, league: str = "EPL", season: int | str = None
    ) -> list[UnderstatMatch]:
        """
        Get all matches with xG and win forecasts for a league and season.

        Supported leagues: ``"EPL"``, ``"La_liga"``, ``"Bundesliga"``,
        ``"Serie_A"``, ``"Ligue_1"``, ``"RFPL"``.
        """
        return self.__service.get_league_matches(league=league, season=season)

    def get_league_players(
        self, league: str = "EPL", season: int | str = None
    ) -> list[UnderstatPlayerStat]:
        """
        Get player xG/xA stats for a league and season.
        """
        return self.__service.get_league_players(league=league, season=season)

    def get_league_teams(
        self, league: str = "EPL", season: int | str = None
    ) -> list[UnderstatTeam]:
        """
        Get teams and their match-by-match xG/xPTS history for a league and season.
        """
        return self.__service.get_league_teams(league=league, season=season)

    def get_match_shots(self, match_id: int | str) -> list[UnderstatShot]:
        """
        Get all shots with pitch coordinates (X, Y) and xG for a match ID.
        """
        return self.__service.get_match_shots(match_id)

    def get_team_matches(
        self, team: str, season: int | str = None
    ) -> list[UnderstatMatch]:
        """
        Get matches for a specific team in a season (e.g. ``"Arsenal"``).
        """
        return self.__service.get_team_matches(team=team, season=season)

    def get_team_players(
        self, team: str, season: int | str = None
    ) -> list[UnderstatPlayerStat]:
        """
        Get squad player xG/xA stats for a team in a season.
        """
        return self.__service.get_team_players(team=team, season=season)

    def get_player_shots(self, player_id: int | str) -> list[UnderstatShot]:
        """
        Get career shots with coordinates (X, Y) and xG for a player ID.
        """
        return self.__service.get_player_shots(player_id)
