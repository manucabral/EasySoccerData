"""
Goaloo module.

This client does not implement live corner counts or ball possession.
"""

from . import types
from .client import GoalooClient
from .types import (
    AsianHandicap,
    EventType,
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
    Team,
    TeamDetail,
    TeamHonor,
    TeamPlayer,
)

__all__ = [
    "GoalooClient",
    "types",
    "League",
    "Match",
    "Standing",
    "Team",
    "HeadToHead",
    "RecentForm",
    "OverUnder",
    "AsianHandicap",
    "GoalTiming",
    "MatchScore",
    "LiveOdds",
    "MatchEvent",
    "EventType",
    "TeamDetail",
    "TeamPlayer",
    "TeamHonor",
]
