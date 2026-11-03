"""
Goaloo data types and parsers.

The raw payload is a list-of-lists structure. Field positions are fixed by
Goaloo's own frontend renderer (see ``/scripts/v2/league``). We parse the
core, stable fields and resolve team names through ``TeamInfo``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


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


def parse_standings_compact(data: list, team_map: dict[int, Team]) -> list[Standing]:
    """
    Parse a compact standings payload (home, away or half-time tables).

    Row layout: ``[rank, team_id, played, win, draw, loss, gf, ga, gd, ...,
    points]``.
    """
    standings: list[Standing] = []
    for raw in data:
        team_id = _to_int(_get(raw, 1))
        standings.append(
            Standing(
                rank=_to_int(_get(raw, 0)),
                team=team_map.get(team_id, Team(id=team_id, name=str(team_id))),
                played=_to_int(_get(raw, 2)),
                win=_to_int(_get(raw, 3)),
                draw=_to_int(_get(raw, 4)),
                loss=_to_int(_get(raw, 5)),
                goals_for=_to_int(_get(raw, 6)),
                goals_against=_to_int(_get(raw, 7)),
                goal_diff=_to_int(_get(raw, 8)),
                points=_to_int(_get(raw, 14)),
            )
        )
    return standings


def _to_float(value: any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass
class Meeting:
    """
    A single head-to-head meeting between two teams.
    """

    is_home: bool = field(default=False)
    home_goals: int = field(default=0)
    away_goals: int = field(default=0)


@dataclass
class HeadToHead:
    """
    Head-to-head history between two teams.

    ``home_wins``/``draws``/``away_wins`` are counted from the home team side.
    """

    meetings: list[Meeting] = field(default_factory=list)
    home_wins: int = field(default=0)
    draws: int = field(default=0)
    away_wins: int = field(default=0)


@dataclass
class TeamMatch:
    """
    A single recent match for one team.
    """

    is_home: bool = field(default=False)
    goals_for: int = field(default=0)
    goals_against: int = field(default=0)


@dataclass
class RecentRound:
    """
    One round of recent form: the home team match and the away team match.
    """

    home: TeamMatch = field(default_factory=TeamMatch)
    away: TeamMatch = field(default_factory=TeamMatch)


@dataclass
class RecentForm:
    """
    Recent match results for both teams, aligned by round.
    """

    rounds: list[RecentRound] = field(default_factory=list)


@dataclass
class OverUnder:
    """
    Over/under result distribution for a team.
    """

    rank: int = field(default=0)
    team: Team = field(default_factory=Team)
    played: int = field(default=0)
    over: int = field(default=0)
    push: int = field(default=0)
    under: int = field(default=0)
    over_pct: float = field(default=0.0)
    push_pct: float = field(default=0.0)
    under_pct: float = field(default=0.0)


@dataclass
class AsianHandicap:
    """
    Asian handicap result distribution for a team.
    """

    rank: int = field(default=0)
    team: Team = field(default_factory=Team)
    played: int = field(default=0)
    win: int = field(default=0)
    walk: int = field(default=0)
    lose: int = field(default=0)
    half_win: int = field(default=0)
    half_walk: int = field(default=0)
    half_lose: int = field(default=0)
    win_rate: float = field(default=0.0)
    walk_rate: float = field(default=0.0)
    lose_rate: float = field(default=0.0)


def parse_head_to_head(battle_raw: str) -> HeadToHead:
    """
    Parse the H2H ``battleData`` payload.

    Each meeting is ``is_home,home_goals,away_goals`` separated by ``|``.
    """
    meetings: list[Meeting] = []
    if not battle_raw:
        return HeadToHead()
    for part in battle_raw.split("|"):
        values = part.split(",")
        if len(values) < 3:
            continue
        meetings.append(
            Meeting(
                is_home=_to_int(values[0]) == 1,
                home_goals=_to_int(values[1]),
                away_goals=_to_int(values[2]),
            )
        )
    home_wins = sum(1 for m in meetings if m.home_goals > m.away_goals)
    draws = sum(1 for m in meetings if m.home_goals == m.away_goals)
    away_wins = sum(1 for m in meetings if m.home_goals < m.away_goals)
    return HeadToHead(
        meetings=meetings, home_wins=home_wins, draws=draws, away_wins=away_wins
    )


def _parse_team_match(raw: str) -> TeamMatch:
    values = raw.split(",")
    return TeamMatch(
        is_home=_to_int(_get(values, 0)) == 1,
        goals_for=_to_int(_get(values, 1)),
        goals_against=_to_int(_get(values, 2)),
    )


def parse_recent_form(last_raw: str) -> RecentForm:
    """
    Parse the recent-form ``lastMatchData`` payload.

    Rounds are separated by ``|``. Within each round the home team match is
    separated from the away team match by ``#``.
    """
    rounds: list[RecentRound] = []
    if not last_raw:
        return RecentForm()
    for part in last_raw.split("|"):
        halves = part.split("#")
        if len(halves) < 2:
            continue
        rounds.append(
            RecentRound(
                home=_parse_team_match(halves[0]),
                away=_parse_team_match(halves[1]),
            )
        )
    return RecentForm(rounds=rounds)


def parse_over_under(data: list, team_map: dict[int, Team]) -> list[OverUnder]:
    """
    Parse the ``BigSmallPan`` payload (over/under distribution).

    Row layout: ``[rank, team_id, played, over, push, under, over_pct,
    push_pct, under_pct]``.
    """
    rows: list[OverUnder] = []
    for raw in data:
        team_id = _to_int(_get(raw, 1))
        rows.append(
            OverUnder(
                rank=_to_int(_get(raw, 0)),
                team=team_map.get(team_id, Team(id=team_id, name=str(team_id))),
                played=_to_int(_get(raw, 2)),
                over=_to_int(_get(raw, 3)),
                push=_to_int(_get(raw, 4)),
                under=_to_int(_get(raw, 5)),
                over_pct=_to_float(_get(raw, 6)),
                push_pct=_to_float(_get(raw, 7)),
                under_pct=_to_float(_get(raw, 8)),
            )
        )
    return rows


def parse_asian_handicap(data: list, team_map: dict[int, Team]) -> list[AsianHandicap]:
    """
    Parse the ``LetgoalPan`` payload (Asian handicap distribution).

    Row layout: ``[rank, team_id, played, win, walk, lose, half_win,
    half_walk, half_lose, _, win_rate, walk_rate, lose_rate]``.
    """
    rows: list[AsianHandicap] = []
    for raw in data:
        team_id = _to_int(_get(raw, 1))
        rows.append(
            AsianHandicap(
                rank=_to_int(_get(raw, 0)),
                team=team_map.get(team_id, Team(id=team_id, name=str(team_id))),
                played=_to_int(_get(raw, 2)),
                win=_to_int(_get(raw, 3)),
                walk=_to_int(_get(raw, 4)),
                lose=_to_int(_get(raw, 5)),
                half_win=_to_int(_get(raw, 6)),
                half_walk=_to_int(_get(raw, 7)),
                half_lose=_to_int(_get(raw, 8)),
                win_rate=_to_float(_get(raw, 10)),
                walk_rate=_to_float(_get(raw, 11)),
                lose_rate=_to_float(_get(raw, 12)),
            )
        )
    return rows


@dataclass
class GoalTiming:
    """
    Goals scored by a team across ten-minute blocks of the match.
    """

    team: Team = field(default_factory=Team)
    intervals: list[int] = field(default_factory=list)


def parse_goal_timings(data: list, team_map: dict[int, Team]) -> list[GoalTiming]:
    """
    Parse the ``GoalInTimeList`` payload.

    Row layout: ``[team_id, g1..g9]`` where each ``g`` is the number of goals
    scored in a ten-minute block (0-10 through 81-90).
    """
    rows: list[GoalTiming] = []
    for raw in data:
        team_id = _to_int(_get(raw, 0))
        rows.append(
            GoalTiming(
                team=team_map.get(team_id, Team(id=team_id, name=str(team_id))),
                intervals=[_to_int(_get(raw, i)) for i in range(1, 10)],
            )
        )
    return rows


@dataclass
class MatchScore:
    """
    The live score and status of a match.

    ``state`` is Goaloo's match phase: -1 finished, 0 not started,
    1 first half, 2 half-time, 3 second half.
    """

    state: int = field(default=0)
    time: str = field(default="")
    home_score: int = field(default=0)
    away_score: int = field(default=0)
    half_home: int = field(default=0)
    half_away: int = field(default=0)
    injury_time: str = field(default="")
    status_text: str = field(default="")

    @property
    def state_name(self) -> str:
        """
        Human-readable name for ``state``.
        """
        return {
            -1: "Finished",
            0: "Not started",
            1: "First half",
            2: "Half-time",
            3: "Second half",
        }.get(self.state, "Unknown")


def parse_match_score(data: dict) -> MatchScore:
    """
    Parse the live match score payload (``soccerajax?type=11``).

    The score values live inside an HTML fragment in the ``html`` field.
    """
    if not data or data.get("ErrCode", 0) != 0:
        return MatchScore()
    inner = data.get("Data", {}) or {}
    raw_html = inner.get("html", "") or ""

    scores = re.findall(r"class='score'>(\d+)<", raw_html)
    halves = re.findall(r"title='Score 1st Half'>(\d+)-(\d+)<", raw_html)
    status = re.findall(r"state[^>]*>([^<]+)<", raw_html)
    if not status:
        status = re.findall(r"id='matchTime'>([^<]+)<", raw_html)

    return MatchScore(
        state=_to_int(inner.get("state", 0)),
        time=inner.get("time", "") or "",
        home_score=_to_int(scores[0]) if len(scores) > 0 else 0,
        away_score=_to_int(scores[1]) if len(scores) > 1 else 0,
        half_home=_to_int(halves[0][0]) if halves else 0,
        half_away=_to_int(halves[0][1]) if halves else 0,
        injury_time=inner.get("injuryTime", "") or "",
        status_text=status[0].strip() if status else "",
    )


@dataclass
class OddsLine:
    """
    A single odds line: home/over odds, the line, and away/under odds.
    """

    home: float = field(default=0.0)
    line: str = field(default="")
    away: float = field(default=0.0)


@dataclass
class LiveOdds:
    """
    The live odds of a match for a given bookmaker.
    """

    asian_handicap: OddsLine = field(default_factory=OddsLine)
    over_under: OddsLine = field(default_factory=OddsLine)
    euro: OddsLine = field(default_factory=OddsLine)
    corners: OddsLine = field(default_factory=OddsLine)


def _parse_odds_line(data: dict) -> OddsLine:
    if not data:
        return OddsLine()
    return OddsLine(
        home=_to_float(data.get("u")),
        line=str(data.get("g", "")) or "",
        away=_to_float(data.get("d")),
    )


def parse_live_odds(data: dict) -> LiveOdds:
    """
    Parse the live odds payload (``soccerajax?type=14&t=10``).

    The response carries one line per market under ``ah``, ``ou``, ``op``
    and ``corner`` keys, each with ``u`` (up/over), ``g`` (line) and
    ``d`` (down/under).
    """
    if not data or data.get("ErrCode", 0) != 0:
        return LiveOdds()
    inner = data.get("Data", {}) or {}
    return LiveOdds(
        asian_handicap=_parse_odds_line(inner.get("ah")),
        over_under=_parse_odds_line(inner.get("ou")),
        euro=_parse_odds_line(inner.get("op")),
        corners=_parse_odds_line(inner.get("corner")),
    )


_EVENT_RE = re.compile(
    r"\[(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),'([^']*)','([^']*)',(\d+),'([^']*)',(\d+),(\d+),'([^']*)'\]"
)


class EventType(Enum):
    """
    Known Goaloo match event codes.
    """

    GOAL = 1
    RED_CARD = 2
    YELLOW_CARD = 3
    SUBSTITUTION = 11


@dataclass
class MatchEvent:
    """
    A single match event: a goal, a card or a substitution.
    """

    type: int = field(default=0)
    minute: int = field(default=0)
    team_id: int = field(default=0)
    side: int = field(default=0)
    player_id: int = field(default=0)
    related_id: int = field(default=0)
    player: str = field(default="")
    related: str = field(default="")
    home_score: int = field(default=0)
    away_score: int = field(default=0)
    gif: str = field(default="")

    @property
    def type_name(self) -> str:
        """
        Human-readable name for ``type``.
        """
        try:
            return EventType(self.type).name.lower()
        except ValueError:
            return "unknown"


def parse_match_events(data_str: str) -> list[MatchEvent]:
    """
    Parse the match events payload (``soccerajax?type=15``).

    ``data_str`` is the JavaScript literal assigned to ``d_f`` by Goaloo's
    frontend. Each event is ``[type, minute, team_id, player_id,
    related_id, side, player, related, _, _, home_score, away_score, gif]``.
    """
    events: list[MatchEvent] = []
    for match in _EVENT_RE.finditer(data_str):
        events.append(
            MatchEvent(
                type=_to_int(match.group(1)),
                minute=_to_int(match.group(2)),
                team_id=_to_int(match.group(3)),
                player_id=_to_int(match.group(4)),
                related_id=_to_int(match.group(5)),
                side=_to_int(match.group(6)),
                player=match.group(7),
                related=match.group(8),
                home_score=_to_int(match.group(11)),
                away_score=_to_int(match.group(12)),
                gif=match.group(13),
            )
        )
    return events
