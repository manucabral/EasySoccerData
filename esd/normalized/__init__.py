"""Normalized records and opt-in adapters for the supported provider tables."""

from .adapters import normalize_match, normalize_standings, normalize_team
from .additional import normalize_match_stats, normalize_player_stats, normalize_shot
from .dataframe import normalized_to_dataframe
from .models import (
    SCHEMA_VERSION,
    NormalizedMarketValue,
    NormalizedMatch,
    NormalizedMatchStats,
    NormalizedPlayer,
    NormalizedPlayerStats,
    NormalizedShot,
    NormalizedStanding,
    NormalizedTeam,
    NormalizedTransfer,
)

__all__ = [
    "NormalizedPlayer", "NormalizedMarketValue", "NormalizedTransfer",
    "SCHEMA_VERSION",
    "NormalizedMatch",
    "NormalizedStanding",
    "NormalizedTeam",
    "normalize_match",
    "normalize_standings",
    "normalize_team",
    "normalized_to_dataframe",
    "NormalizedMatchStats",
    "NormalizedPlayerStats",
    "NormalizedShot",
    "normalize_match_stats",
    "normalize_player_stats",
    "normalize_shot",
]
