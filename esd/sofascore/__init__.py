"""
Sofascore client module.
"""

from .client import SofascoreClient
from .types import (
    EntityType,
    Event,
    Team,
    Player,
    MatchStats,
    PlayerLineup,
    TeamLineup,
    Lineups,
    TeamColor,
    Category,
    Tournament,
    Season,
    Bracket,
    Standing,
)

__all__ = [
    "SofascoreClient",
    "EntityType",
    "Event",
    "Team",
    "Player",
    "MatchStats",
    "PlayerLineup",
    "TeamLineup",
    "Lineups",
    "TeamColor",
    "Category",
    "Tournament",
    "Season",
    "Bracket",
    "Standing",
]
