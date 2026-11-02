"""
Goaloo module.
"""

from . import types
from .client import GoalooClient
from .types import (
    AsianHandicap,
    GoalTiming,
    HeadToHead,
    League,
    LiveOdds,
    Match,
    MatchScore,
    OverUnder,
    RecentForm,
    Standing,
    Team,
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
]
