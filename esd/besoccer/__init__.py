"""
BeSoccer module.
"""

from . import types
from .client import BeSoccerClient
from .types import (
    BeSoccerMatch,
    BeSoccerStandingRow,
    BeSoccerTeam,
)

__all__ = [
    "BeSoccerClient",
    "types",
    "BeSoccerMatch",
    "BeSoccerStandingRow",
    "BeSoccerTeam",
]
