"""
Client for interacting with the ESPN Soccer API.
"""

from __future__ import annotations

from .service import ESPNService
from .types import (
    ESPNMatch,
    ESPNMatchSummary,
    ESPNStandingTable,
    ESPNTeam,
)


class ESPNClient:
    """
    Client for fetching live scoreboards, match summaries, lineups, commentary
    and standings from ESPN.
    """

    def __init__(self, proxies: dict | None = None) -> None:
        """
        Initialize the ESPN client.

        Args:
            proxies: Optional proxy dictionary.
        """
        self.__service = ESPNService(proxies=proxies)

    def get_scoreboard(
        self, league: str = "arg.1", date: str = "today"
    ) -> list[ESPNMatch]:
        """
        Get matches for a league and date (``"today"``, ``"YYYY-MM-DD"`` or ``"YYYYMMDD"``).

        Common league codes:
        - ``"arg.1"``: Liga Profesional Argentina
        - ``"eng.1"``: English Premier League
        - ``"esp.1"``: Spanish LaLiga
        - ``"ita.1"``: Italian Serie A
        - ``"ger.1"``: German Bundesliga
        - ``"fra.1"``: French Ligue 1
        - ``"bra.1"``: Brasileirão
        - ``"conmebol.libertadores"``: Copa Libertadores
        - ``"uefa.champions"``: UEFA Champions League
        - ``"all"``: All active leagues
        """
        return self.__service.get_scoreboard(league=league, date=date)

    def get_match_summary(
        self, event_id: int | str, league: str = "all"
    ) -> ESPNMatchSummary:
        """
        Get full match summary (boxscore stats, rosters, timeline events and commentary).
        """
        return self.__service.get_match_summary(event_id=event_id, league=league)

    def get_standings(
        self, league: str = "arg.1", season: int | str | None = None
    ) -> list[ESPNStandingTable]:
        """
        Get standings tables for a league and optional season year.
        """
        return self.__service.get_standings(league=league, season=season)

    def get_teams(self, league: str = "arg.1") -> list[ESPNTeam]:
        """
        Get all teams participating in a league.
        """
        return self.__service.get_teams(league=league)
