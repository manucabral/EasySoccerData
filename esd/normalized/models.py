"""Flat records shared by supported provider adapters.

Identifiers are strings scoped to their provider.
Unknown values remain None. The adapters cannot recover missing values that
a provider parser has already replaced with a default such as zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

SCHEMA_VERSION = "4"


@dataclass(frozen=True)
class NormalizedMatchEvent:
    """One source event, scoped to a match, with nullable native participants.

    ESPN event_id is native. 365Scores uses source_order within the response,
    without claiming a persistent event ID. team_id retains the source's event
    team, which can be the beneficiary of an own goal. Related players have no
    inferred role except for verified substitution ordering (incoming/outgoing).
    Shootout counters never become match minutes or alter match scores.
    """

    source: str
    match_id: str | None = None
    event_id: str | None = None
    source_order: int | None = None
    source_collection: str | None = None
    event_type: str | None = None
    source_type_id: str | None = None
    source_type_name: str | None = None
    source_subtype_id: str | None = None
    source_subtype_name: str | None = None
    source_period: str | None = None
    source_status_id: str | None = None
    minute: int | None = None
    added_minute: int | None = None
    clock_seconds: float | None = None
    source_game_time: float | None = None
    source_clock: str | None = None
    is_shootout: bool | None = None
    scoring_play: bool | None = None
    team_id: str | None = None
    team_name: str | None = None
    player_id: str | None = None
    player_name: str | None = None
    source_athlete_id: str | None = None
    related_player_id: str | None = None
    related_player_name: str | None = None
    related_source_athlete_id: str | None = None
    player_role: str | None = None
    related_player_role: str | None = None
    source_participants_json: str | None = None
    source_text: str | None = None


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
class NormalizedLineup:
    """One listed player in a match, including unused substitutes.

    Positions and lineup status retain source labels. Unknown flags stay None.
    For 365Scores, player_id is the member ID; source_athlete_id retains its
    distinct athlete ID. Neither names nor shirt numbers establish identity.
    """

    source: str
    match_id: str | None = None
    team_id: str | None = None
    player_id: str | None = None
    player_name: str | None = None
    source_athlete_id: str | None = None
    home_away: str | None = None
    starter: bool | None = None
    captain: bool | None = None
    jersey_number: str | None = None
    position: str | None = None
    source_position_id: str | None = None
    formation: str | None = None
    confirmed: bool | None = None
    source_lineup_status: str | None = None
    source_role: str | None = None


@dataclass(frozen=True)
class NormalizedPlayerMatchStats:
    """Source observations for one player/team/match, without season aggregation.

    Missing metrics remain None, including minutes for unused substitutes when
    no minutes were reported. Ratings and xG/xA retain their source models.
    For 365Scores, source_athlete_id is separate from the lineup member player_id.
    """

    source: str
    match_id: str | None = None
    team_id: str | None = None
    player_id: str | None = None
    player_name: str | None = None
    source_athlete_id: str | None = None
    minutes: int | None = None
    appearances: int | None = None
    goals: int | None = None
    assists: int | None = None
    own_goals: int | None = None
    shots: int | None = None
    shots_on_target: int | None = None
    passes: int | None = None
    accurate_passes: int | None = None
    key_passes: int | None = None
    touches: int | None = None
    tackles: int | None = None
    interceptions: int | None = None
    fouls_committed: int | None = None
    fouls_suffered: int | None = None
    offsides: int | None = None
    yellow_cards: int | None = None
    red_cards: int | None = None
    saves: int | None = None
    goals_conceded: int | None = None
    xg: float | None = None
    xa: float | None = None
    source_rating: float | None = None


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
