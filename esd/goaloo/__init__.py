"""
Goaloo module.

Note: Goaloo's live corner-count and ball-possession feeds are not
available. Corner data was served from the retired nowgoal domain, and
ball possession is only rendered server-side without a JSON endpoint.
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
