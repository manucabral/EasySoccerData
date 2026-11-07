"""Adapters preserving native identities and date/score availability."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from ..besoccer.types import BeSoccerMatch, BeSoccerStandingRow, BeSoccerTeam
from ..fbref.types import Match as FBMatch
from ..goaloo.types import Match as GoalooMatch
from ..goaloo.types import Standing as GoalooStanding
from ..goaloo.types import Team as GoalooTeam
from ..promiedos.types import Match as PromiedosMatch
from ..promiedos.types import MatchStatus
from ..promiedos.types import Team as PromiedosTeam
from ..transfermarkt.types import TMClub
from .models import NormalizedMatch, NormalizedStanding, NormalizedTeam


def native_id(value):
    return str(value) if value not in (None, "", 0) else None


def kickoff(value, zone=None):
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        if zone is None:
            raise ValueError("Naive source dates require explicit source_timezone")
        parsed = parsed.replace(tzinfo=timezone.utc if zone == "UTC" else ZoneInfo(zone))
    return parsed.astimezone(timezone.utc)


TEAM_TYPES = (GoalooTeam, PromiedosTeam, BeSoccerTeam, TMClub)
MATCH_TYPES = (GoalooMatch, PromiedosMatch, BeSoccerMatch, FBMatch)
STANDING_TYPES = (GoalooStanding, BeSoccerStandingRow)


def team_record(team):
    source = {
        GoalooTeam: "goaloo",
        PromiedosTeam: "promiedos",
        BeSoccerTeam: "besoccer",
        TMClub: "transfermarkt",
    }[type(team)]
    return NormalizedTeam(
        source, native_id(team.id), team.name or None, getattr(team, "short_name", None)
    )


def match_record(match, competition_id, season, source_timezone):
    source = {
        GoalooMatch: "goaloo",
        PromiedosMatch: "promiedos",
        BeSoccerMatch: "besoccer",
        FBMatch: "fbref",
    }[type(match)]
    common = {
        "source": source,
        "match_id": native_id(match.id),
        "competition_id": native_id(competition_id),
        "season": native_id(season),
    }
    if isinstance(match, FBMatch):
        if match.competition_id is not None:
            if competition_id is not None and str(competition_id) != str(match.competition_id):
                raise ValueError("competition_id conflicts with the provider model")
            common["competition_id"] = str(match.competition_id)
        raw = match.raw_score or ""
        has_score = bool(re.search(r"\d+(?:\s*\(\d+\))?\s*[–-]\s*(?:\(\d+\)\s*)?\d+", raw))
        # A time without a date cannot identify an instant.
        date = f"{match.date}T{match.start_time}" if match.date and match.start_time else None
        identifier = re.search(r"/matches/([^/?]+)", match.id or "")
        if identifier:
            common["match_id"] = identifier.group(1)
        return NormalizedMatch(
            **common,
            kickoff=kickoff(date, source_timezone),
            home_team_id=native_id(match.home_team_id),
            home_team_name=match.home_team or None,
            away_team_id=native_id(match.away_team_id),
            away_team_name=match.away_team or None,
            home_score=match.home_score if has_score else None,
            away_score=match.away_score if has_score else None,
        )
    home, away = team_record(match.home_team), team_record(match.away_team)
    if isinstance(match, PromiedosMatch):
        original = native_id(match.league.id)
        if original is not None:
            if competition_id is not None and str(competition_id) != original:
                raise ValueError("competition_id conflicts with the provider model")
            common["competition_id"] = original
        date = (
            datetime.strptime(match.raw_start_time, "%d-%m-%Y %H:%M").isoformat()
            if match.raw_start_time
            else None
        )
        active = match.status.value in (MatchStatus.FINISHED, MatchStatus.IN_PROGRESS)
        hs, aws = (match.scores.home, match.scores.away) if active else (None, None)
        status = str(
            match.status.native_value
            if match.status.native_value is not None
            else match.status.value.value
        )
        text = match.status.name
    elif isinstance(match, GoalooMatch):
        date = match.start_time or None
        active = bool(re.fullmatch(r"\s*\d+\s*-\s*\d+\s*", match.score or ""))
        hs, aws = (match.home_score, match.away_score) if active else (None, None)
        # A score is not evidence of a finished match.
        status = str(match.native_state) if match.native_state is not None else None
        text = match.score or None
    else:
        original = native_id(match.competition_slug)
        if original is not None:
            if competition_id is not None and str(competition_id) != original:
                raise ValueError("competition_id conflicts with the provider model")
            common["competition_id"] = original
        date, hs, aws = match.start_time, match.home_team.score, match.away_team.score
        status, text = native_id(match.status_id), match.time_display
        common["competition_name"] = match.competition_name
    return NormalizedMatch(
        **common,
        kickoff=kickoff(date, source_timezone),
        home_team_id=home.team_id,
        home_team_name=home.name,
        away_team_id=away.team_id,
        away_team_name=away.name,
        home_score=hs,
        away_score=aws,
        source_status=status,
        source_status_text=text,
    )


def standing_record(row, competition_id, season):
    team = team_record(row.team)
    goaloo = isinstance(row, GoalooStanding)
    return NormalizedStanding(
        source=team.source,
        competition_id=native_id(competition_id),
        season=native_id(season),
        team_id=team.team_id,
        team_name=team.name,
        rank=row.rank if goaloo else row.position,
        played=row.played,
        won=row.win if goaloo else row.won,
        drawn=row.draw if goaloo else row.drawn,
        lost=row.loss if goaloo else row.lost,
        goals_for=row.goals_for,
        goals_against=row.goals_against,
        goal_difference=row.goal_diff,
        points=row.points,
    )
