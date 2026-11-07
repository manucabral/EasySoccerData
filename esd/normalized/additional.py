"""Sofascore and Understat adapters; provider semantics stay explicit."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from ..sofascore.types import Event, Standing, StatusType, Team
from ..understat.types import UnderstatMatch, UnderstatPlayerStat, UnderstatShot, UnderstatTeam
from .models import (
    NormalizedMatch,
    NormalizedMatchStats,
    NormalizedPlayerStats,
    NormalizedShot,
    NormalizedStanding,
    NormalizedTeam,
)


def _id(value):
    return str(value) if value is not None else None


def additional_team(team):
    if isinstance(team, Team):
        return NormalizedTeam("sofascore", _id(team.id) if team.id else None,
                              team.name or None, team.short_name or None)
    if isinstance(team, UnderstatTeam):
        return NormalizedTeam("understat", _id(team.id), team.title)
    raise TypeError(f"Unsupported team model: {type(team).__name__}")


def additional_match(match, competition_id, season, source_timezone):
    if isinstance(match, Event):
        if competition_id is not None and match.unique_tournament_id is not None:
            if str(competition_id) != str(match.unique_tournament_id):
                raise ValueError("competition_id conflicts with the provider model")
        competition = _id(match.unique_tournament_id if match.unique_tournament_id is not None else competition_id)
        active = match.status.type in (StatusType.IN_PROGRESS, StatusType.FINISHED)
        return NormalizedMatch(
            source="sofascore", match_id=_id(match.id) if match.id else None,
            competition_id=competition, competition_name=match.tournament.name,
            season=_id(season), source_season_id=_id(match.source_season_id),
            kickoff=datetime.fromtimestamp(match.start_timestamp, timezone.utc) if match.start_timestamp else None,
            home_team_id=additional_team(match.home_team).team_id, home_team_name=match.home_team.name or None,
            away_team_id=additional_team(match.away_team).team_id, away_team_name=match.away_team.name or None,
            home_score=match.home_score.current if active else None,
            away_score=match.away_score.current if active else None,
            source_status=match.status.type.value, source_status_text=match.status.description,
        )
    if isinstance(match, UnderstatMatch):
        kickoff = None
        if match.datetime:
            kickoff = datetime.fromisoformat(match.datetime.replace("Z", "+00:00"))
            if kickoff.tzinfo is None:
                if source_timezone is None:
                    raise ValueError("Understat naive dates require an explicit source_timezone")
                zone = timezone.utc if source_timezone == "UTC" else ZoneInfo(source_timezone)
                kickoff = kickoff.replace(tzinfo=zone)
            kickoff = kickoff.astimezone(timezone.utc)
        return NormalizedMatch(
            source="understat", match_id=_id(match.id), competition_id=_id(competition_id),
            season=_id(season), kickoff=kickoff,
            home_team_id=_id(match.home_id), home_team_name=match.home_team,
            away_team_id=_id(match.away_id), away_team_name=match.away_team,
            home_score=match.home_goals if match.is_result else None,
            away_score=match.away_goals if match.is_result else None,
            source_status="result" if match.is_result else "fixture",
        )
    raise TypeError(f"Unsupported match model: {type(match).__name__}")


def sofa_standings(table: Standing, competition_id, season):
    result = []
    for row in table.items:
        team = additional_team(row.team) if row.team is not None else NormalizedTeam("sofascore")
        result.append(NormalizedStanding(
            source="sofascore", competition_id=_id(competition_id), season=_id(season),
            table_id=_id(table.id), table_name=table.name, team_id=team.team_id, team_name=team.name,
            rank=row.position, played=row.matches, won=row.wins, drawn=row.draws, lost=row.losses,
            goals_for=row.scores_for, goals_against=row.scores_against,
            goal_difference=int(row.score_diff_formatted) if row.score_diff_formatted else None,
            points=row.points,
        ))
    return result


def normalize_match_stats(match: UnderstatMatch) -> NormalizedMatchStats:
    """Retain Understat xG/forecast values without recalculating metrics."""
    if not isinstance(match, UnderstatMatch):
        raise TypeError("Match statistics adapter requires UnderstatMatch")
    return NormalizedMatchStats("understat", _id(match.id), match.home_xg, match.away_xg,
                                match.forecast_win, match.forecast_draw, match.forecast_loss)


def normalize_shot(shot: UnderstatShot) -> NormalizedShot:
    """Keep Understat native coordinates; no pitch-size or orientation conversion."""
    if not isinstance(shot, UnderstatShot):
        raise TypeError("Shot adapter requires UnderstatShot")
    return NormalizedShot(
        source="understat", shot_id=_id(shot.id), match_id=_id(shot.match_id),
        player_id=_id(shot.player_id), player_name=shot.player, minute=shot.minute,
        home_away=shot.home_away, result=shot.result, situation=shot.situation,
        source_shot_type=shot.shot_type, source_date=shot.date,
        coordinate_system="understat-native", x=shot.x, y=shot.y, xg=shot.xg,
    )


def normalize_player_stats(
    player: UnderstatPlayerStat, *, competition_id=None, season=None,
) -> NormalizedPlayerStats:
    """One season aggregation. source_team_names is not a resolved team identity."""
    if not isinstance(player, UnderstatPlayerStat):
        raise TypeError("Player statistics adapter requires UnderstatPlayerStat")
    return NormalizedPlayerStats(
        source="understat", competition_id=_id(competition_id), season=_id(season),
        player_id=_id(player.id), player_name=player.player_name, source_team_names=player.team_title,
        position=player.position, games=player.games, minutes=player.time, goals=player.goals,
        assists=player.assists, shots=player.shots, key_passes=player.key_passes,
        yellow_cards=player.yellow_cards, red_cards=player.red_cards,
        xg=player.xg, xa=player.xa, npxg=player.npxg,
        xg_chain=player.xg_chain, xg_buildup=player.xg_buildup,
    )
