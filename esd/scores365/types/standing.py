"""
365Scores standings dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .game import Competitor, Game, parse_competitor, parse_game


@dataclass
class StandingRow:
    """
    A single row in a 365Scores standings table.
    """

    position: int = 0
    team: Competitor = field(default_factory=Competitor)
    group_num: int = 1
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_diff: int = 0
    points: int = 0
    recent_form: list[int] = field(default_factory=list)
    next_match: Game | None = None


@dataclass
class StandingTable:
    """
    A competition standings table in 365Scores.
    """

    competition_id: int = None
    season_num: int = None
    stage_num: int = None
    display_name: str = None
    rows: list[StandingRow] = field(default_factory=list)


def parse_standings(data: dict) -> list[StandingTable]:
    """
    Parse standings tables from the 365Scores standings payload.
    """
    if not data:
        return []
    tables: list[StandingTable] = []
    for item in data.get("standings", []) or []:
        rows: list[StandingRow] = []
        for r in item.get("rows", []) or []:
            next_raw = r.get("nextMatch")
            rows.append(
                StandingRow(
                    position=int(r.get("position", 0) or 0),
                    team=parse_competitor(r.get("competitor") or {}),
                    group_num=int(r.get("groupNum", 1) or 1),
                    played=int(r.get("gamePlayed", 0) or 0),
                    won=int(r.get("gamesWon", 0) or 0),
                    drawn=int(r.get("gamesEven", 0) or 0),
                    lost=int(r.get("gamesLost", 0) or 0),
                    goals_for=int(r.get("for", 0) or 0),
                    goals_against=int(r.get("against", 0) or 0),
                    goal_diff=int(r.get("ratio", 0) or 0),
                    points=int(r.get("points", 0) or 0),
                    recent_form=list(r.get("recentForm") or []),
                    next_match=parse_game(next_raw) if next_raw else None,
                )
            )
        tables.append(
            StandingTable(
                competition_id=item.get("competitionId"),
                season_num=item.get("seasonNum"),
                stage_num=item.get("stageNum"),
                display_name=item.get("displayName"),
                rows=rows,
            )
        )
    return tables
