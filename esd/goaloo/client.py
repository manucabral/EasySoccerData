"""
This module contains the client class for interacting with Goaloo.
"""

from __future__ import annotations

from .service import GoalooService
from .types import (
    AsianHandicap,
    GoalTiming,
    HeadToHead,
    League,
    LiveOdds,
    Match,
    MatchEvent,
    MatchScore,
    OverUnder,
    RecentForm,
    Standing,
    TeamDetail,
)


class GoalooClient:
    """
    Client for interacting with Goaloo.

    This class provides methods to access and retrieve football data
    (leagues, schedules and standings) from Goaloo.
    """

    def __init__(self, proxies: dict = None) -> None:
        """
        Initializes the Goaloo client.

        Args:
            proxies: Optional proxy dict.
        """
        self.__service = GoalooService(proxies=proxies)

    def get_league(self, league_id: int, season: str = None) -> League:
        """
        Get a competition's metadata and team list.

        Args:
            league_id (int): The Goaloo competition id (e.g. 36 for Premier League).
            season (str): The season (e.g. "2026-2027"). Defaults to current.

        Returns:
            League: The competition metadata.
        """
        return self.__service.get_league(league_id, season)

    def get_matches(self, league_id: int, season: str = None) -> list[Match]:
        """
        Get all matches of a competition for a season.

        Args:
            league_id (int): The Goaloo competition id.
            season (str): The season (e.g. "2026-2027"). Defaults to current.

        Returns:
            list[Match]: The matches of the competition.
        """
        return self.__service.get_matches(league_id, season)

    def get_standings(self, league_id: int, season: str = None) -> list[Standing]:
        """
        Get the standings of a competition for a season.

        Args:
            league_id (int): The Goaloo competition id.
            season (str): The season (e.g. "2026-2027"). Defaults to current.

        Returns:
            list[Standing]: The standings of the competition.
        """
        return self.__service.get_standings(league_id, season)

    def get_seasons(self, league_id: int) -> list[str]:
        """
        Get the available seasons for a competition.

        Args:
            league_id (int): The Goaloo competition id.

        Returns:
            list[str]: The available seasons.
        """
        return self.__service.get_seasons(league_id)

    def get_h2h(self, match_id: int) -> HeadToHead:
        """
        Get the head-to-head history between the two teams of a match.

        Args:
            match_id (int): The Goaloo match id.

        Returns:
            HeadToHead: The H2H meetings and aggregate record.
        """
        return self.__service.get_h2h(match_id)

    def get_last_matches(self, match_id: int) -> RecentForm:
        """
        Get the recent match results for both teams of a match.

        Args:
            match_id (int): The Goaloo match id.

        Returns:
            RecentForm: The recent results for both teams.
        """
        return self.__service.get_last_matches(match_id)

    def get_over_under(self, league_id: int, season: str = None) -> list[OverUnder]:
        """
        Get the over/under result distribution for a competition.

        Args:
            league_id (int): The Goaloo competition id.
            season (str): The season (e.g. "2026-2027"). Defaults to current.

        Returns:
            list[OverUnder]: The over/under distribution per team.
        """
        return self.__service.get_over_under(league_id, season)

    def get_asian_handicap(
        self, league_id: int, season: str = None
    ) -> list[AsianHandicap]:
        """
        Get the Asian handicap result distribution for a competition.

        Args:
            league_id (int): The Goaloo competition id.
            season (str): The season (e.g. "2026-2027"). Defaults to current.

        Returns:
            list[AsianHandicap]: The Asian handicap distribution per team.
        """
        return self.__service.get_asian_handicap(league_id, season)

    def get_home_standings(self, league_id: int, season: str = None) -> list[Standing]:
        """
        Get the home-only standings of a competition for a season.

        Args:
            league_id (int): The Goaloo competition id.
            season (str): The season (e.g. "2026-2027"). Defaults to current.

        Returns:
            list[Standing]: The home-only standings.
        """
        return self.__service.get_home_standings(league_id, season)

    def get_away_standings(self, league_id: int, season: str = None) -> list[Standing]:
        """
        Get the away-only standings of a competition for a season.

        Args:
            league_id (int): The Goaloo competition id.
            season (str): The season (e.g. "2026-2027"). Defaults to current.

        Returns:
            list[Standing]: The away-only standings.
        """
        return self.__service.get_away_standings(league_id, season)

    def get_goal_timings(self, league_id: int, season: str = None) -> list[GoalTiming]:
        """
        Get the goal timing distribution for each team of a competition.

        Args:
            league_id (int): The Goaloo competition id.
            season (str): The season (e.g. "2026-2027"). Defaults to current.

        Returns:
            list[GoalTiming]: The goals per ten-minute block for each team.
        """
        return self.__service.get_goal_timings(league_id, season)

    def get_match_score(self, match_id: int) -> MatchScore:
        """
        Get the live score and status of a match.

        Args:
            match_id (int): The Goaloo match id.

        Returns:
            MatchScore: The current score, state and time.
        """
        return self.__service.get_match_score(match_id)

    def get_live_odds(self, match_id: int, company_id: int = 0) -> LiveOdds:
        """
        Get the live odds of a match for a bookmaker.

        Only available for matches that are upcoming or in play.

        Args:
            match_id (int): The Goaloo match id.
            company_id (int): The bookmaker id (default 0).

        Returns:
            LiveOdds: The Asian handicap, over/under, 1x2 and corner odds.
        """
        return self.__service.get_live_odds(match_id, company_id)

    def get_match_events(self, match_id: int) -> list[MatchEvent]:
        """
        Get the events (goals, cards and substitutions) of a match.

        Args:
            match_id (int): The Goaloo match id.

        Returns:
            list[MatchEvent]: The match events in chronological order.
        """
        return self.__service.get_match_events(match_id)

    def get_team(self, team_id: int) -> TeamDetail:
        """
        Get a team's squad, coach and honors.

        Args:
            team_id (int): The Goaloo team id.

        Returns:
            TeamDetail: The team metadata, players, coach and honors.
        """
        return self.__service.get_team(team_id)
