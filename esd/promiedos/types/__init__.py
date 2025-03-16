"""
Contains the types for the Sofascore service.
"""

from .event import Event, parse_events, parse_event
from .league import League, parse_league
from .color import Color
from .status import Status, MatchStatus
from .team import Team
from .odds import MainOdds, OddsOption
from .tvnetwork import TVNetwork
from .scores import Scores
from .match import Match, parse_match
from .players import Player, Players, Lineups, LineupTeam, parse_players, parse_player
from .match_stats import MatchStats, parse_match_stats

__all__ = [
    "Event",
    "parse_event",
    "parse_events",
    "League",
    "parse_league",
    "Color",
    "Status",
    "MatchStatus",
    "Team",
    "MainOdds",
    "OddsOption",
    "TVNetwork",
    "Scores",
    "Match",
    "parse_match",
    "Player",
    "Players",
    "Lineups",
    "LineupTeam",
    "parse_players",
    "parse_player",
    "MatchStats",
    "parse_match_stats",
]
