"""
FBref client module.
"""

from . import types
from .client import FBrefClient
from .types import Match, MatchDetails

__all__ = ["FBrefClient", "types", "Match", "MatchDetails"]
