"""
Goaloo service module.
"""

from __future__ import annotations

import re

from ..logger import get_logger
from ..utils import TTLCache, get_api_json, get_text
from .endpoints import GoalooEndpoints
from .exceptions import LeagueNotFound, TeamNotFound
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
    parse_asian_handicap,
    parse_goal_timings,
    parse_head_to_head,
    parse_league,
    parse_live_odds,
    parse_match_events,
    parse_match_score,
    parse_matches,
    parse_over_under,
    parse_recent_form,
    parse_standings,
    parse_standings_compact,
    parse_team_detail,
    parse_teams,
)

_logger = get_logger("goaloo.service")

_BATTLE_RE = re.compile(r'var\s+battleData\s*=\s*"([^"]*)"')
_LAST_MATCH_RE = re.compile(r'var\s+lastMatchData\s*=\s*"([^"]*)"')

_CACHE_TTL = 60.0
_SEASONS_CACHE_TTL = 3600.0


class GoalooService:
    """
    A class to represent the Goaloo service.
    """

    def __init__(self, proxies: dict = None) -> None:
        self.proxies = proxies
        self.endpoints = GoalooEndpoints()
        self._seasons_cache = TTLCache(ttl=_SEASONS_CACHE_TTL, maxsize=128)
        self._data_cache = TTLCache(ttl=_CACHE_TTL, maxsize=128)
        self._h2h_cache = TTLCache(ttl=_CACHE_TTL, maxsize=128)

    def get_seasons(self, league_id: int) -> list[str]:
        """
        Get the available seasons for a competition.
        """
        cached = self._seasons_cache.get(league_id)
        if cached is not None:
            return cached

        url = self.endpoints.seasons_endpoint(league_id)
        data = get_api_json(url, proxies=self.proxies)
        seasons = data.get("SeasonList", []) if data else []
        if not seasons:
            raise LeagueNotFound(league_id)
        self._seasons_cache.set(league_id, seasons)
        return seasons

    def _resolve_season(self, league_id: int, season: str | None) -> str:
        if season:
            return season
        return self.get_seasons(league_id)[0]

    def _fetch_data(self, league_id: int, season: str) -> tuple[dict, dict]:
        key = (league_id, season)
        cached = self._data_cache.get(key)
        if cached is not None:
            _logger.debug("using cached goaloo data: %s", key)
            return cached
        url = self.endpoints.data_endpoint(league_id, season)
        _logger.debug("fetching goaloo data: %s", url)
        data = get_api_json(url, proxies=self.proxies)
        team_map = parse_teams(data.get("TeamInfo", [])) if data else {}
        if data:
            self._data_cache.set(key, (data, team_map))
        return data, team_map

    def _fetch_h2h_page(self, match_id: int) -> str:
        cached = self._h2h_cache.get(match_id)
        if cached is not None:
            return cached
        url = self.endpoints.h2h_endpoint(match_id)
        _logger.debug("fetching goaloo h2h: %s", url)
        page = get_text(url, proxies=self.proxies)
        if page:
            self._h2h_cache.set(match_id, page)
        return page

    def get_league(self, league_id: int, season: str = None) -> League:
        """
        Get a competition's metadata and team list.
        """
        season = self._resolve_season(league_id, season)
        data, team_map = self._fetch_data(league_id, season)
        if not data or "LeagueInfo" not in data:
            raise LeagueNotFound(league_id)
        league = parse_league(data["LeagueInfo"])
        league.teams = list(team_map.values())
        return league

    def get_matches(self, league_id: int, season: str = None) -> list[Match]:
        """
        Get all matches of a competition for a season.
        """
        season = self._resolve_season(league_id, season)
        data, team_map = self._fetch_data(league_id, season)
        if not data or "ScheduleList" not in data:
            raise LeagueNotFound(league_id)
        return parse_matches(data.get("ScheduleList", {}), team_map)

    def get_standings(self, league_id: int, season: str = None) -> list[Standing]:
        """
        Get the standings of a competition for a season.
        """
        season = self._resolve_season(league_id, season)
        data, team_map = self._fetch_data(league_id, season)
        if not data or "TotalScore" not in data:
            raise LeagueNotFound(league_id)
        return parse_standings(data.get("TotalScore", []), team_map)

    def get_h2h(self, match_id: int) -> HeadToHead:
        """
        Get the head-to-head history between the two teams of a match.
        """
        page = self._fetch_h2h_page(match_id)
        battle = _BATTLE_RE.search(page)
        return parse_head_to_head(battle.group(1) if battle else "")

    def get_last_matches(self, match_id: int) -> RecentForm:
        """
        Get the recent match results for both teams of a match.
        """
        page = self._fetch_h2h_page(match_id)
        last = _LAST_MATCH_RE.search(page)
        return parse_recent_form(last.group(1) if last else "")

    def get_over_under(self, league_id: int, season: str = None) -> list[OverUnder]:
        """
        Get the over/under result distribution for a competition.
        """
        season = self._resolve_season(league_id, season)
        data, team_map = self._fetch_data(league_id, season)
        if not data:
            raise LeagueNotFound(league_id)
        pan = data.get("BigSmallPan", {}) or {}
        return parse_over_under(pan.get("TotalBs", []), team_map)

    def get_asian_handicap(
        self, league_id: int, season: str = None
    ) -> list[AsianHandicap]:
        """
        Get the Asian handicap result distribution for a competition.
        """
        season = self._resolve_season(league_id, season)
        data, team_map = self._fetch_data(league_id, season)
        if not data:
            raise LeagueNotFound(league_id)
        pan = data.get("LetgoalPan", {}) or {}
        return parse_asian_handicap(pan.get("TotalPanLu", []), team_map)

    def get_home_standings(self, league_id: int, season: str = None) -> list[Standing]:
        """
        Get the home-only standings of a competition for a season.
        """
        season = self._resolve_season(league_id, season)
        data, team_map = self._fetch_data(league_id, season)
        if not data or "HomeScore" not in data:
            raise LeagueNotFound(league_id)
        return parse_standings_compact(data.get("HomeScore", []), team_map)

    def get_away_standings(self, league_id: int, season: str = None) -> list[Standing]:
        """
        Get the away-only standings of a competition for a season.
        """
        season = self._resolve_season(league_id, season)
        data, team_map = self._fetch_data(league_id, season)
        if not data or "GuestScore" not in data:
            raise LeagueNotFound(league_id)
        return parse_standings_compact(data.get("GuestScore", []), team_map)

    def get_goal_timings(self, league_id: int, season: str = None) -> list[GoalTiming]:
        """
        Get the goal timing distribution for each team of a competition.
        """
        season = self._resolve_season(league_id, season)
        data, team_map = self._fetch_data(league_id, season)
        if not data:
            raise LeagueNotFound(league_id)
        return parse_goal_timings(data.get("GoalInTimeList", []), team_map)

    def get_match_score(self, match_id: int) -> MatchScore:
        """
        Get the live score and status of a match.
        """
        url = self.endpoints.match_score_endpoint(match_id)
        _logger.debug("fetching goaloo match score: %s", url)
        data = get_api_json(url, proxies=self.proxies)
        return parse_match_score(data)

    def get_live_odds(self, match_id: int, company_id: int = 0) -> LiveOdds:
        """
        Get the live odds of a match for a bookmaker.

        Only available for matches that are upcoming or in play.
        """
        url = self.endpoints.live_odds_endpoint(match_id, company_id)
        _logger.debug("fetching goaloo live odds: %s", url)
        data = get_api_json(url, proxies=self.proxies)
        return parse_live_odds(data)

    def get_match_events(self, match_id: int) -> list[MatchEvent]:
        """
        Get the events (goals, cards and substitutions) of a match.
        """
        url = self.endpoints.match_events_endpoint(match_id)
        _logger.debug("fetching goaloo match events: %s", url)
        data = get_api_json(url, proxies=self.proxies)
        if not data or data.get("ErrCode", 0) != 0:
            return []
        return parse_match_events(data.get("Data", "") or "")

    def get_team(self, team_id: int) -> TeamDetail:
        """
        Get a team's squad, coach and honors.
        """
        url = self.endpoints.team_endpoint(team_id)
        _logger.debug("fetching goaloo team: %s", url)
        data = get_api_json(url, proxies=self.proxies)
        if not data or "TeamInfo" not in data:
            raise TeamNotFound(team_id)
        return parse_team_detail(data)
