"""Shared schema definitions for DataFrame and file exports."""

from .models import (
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

TABLE_MODELS = {
    "matches": NormalizedMatch, "teams": NormalizedTeam, "standings": NormalizedStanding,
    "match_stats": NormalizedMatchStats, "shots": NormalizedShot, "player_stats": NormalizedPlayerStats,
    "players": NormalizedPlayer, "market_values": NormalizedMarketValue, "transfers": NormalizedTransfer,
}
INTEGER_COLUMNS = {
    "home_score", "away_score", "rank", "played", "won", "drawn", "lost",
    "goals_for", "goals_against", "goal_difference", "points", "deductions",
    "minute", "games", "minutes", "goals", "assists", "shots", "key_passes", "yellow_cards", "red_cards",
    "market_value", "value", "fee",
}
FLOAT_COLUMNS = {
    "home_xg", "away_xg", "forecast_win", "forecast_draw", "forecast_loss",
    "x", "y", "xg", "xa", "npxg", "xg_chain", "xg_buildup",
}
