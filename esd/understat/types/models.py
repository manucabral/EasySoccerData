"""
Understat dataclasses and parsers.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def _to_float(val, default: float = 0.0) -> float:
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def _to_int(val, default: int = 0) -> int:
    try:
        return int(float(val)) if val is not None else default
    except (ValueError, TypeError):
        return default


@dataclass
class UnderstatMatch:
    """
    A match with Expected Goals (xG) and win probability forecast from Understat.
    """

    id: int = None
    is_result: bool = False
    datetime: str = None
    home_id: int = None
    home_team: str = None
    home_short: str = None
    away_id: int = None
    away_team: str = None
    away_short: str = None
    home_goals: int | None = None
    away_goals: int | None = None
    home_xg: float | None = None
    away_xg: float | None = None
    forecast_win: float | None = None
    forecast_draw: float | None = None
    forecast_loss: float | None = None


@dataclass
class UnderstatShot:
    """
    A single shot event with pitch coordinates (X, Y) and xG value.
    """

    id: int = None
    match_id: int = None
    minute: int = 0
    result: str = None
    x: float = 0.0
    y: float = 0.0
    xg: float = 0.0
    player: str = None
    player_id: int = None
    home_away: str = None
    situation: str = None
    shot_type: str = None
    home_team: str = None
    away_team: str = None
    home_goals: int = 0
    away_goals: int = 0
    date: str = None
    player_assisted: str = None
    last_action: str = None


@dataclass
class UnderstatPlayerStat:
    """
    Aggregated player xG / xA metrics on Understat.
    """

    id: int = None
    player_name: str = None
    team_title: str = None
    position: str = None
    games: int = 0
    time: int = 0
    goals: int = 0
    assists: int = 0
    shots: int = 0
    key_passes: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    xg: float = 0.0
    xa: float = 0.0
    npxg: float = 0.0
    xg_chain: float = 0.0
    xg_buildup: float = 0.0


@dataclass
class UnderstatTeamHistory:
    """
    Single match performance entry in an Understat team history list.
    """

    date: str = None
    home_away: str = None
    result: str = None
    scored: int = 0
    missed: int = 0
    pts: int = 0
    xg: float = 0.0
    xga: float = 0.0
    npxg: float = 0.0
    npxga: float = 0.0
    xpts: float = 0.0


@dataclass
class UnderstatTeam:
    """
    A team and its match-by-match xG history in a league season.
    """

    id: int = None
    title: str = None
    history: list[UnderstatTeamHistory] = field(default_factory=list)


def parse_league_matches(data: dict) -> list[UnderstatMatch]:
    """
    Parse matches from Understat ``dates`` list.
    """
    if not data:
        return []
    matches: list[UnderstatMatch] = []
    for item in data.get("dates", []) or []:
        h = item.get("h") or {}
        a = item.get("a") or {}
        goals = item.get("goals") or {}
        xg = item.get("xG") or {}
        fc = item.get("forecast") or {}
        is_res = bool(item.get("isResult", False))
        matches.append(
            UnderstatMatch(
                id=_to_int(item.get("id"), None),
                is_result=is_res,
                datetime=item.get("datetime"),
                home_id=_to_int(h.get("id"), None),
                home_team=h.get("title"),
                home_short=h.get("short_title"),
                away_id=_to_int(a.get("id"), None),
                away_team=a.get("title"),
                away_short=a.get("short_title"),
                home_goals=_to_int(goals.get("h"), None) if is_res else None,
                away_goals=_to_int(goals.get("a"), None) if is_res else None,
                home_xg=_to_float(xg.get("h"), None)
                if xg.get("h") is not None
                else None,
                away_xg=_to_float(xg.get("a"), None)
                if xg.get("a") is not None
                else None,
                forecast_win=_to_float(fc.get("w"), None)
                if fc.get("w") is not None
                else None,
                forecast_draw=_to_float(fc.get("d"), None)
                if fc.get("d") is not None
                else None,
                forecast_loss=_to_float(fc.get("l"), None)
                if fc.get("l") is not None
                else None,
            )
        )
    return matches


def parse_players(items: list[dict]) -> list[UnderstatPlayerStat]:
    """
    Parse player stats from Understat ``players`` list.
    """
    return [
        UnderstatPlayerStat(
            id=_to_int(p.get("id"), None),
            player_name=p.get("player_name"),
            team_title=p.get("team_title"),
            position=p.get("position"),
            games=_to_int(p.get("games")),
            time=_to_int(p.get("time")),
            goals=_to_int(p.get("goals")),
            assists=_to_int(p.get("assists")),
            shots=_to_int(p.get("shots")),
            key_passes=_to_int(p.get("key_passes")),
            yellow_cards=_to_int(p.get("yellow_cards")),
            red_cards=_to_int(p.get("red_cards")),
            xg=_to_float(p.get("xG")),
            xa=_to_float(p.get("xA")),
            npxg=_to_float(p.get("npxG")),
            xg_chain=_to_float(p.get("xGChain")),
            xg_buildup=_to_float(p.get("xGBuildup")),
        )
        for p in (items or [])
    ]


def parse_teams(data: dict) -> list[UnderstatTeam]:
    """
    Parse teams and their match histories from Understat ``teams`` dictionary.
    """
    if not data:
        return []
    raw_teams = data.get("teams") or {}
    iterator = raw_teams.values() if isinstance(raw_teams, dict) else raw_teams
    teams: list[UnderstatTeam] = []
    for t in iterator:
        history = [
            UnderstatTeamHistory(
                date=h.get("date"),
                home_away=h.get("h_a"),
                result=h.get("result"),
                scored=_to_int(h.get("scored")),
                missed=_to_int(h.get("missed")),
                pts=_to_int(h.get("pts")),
                xg=_to_float(h.get("xG")),
                xga=_to_float(h.get("xGA")),
                npxg=_to_float(h.get("npxG")),
                npxga=_to_float(h.get("npxGA")),
                xpts=_to_float(h.get("xpts")),
            )
            for h in (t.get("history") or [])
        ]
        teams.append(
            UnderstatTeam(
                id=_to_int(t.get("id"), None),
                title=t.get("title"),
                history=history,
            )
        )
    return teams


def parse_shots(items: list[dict]) -> list[UnderstatShot]:
    """
    Parse a list of shot dictionaries into :class:`UnderstatShot` instances.
    """
    return [
        UnderstatShot(
            id=_to_int(s.get("id"), None),
            match_id=_to_int(s.get("match_id"), None),
            minute=_to_int(s.get("minute")),
            result=s.get("result"),
            x=_to_float(s.get("X")),
            y=_to_float(s.get("Y")),
            xg=_to_float(s.get("xG")),
            player=s.get("player"),
            player_id=_to_int(s.get("player_id"), None),
            home_away=s.get("h_a"),
            situation=s.get("situation"),
            shot_type=s.get("shotType"),
            home_team=s.get("h_team"),
            away_team=s.get("a_team"),
            home_goals=_to_int(s.get("h_goals")),
            away_goals=_to_int(s.get("a_goals")),
            date=s.get("date"),
            player_assisted=s.get("player_assisted"),
            last_action=s.get("lastAction"),
        )
        for s in (items or [])
    ]


def parse_match_shots(data: dict) -> list[UnderstatShot]:
    """
    Parse home and away shots from ``getMatchData`` payload.
    """
    if not data:
        return []
    shots_raw = data.get("shots") or {}
    if isinstance(shots_raw, dict):
        combined = (shots_raw.get("h") or []) + (shots_raw.get("a") or [])
        return parse_shots(combined)
    if isinstance(shots_raw, list):
        return parse_shots(shots_raw)
    return []
