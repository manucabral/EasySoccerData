"""Opt-in provider adapters. No network access or automatic entity matching."""

from __future__ import annotations

from datetime import datetime, timezone

from ..espn.types import ESPNMatch, ESPNStandingTable, ESPNTeam
from ..scores365.types import Competitor, Game, StandingTable
from ..sofascore.types import Event, Standing, Team
from ..understat.types import UnderstatMatch, UnderstatTeam
from .additional import additional_match, additional_team, sofa_standings
from .models import NormalizedMatch, NormalizedStanding, NormalizedTeam
from .remaining import (
    MATCH_TYPES,
    STANDING_TYPES,
    TEAM_TYPES,
    BeSoccerMatch,
    BeSoccerStandingRow,
    BeSoccerTeam,
    FBMatch,
    GoalooMatch,
    GoalooStanding,
    GoalooTeam,
    PromiedosMatch,
    PromiedosTeam,
    TMClub,
    match_record,
    standing_record,
    team_record,
)


def _identifier(value) -> str | None:
    return str(value) if value is not None else None


def _competition_id(provided, original=None) -> str | None:
    if provided is not None and original is not None and str(provided) != str(original):
        raise ValueError("competition_id conflicts with the provider model")
    return _identifier(original if original is not None else provided)


def _kickoff(value: str | datetime | None) -> datetime | None:
    if value is None or value == "":
        return None
    date = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    if date.tzinfo is None or date.utcoffset() is None:
        raise ValueError("Kickoff must include a timezone; localize source-local dates first")
    return date.astimezone(timezone.utc)


def normalize_team(team: ESPNTeam | Competitor | Team | UnderstatTeam | GoalooTeam | PromiedosTeam | BeSoccerTeam | TMClub) -> NormalizedTeam:
    """Convert a team model, preserving its source ID and original name."""
    if isinstance(team, TEAM_TYPES):
        return team_record(team)
    if isinstance(team, ESPNTeam):
        source = "espn"
    elif isinstance(team, Competitor):
        source = "scores365"
    elif isinstance(team, (Team, UnderstatTeam)):
        return additional_team(team)
    else:
        raise TypeError(f"Unsupported team model: {type(team).__name__}")
    return NormalizedTeam(source, _identifier(team.id), team.name, team.short_name)


def normalize_match(
    match: ESPNMatch | Game | Event | UnderstatMatch | FBMatch | GoalooMatch | PromiedosMatch | BeSoccerMatch,
    *,
    competition_id: str | int | None = None,
    season: str | int | None = None,
    source_timezone: str | None = None,
) -> NormalizedMatch:
    """Adapt one match; season is a caller-supplied label, not a native season ID.

    Supply the ESPN league code as competition_id when known. 365Scores models
    carry their own competition ID, which cannot be overridden with another ID.
    Native status codes/text are retained without asserting semantic equivalence.
    Invalid or naive kickoff times raise ValueError.
    """
    if isinstance(match, MATCH_TYPES):
        return match_record(match, competition_id, season, source_timezone)
    if isinstance(match, (Event, UnderstatMatch)):
        return additional_match(match, competition_id, season, source_timezone)
    if isinstance(match, ESPNMatch):
        source = "espn"
        competition = _competition_id(competition_id)
        name = source_season = stage = None
        kickoff = match.date
        status, text = match.status_name, match.status_detail
    elif isinstance(match, Game):
        source = "scores365"
        competition = _competition_id(competition_id, match.competition_id)
        name = match.competition_name
        source_season = _identifier(match.season_num)
        stage = _identifier(match.stage_num)
        kickoff = match.start_time
        status, text = _identifier(match.status_group), match.status_text
    else:
        raise TypeError(f"Unsupported match model: {type(match).__name__}")
    home = normalize_team(match.home_team)
    away = normalize_team(match.away_team)
    return NormalizedMatch(
        source=source,
        match_id=_identifier(match.id),
        competition_id=competition,
        competition_name=name,
        season=_identifier(season),
        source_season_id=source_season,
        stage_id=stage,
        kickoff=_kickoff(kickoff),
        home_team_id=home.team_id,
        home_team_name=home.name,
        away_team_id=away.team_id,
        away_team_name=away.name,
        home_score=match.home_team.score,
        away_score=match.away_team.score,
        source_status=status,
        source_status_text=text,
    )


def normalize_standings(
    table: ESPNStandingTable | StandingTable | Standing | GoalooStanding | BeSoccerStandingRow,
    *,
    competition_id: str | int | None = None,
    season: str | int | None = None,
) -> list[NormalizedStanding]:
    """Convert one standings table while retaining its stage/group context.

    Feed each table separately. No ranking, points, deductions or group IDs are
    recomputed. Unsupported models raise even if they contain no rows.
    """
    if isinstance(table, STANDING_TYPES):
        return [standing_record(table, competition_id, season)]
    if isinstance(table, Standing):
        return sofa_standings(table, competition_id, season)
    if isinstance(table, ESPNStandingTable):
        source = "espn"
        competition = _competition_id(competition_id)
        table_id, name = _identifier(table.id), table.name
        source_season = stage = None
    elif isinstance(table, StandingTable):
        source = "scores365"
        competition = _competition_id(competition_id, table.competition_id)
        table_id = None
        name = table.display_name
        source_season, stage = _identifier(table.season_num), _identifier(table.stage_num)
    else:
        raise TypeError(f"Unsupported standings model: {type(table).__name__}")
    rows = []
    for row in table.rows:
        team = normalize_team(row.team)
        rows.append(NormalizedStanding(
            source=source,
            competition_id=competition,
            season=_identifier(season),
            source_season_id=source_season,
            table_id=table_id,
            table_name=name,
            stage_id=stage,
            group_id=_identifier(row.group_num) if source == "scores365" else None,
            team_id=team.team_id,
            team_name=team.name,
            rank=row.rank if source == "espn" else row.position,
            played=row.played,
            won=row.won,
            drawn=row.drawn,
            lost=row.lost,
            goals_for=row.goals_for,
            goals_against=row.goals_against,
            goal_difference=row.goal_diff,
            points=row.points,
            deductions=row.deductions if source == "espn" else None,
        ))
    return rows
