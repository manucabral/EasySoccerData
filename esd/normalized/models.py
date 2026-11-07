"""Flat records shared by supported provider adapters.

Identifiers are strings scoped to their provider.
Unknown values remain None. The adapters cannot recover missing values that
a provider parser has already replaced with a default such as zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

SCHEMA_VERSION = "2"


@dataclass(frozen=True)
class NormalizedTeam:
    """One team, keyed by (source, team_id). Match scores are excluded."""

    source: str
    team_id: str | None = None
    name: str | None = None
    short_name: str | None = None


@dataclass(frozen=True)
class NormalizedMatch:
    """One match. Kickoff is aware UTC; status fields retain source semantics."""

    source: str
    match_id: str | None = None
    competition_id: str | None = None
    competition_name: str | None = None
    season: str | None = None
    source_season_id: str | None = None
    stage_id: str | None = None
    kickoff: datetime | None = None
    home_team_id: str | None = None
    home_team_name: str | None = None
    away_team_id: str | None = None
    away_team_name: str | None = None
    home_score: int | None = None
    away_score: int | None = None
    source_status: str | None = None
    source_status_text: str | None = None


@dataclass(frozen=True)
class NormalizedStanding:
    """One team in one source table, stage and group for a season snapshot."""

    source: str
    competition_id: str | None = None
    season: str | None = None
    source_season_id: str | None = None
    table_id: str | None = None
    table_name: str | None = None
    stage_id: str | None = None
    group_id: str | None = None
    team_id: str | None = None
    team_name: str | None = None
    rank: int | None = None
    played: int | None = None
    won: int | None = None
    drawn: int | None = None
    lost: int | None = None
    goals_for: int | None = None
    goals_against: int | None = None
    goal_difference: int | None = None
    points: int | None = None
    deductions: int | None = None


@dataclass(frozen=True)
class NormalizedMatchStats:
    """One match's source totals. Missing values remain None; reported zeros stay zero.

    Possession uses percentage points (0 to 100). Other added metrics are counts.
    source_period retains the source total selector, including extra time where
    the provider includes it. Matching columns do not establish metric equivalence.
    """

    source: str
    match_id: str | None = None
    home_xg: float | None = None
    away_xg: float | None = None
    forecast_win: float | None = None
    forecast_draw: float | None = None
    forecast_loss: float | None = None
    source_period: str | None = None
    home_possession_pct: float | None = None
    away_possession_pct: float | None = None
    home_shots: int | None = None
    away_shots: int | None = None
    home_shots_on_target: int | None = None
    away_shots_on_target: int | None = None
    home_corners: int | None = None
    away_corners: int | None = None
    home_fouls: int | None = None
    away_fouls: int | None = None
    home_offsides: int | None = None
    away_offsides: int | None = None
    home_yellow_cards: int | None = None
    away_yellow_cards: int | None = None
    home_red_cards: int | None = None
    away_red_cards: int | None = None
    home_saves: int | None = None
    away_saves: int | None = None
    home_passes: int | None = None
    away_passes: int | None = None
    home_accurate_passes: int | None = None
    away_accurate_passes: int | None = None


@dataclass(frozen=True)
class NormalizedShot:
    """One Understat shot. Coordinates retain the source's native convention."""

    source: str
    shot_id: str | None = None
    match_id: str | None = None
    player_id: str | None = None
    player_name: str | None = None
    minute: int | None = None
    home_away: str | None = None
    result: str | None = None
    situation: str | None = None
    source_shot_type: str | None = None
    source_date: str | None = None
    coordinate_system: str | None = None
    x: float | None = None
    y: float | None = None
    xg: float | None = None


@dataclass(frozen=True)
class NormalizedPlayerStats:
    """One Understat player-season row. Team names may contain multiple clubs."""

    source: str
    competition_id: str | None = None
    season: str | None = None
    player_id: str | None = None
    player_name: str | None = None
    source_team_names: str | None = None
    position: str | None = None
    games: int | None = None
    minutes: int | None = None
    goals: int | None = None
    assists: int | None = None
    shots: int | None = None
    key_passes: int | None = None
    yellow_cards: int | None = None
    red_cards: int | None = None
    xg: float | None = None
    xa: float | None = None
    npxg: float | None = None
    xg_chain: float | None = None
    xg_buildup: float | None = None


@dataclass(frozen=True)
class NormalizedPlayer:
    """Player profile as reported by the source at download time."""

    source: str
    player_id: str | None = None
    name: str | None = None
    team_id: str | None = None
    position: str | None = None
    source_birth_date: str | None = None
    market_value: int | None = None
    currency: str | None = None


@dataclass(frozen=True)
class NormalizedMarketValue:
    """Native valuation history. Source dates are retained as text."""

    source: str
    player_id: str | None = None
    team_id: str | None = None
    source_season_id: str | None = None
    source_date: str | None = None
    value: int | None = None
    currency: str | None = None


@dataclass(frozen=True)
class NormalizedTransfer:
    """Native transfer history, including source fee display and pending status."""

    source: str
    transfer_id: str | None = None
    player_id: str | None = None
    source_season: str | None = None
    source_date: str | None = None
    from_team_id: str | None = None
    to_team_id: str | None = None
    fee: int | None = None
    source_fee_display: str | None = None
    source_pending: str | None = None
    source_transfer_type: str | None = None
