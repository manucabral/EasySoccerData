"""
Contains the types for the FBRef service.
"""

from .details import MatchDetails, parse_match_details
from .match import Match, parse_matchs

__all__ = [
    "Match",
    "parse_matchs",
    "MatchDetails",
    "parse_match_details",
]
