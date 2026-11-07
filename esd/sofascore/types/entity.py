"""
Module with entity types.

The search endpoint uses these values to select entity types.
"""

from enum import Enum


class EntityType(Enum):
    """
    Enum with all entity types.
    """

    ALL = "all"
    TEAM = "teams"
    PLAYER = "player-team-persons"
    TOURNAMENT = "unique-tournaments"
    EVENT = "events"
