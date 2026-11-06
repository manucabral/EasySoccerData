"""
ESPN module.
"""

from . import types
from .client import ESPNClient
from .types import (
    ESPNKeyEvent,
    ESPNMatch,
    ESPNMatchSummary,
    ESPNRosterPlayer,
    ESPNStandingRow,
    ESPNStandingTable,
    ESPNStatItem,
    ESPNTeam,
)

__all__ = [
    "ESPNClient",
    "types",
    "ESPNKeyEvent",
    "ESPNMatch",
    "ESPNMatchSummary",
    "ESPNRosterPlayer",
    "ESPNStandingRow",
    "ESPNStandingTable",
    "ESPNStatItem",
    "ESPNTeam",
]
