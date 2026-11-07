"""Shared schema definitions for DataFrame and file exports."""

from .models import (
    NormalizedLineup,
    NormalizedMarketValue,
    NormalizedMatch,
    NormalizedMatchStats,
    NormalizedPlayer,
    NormalizedPlayerMatchStats,
    NormalizedPlayerStats,
    NormalizedShot,
    NormalizedStanding,
    NormalizedTeam,
    NormalizedTransfer,
)

TABLE_MODELS = {
    "lineups": NormalizedLineup, "player_match_stats": NormalizedPlayerMatchStats,
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
PLAYER_MATCH_COUNT_METRICS = (
    "minutes", "appearances", "goals", "assists", "own_goals", "shots", "shots_on_target",
    "passes", "accurate_passes", "key_passes", "touches", "tackles", "interceptions",
    "fouls_committed", "fouls_suffered", "offsides", "yellow_cards", "red_cards", "saves", "goals_conceded",
)
INTEGER_COLUMNS.update(PLAYER_MATCH_COUNT_METRICS)
BOOLEAN_COLUMNS = {"starter", "captain", "confirmed"}
FLOAT_COLUMNS = {
    "home_xg", "away_xg", "forecast_win", "forecast_draw", "forecast_loss",
    "x", "y", "xg", "xa", "npxg", "xg_chain", "xg_buildup",
    "home_possession_pct", "away_possession_pct",
    "source_rating",
}
