"""
Goaloo service module.
"""

from __future__ import annotations

from ..logger import get_logger
from ..utils import get_api_json
from .endpoints import GoalooEndpoints
from .exceptions import LeagueNotFound
from .types import (
    League,
    Match,
    Standing,
    parse_league,
    parse_matches,
    parse_standings,
    parse_teams,
)

_logger = get_logger("goaloo.service")


class GoalooService:
    """
    A class to represent the Goaloo service.
    """

    def __init__(self, proxies: dict = None) -> None:
        self.proxies = proxies
        self.endpoints = GoalooEndpoints()
        self._seasons_cache: dict[int, list[str]] = {}

    def get_seasons(self, league_id: int) -> list[str]:
        """
        Get the available seasons for a competition.
        """
        if league_id in self._seasons_cache:
            return self._seasons_cache[league_id]

        url = self.endpoints.seasons_endpoint(league_id)
        data = get_api_json(url, proxies=self.proxies)
        seasons = data.get("SeasonList", []) if data else []
        if not seasons:
            raise LeagueNotFound(league_id)
        self._seasons_cache[league_id] = seasons
        return seasons

    def _resolve_season(self, league_id: int, season: str | None) -> str:
        if season:
            return season
        return self.get_seasons(league_id)[0]

    def _fetch_data(self, league_id: int, season: str) -> dict:
        url = self.endpoints.data_endpoint(league_id, season)
        _logger.debug("fetching goaloo data: %s", url)
        return get_api_json(url, proxies=self.proxies)

    def get_league(self, league_id: int, season: str = None) -> League:
        """
        Get a competition's metadata and team list.
        """
        season = self._resolve_season(league_id, season)
        data = self._fetch_data(league_id, season)
        if not data or "LeagueInfo" not in data:
            raise LeagueNotFound(league_id)
        league = parse_league(data["LeagueInfo"])
        league.teams = list(parse_teams(data.get("TeamInfo", [])).values())
        return league

    def get_matches(self, league_id: int, season: str = None) -> list[Match]:
        """
        Get all matches of a competition for a season.
        """
        season = self._resolve_season(league_id, season)
        data = self._fetch_data(league_id, season)
        if not data or "ScheduleList" not in data:
            raise LeagueNotFound(league_id)
        team_map = parse_teams(data.get("TeamInfo", []))
        return parse_matches(data.get("ScheduleList", {}), team_map)

    def get_standings(self, league_id: int, season: str = None) -> list[Standing]:
        """
        Get the standings of a competition for a season.
        """
        season = self._resolve_season(league_id, season)
        data = self._fetch_data(league_id, season)
        if not data or "TotalScore" not in data:
            raise LeagueNotFound(league_id)
        team_map = parse_teams(data.get("TeamInfo", []))
        return parse_standings(data.get("TotalScore", []), team_map)
