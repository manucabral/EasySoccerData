"""
Contains the types for the Sofascore service.
"""

from .color import Color
from .event import Event, parse_event, parse_events
from .league import League, parse_league
from .match import Match, parse_match
from .match_events import (
    EventItem,
    EventType,
    MatchEvents,
    Substitution,
    parse_match_events,
)
from .match_stats import MatchStats, parse_match_stats
from .odds import MainOdds, OddsOption
from .players import Lineups, LineupTeam, Player, Players, parse_player, parse_players
from .scores import GlobalScores, Penalties, Scores
from .status import MatchStatus, Status
from .team import Team
from .tournament import Stage, Tournament, parse_tournament
from .tvnetwork import TVNetwork

__all__ = [
    "Event",
    "parse_event",
    "parse_events",
    "Tournament",
    "Stage",
    "parse_tournament",
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
    "Penalties",
    "GlobalScores",
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
    "MatchEvents",
    "parse_match_events",
    "EventItem",
    "EventType",
    "Substitution",
]
