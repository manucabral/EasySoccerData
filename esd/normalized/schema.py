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
MATCH_COUNT_METRICS = (
    "shots", "shots_on_target", "corners", "fouls", "offsides", "yellow_cards", "red_cards",
    "saves", "passes", "accurate_passes",
)
INTEGER_COLUMNS.update(f"{side}_{metric}" for side in ("home", "away") for metric in MATCH_COUNT_METRICS)
FLOAT_COLUMNS = {
    "home_xg", "away_xg", "forecast_win", "forecast_draw", "forecast_loss",
    "x", "y", "xg", "xa", "npxg", "xg_chain", "xg_buildup",
    "home_possession_pct", "away_possession_pct",
}
