"""
Goaloo module.
"""

from . import types
from .client import GoalooClient
from .types import League, Match, Standing, Team

__all__ = [
    "GoalooClient",
    "types",
    "League",
    "Match",
    "Standing",
    "Team",
]
