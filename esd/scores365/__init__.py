"""
365Scores module.
"""

from . import types
from .client import Scores365Client
from .types import (
    Competitor,
    Game,
    GameEvent,
    GameStatItem,
    LineupPlayer,
    PlayerStat,
    SearchEntity,
    SearchResult,
    StandingRow,
    StandingTable,
    TeamLineup,
)

__all__ = [
    "Scores365Client",
    "types",
    "Competitor",
    "Game",
    "GameEvent",
    "GameStatItem",
    "LineupPlayer",
    "PlayerStat",
    "SearchEntity",
    "SearchResult",
    "StandingRow",
    "StandingTable",
    "TeamLineup",
]
