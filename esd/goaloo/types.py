"""
Goaloo data types and parsers.

The raw payload is a list-of-lists structure. Field positions are fixed by
Goaloo's own frontend renderer (see ``/scripts/v2/league``). We parse the
core, stable fields and resolve team names through ``TeamInfo``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Team:
    """
    A team as reported by Goaloo.
    """

    id: int = field(default=0)
    name: str = field(default="")
    logo: str = field(default="")


@dataclass
class League:
    """
    A competition/league and its metadata.
    """

    id: int = field(default=0)
    name: str = field(default="")
    season: str = field(default="")
    short_name: str = field(default="")
    logo: str = field(default="")
    total_rounds: int = field(default=0)
    teams: list[Team] = field(default_factory=list)


@dataclass
class Match:
    """
    A scheduled or played match.
    """

    id: int = field(default=0)
    round: int = field(default=0)
    start_time: str = field(default="")
    home_team: Team = field(default_factory=Team)
    away_team: Team = field(default_factory=Team)
    score: str = field(default="")
    half_score: str = field(default="")
    home_score: int = field(default=0)
    away_score: int = field(default=0)


@dataclass
class Standing:
    """
    A row of the competition standings.
    """

    rank: int = field(default=0)
    team: Team = field(default_factory=Team)
    played: int = field(default=0)
    win: int = field(default=0)
    draw: int = field(default=0)
    loss: int = field(default=0)
    goals_for: int = field(default=0)
    goals_against: int = field(default=0)
    goal_diff: int = field(default=0)
    points: int = field(default=0)


def _to_int(value: any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _get(raw: list, index: int, default: any = None) -> any:
    return raw[index] if index < len(raw) else default


def _parse_score(score: str) -> tuple[int, int]:
    if not score or "-" not in score:
        return 0, 0
    parts = score.split("-")
    if len(parts) >= 2:
        return _to_int(parts[0]), _to_int(parts[1])
    return 0, 0


def parse_team(raw: list) -> Team:
    """
    Parse a team row: ``[team_id, name, '', logo_path, 0]``.
    """
    return Team(id=_to_int(_get(raw, 0)), name=_get(raw, 1, "") or "", logo=_get(raw, 3, "") or "")


def parse_teams(data: list) -> dict[int, Team]:
    """
    Build a ``team_id -> Team`` map from the ``TeamInfo`` payload.
    """
    return {_to_int(row[0]): parse_team(row) for row in data if row}


def parse_league(data: list) -> League:
    """
    Parse ``LeagueInfo``: ``[id, name, season, color, logo, total_rounds, ...]``.
    """
    return League(
        id=_to_int(_get(data, 0)),
        name=_get(data, 1, "") or "",
        season=_get(data, 2, "") or "",
        logo=_get(data, 4, "") or "",
        total_rounds=_to_int(_get(data, 5)),
        short_name=_get(data, 7, "") or "",
    )


def parse_matches(schedule: dict, team_map: dict[int, Team]) -> list[Match]:
    """
    Parse the ``ScheduleList`` payload (``{"R_1": [match, ...], ...}``).

    Each match row: ``[id, sclass_id, ?, datetime, home_id, away_id, score,
    half_score, ...]``.
    """
    matches: list[Match] = []
    for round_key, entries in schedule.items():
        round_no = _to_int(str(round_key).replace("R_", ""))
        for raw in entries:
            home_id = _to_int(_get(raw, 4))
            away_id = _to_int(_get(raw, 5))
            score = _get(raw, 6, "") or ""
            home_score, away_score = _parse_score(score)
            matches.append(
                Match(
                    id=_to_int(_get(raw, 0)),
                    round=round_no,
                    start_time=_get(raw, 3, "") or "",
                    home_team=team_map.get(home_id, Team(id=home_id, name=str(home_id))),
                    away_team=team_map.get(away_id, Team(id=away_id, name=str(away_id))),
                    score=score,
                    half_score=_get(raw, 7, "") or "",
                    home_score=home_score,
                    away_score=away_score,
                )
            )
    return matches


def parse_standings(data: list, team_map: dict[int, Team]) -> list[Standing]:
    """
    Parse the ``TotalScore`` payload into standings rows.

    Row layout: ``[?, rank, team_id, ?, played, win, draw, loss, gf, ga, gd,
    ..., points, ...]``.
    """
    standings: list[Standing] = []
    for raw in data:
        team_id = _to_int(_get(raw, 2))
        standings.append(
            Standing(
                rank=_to_int(_get(raw, 1)),
                team=team_map.get(team_id, Team(id=team_id, name=str(team_id))),
                played=_to_int(_get(raw, 4)),
                win=_to_int(_get(raw, 5)),
                draw=_to_int(_get(raw, 6)),
                loss=_to_int(_get(raw, 7)),
                goals_for=_to_int(_get(raw, 8)),
                goals_against=_to_int(_get(raw, 9)),
                goal_diff=_to_int(_get(raw, 10)),
                points=_to_int(_get(raw, 16)),
            )
        )
    return standings
