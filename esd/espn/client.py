"""
Client for interacting with the ESPN Soccer API.
"""

from __future__ import annotations

from ..cache import CachePolicy, ResponseCache, ResponseInfo
from .service import ESPNService
from .types import (
    ESPNMatch,
    ESPNMatchSummary,
    ESPNSeasonCalendar,
    ESPNStandingTable,
    ESPNTeam,
)


class ESPNClient:
    """
    Client for fetching live scoreboards, match summaries, lineups, commentary
    and standings from ESPN.
    """

    def __init__(
        self, proxies: dict | None = None, *, response_cache: ResponseCache | None = None,
        cache_policy: CachePolicy | None = None, refresh: bool = False, request_delay: float = 0.0,
    ) -> None:
        """
        Initialize the ESPN client.

        Args:
            proxies: Optional proxy dictionary.
            response_cache: Optional persistent JSON cache. No optional dependencies.
            cache_policy: Freshness policy for cached responses.
            refresh: Bypass cache reads and publish validated replacements.
            request_delay: Minimum delay between source requests. Cache hits do not wait.
        """
        self.__service = ESPNService(
            proxies=proxies, response_cache=response_cache, cache_policy=cache_policy,
            refresh=refresh, request_delay=request_delay,
        )

    @property
    def last_response(self) -> ResponseInfo | None:
        """Whether the last response was cached and when it was originally fetched."""
        return self.__service.last_response

    def get_scoreboard(
        self, league: str = "arg.1", date: str = "today", *, expected_season: int | None = None
    ) -> list[ESPNMatch]:
        """
        Get matches for a league and date (``"today"``, ``"YYYY-MM-DD"`` or ``"YYYYMMDD"``).

        expected_season enables strict validation of source metadata and the
        event list. A response at the requested limit raises because it may be
        truncated. Ordinary calls retain their existing empty-result behavior.

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
        return self.__service.get_scoreboard(league=league, date=date, expected_season=expected_season)

    def get_season_calendar(
        self, league: str, season: int, *, anchor_date: str | None = None
    ) -> ESPNSeasonCalendar:
        """Get the source's calendar days for an ESPN season year.

        Uses July 1 unless anchor_date is supplied. The returned season must
        match the requested year. This is a snapshot, not proof of a final season.
        """
        return self.__service.get_season_calendar(league, season, anchor_date=anchor_date)

    def get_match_summary(
        self, event_id: int | str, league: str = "all"
    ) -> ESPNMatchSummary:
        """
        Get full match summary (boxscore stats, rosters, timeline events and commentary).
        """
        return self.__service.get_match_summary(event_id=event_id, league=league)

    def get_standings(
        self, league: str = "arg.1", season: int | str | None = None, *, strict: bool = False
    ) -> list[ESPNStandingTable]:
        """
        Get standings tables for a league and optional season year.

        strict=True requires standings metadata for the requested season.
        """
        return self.__service.get_standings(league=league, season=season, strict=strict)

    def get_teams(self, league: str = "arg.1") -> list[ESPNTeam]:
        """
        Get all teams participating in a league.
        """
        return self.__service.get_teams(league=league)
