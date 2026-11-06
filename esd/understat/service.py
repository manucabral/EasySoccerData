"""
Understat service module.
"""

from __future__ import annotations

import codecs
import json
import re

from ..exceptions import SourceError
from ..utils import TTLCache, current_year, get_api_json, get_text
from .endpoints import UnderstatEndpoints
from .types import (
    UnderstatMatch,
    UnderstatPlayerStat,
    UnderstatShot,
    UnderstatTeam,
    parse_league_matches,
    parse_match_shots,
    parse_players,
    parse_shots,
    parse_teams,
)

_INLINE_JSON_RE = re.compile(r"var\s+(\w+)\s*=\s*JSON\.parse\('([^']+)'\)")


def extract_embedded_json(html_text: str) -> dict:
    """
    Extract ``var <name> = JSON.parse('...')`` variables embedded in Understat HTML.
    """
    result: dict = {}
    for name, encoded in _INLINE_JSON_RE.findall(html_text):
        decoded = codecs.decode(encoded, "unicode_escape")
        result[name] = json.loads(decoded)
    return result


class UnderstatService:
    """
    Service layer for fetching and parsing Understat data.
    """

    def __init__(self, proxies: dict | None = None) -> None:
        self.proxies = proxies
        self.endpoints = UnderstatEndpoints()
        self._cache = TTLCache(ttl=60.0)

    def _fetch(self, url: str) -> dict:
        cached = self._cache.get(url)
        if cached is not None:
            return cached
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://understat.com/",
        }
        try:
            data = get_api_json(url, headers=headers, proxies=self.proxies)
        except SourceError:
            raw = get_text(url, proxies=self.proxies)
            if "We will come back soon" in raw or "/css/errors.css" in raw:
                raise SourceError(
                    "Understat is temporarily under maintenance."
                ) from None
            embedded = extract_embedded_json(raw)
            if not embedded:
                raise
            data = embedded
        self._cache.set(url, data)
        return data

    def get_league_matches(
        self, league: str = "EPL", season: int | str = None
    ) -> list[UnderstatMatch]:
        """
        Get all matches with xG and win forecasts for a league and season.
        """
        yr = season if season is not None else current_year()
        data = self._fetch(self.endpoints.league_data(league, yr))
        if "datesData" in data and "dates" not in data:
            data = {"dates": data["datesData"]}
        return parse_league_matches(data)

    def get_league_players(
        self, league: str = "EPL", season: int | str = None
    ) -> list[UnderstatPlayerStat]:
        """
        Get player xG/xA stats for a league and season.
        """
        yr = season if season is not None else current_year()
        data = self._fetch(self.endpoints.league_data(league, yr))
        players = data.get("players") or data.get("playersData") or []
        return parse_players(players)

    def get_league_teams(
        self, league: str = "EPL", season: int | str = None
    ) -> list[UnderstatTeam]:
        """
        Get teams and their match-by-match xG/xPTS history for a league and season.
        """
        yr = season if season is not None else current_year()
        data = self._fetch(self.endpoints.league_data(league, yr))
        if "teamsData" in data and "teams" not in data:
            data = {"teams": data["teamsData"]}
        return parse_teams(data)

    def get_match_shots(self, match_id: int | str) -> list[UnderstatShot]:
        """
        Get shotmap coordinates (X, Y) and xG for a match.
        """
        data = self._fetch(self.endpoints.match_data(match_id))
        if "shotsData" in data and "shots" not in data:
            data = {"shots": data["shotsData"]}
        return parse_match_shots(data)

    def get_team_matches(
        self, team: str, season: int | str = None
    ) -> list[UnderstatMatch]:
        """
        Get matches for a specific team in a season.
        """
        yr = season if season is not None else current_year()
        data = self._fetch(self.endpoints.team_data(team, yr))
        if "datesData" in data and "dates" not in data:
            data = {"dates": data["datesData"]}
        return parse_league_matches(data)

    def get_team_players(
        self, team: str, season: int | str = None
    ) -> list[UnderstatPlayerStat]:
        """
        Get squad player xG/xA stats for a team in a season.
        """
        yr = season if season is not None else current_year()
        data = self._fetch(self.endpoints.team_data(team, yr))
        players = data.get("players") or data.get("playersData") or []
        return parse_players(players)

    def get_player_shots(self, player_id: int | str) -> list[UnderstatShot]:
        """
        Get all career shots with coordinates (X, Y) and xG for a player.
        """
        data = self._fetch(self.endpoints.player_data(player_id))
        shots = data.get("shots") or data.get("shotsData") or []
        return parse_shots(shots)
