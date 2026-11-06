"""
365Scores game, lineup and event dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Competitor:
    """
    A team participating in a 365Scores match.
    """

    id: int = None
    name: str = None
    short_name: str = None
    symbolic_name: str = None
    score: int | None = None
    red_cards: int = 0
    is_winner: bool = False
    color: str = None
    away_color: str = None
    country_id: int = None


@dataclass
class GameEvent:
    """
    An incident (goal, card, substitution) inside a 365Scores match.
    """

    competitor_id: int = None
    player_id: int = None
    player_name: str = None
    minute: int = 0
    added_time: int = 0
    time_display: str = None
    event_type_id: int = None
    event_type_name: str = None
    sub_type_name: str = None
    is_major: bool = False


@dataclass
class PlayerStat:
    """
    A single statistic entry for a player in a match lineup.
    """

    type_id: int = None
    name: str = None
    short_name: str = None
    value: str = None


@dataclass
class LineupPlayer:
    """
    A player in a match starting XI or bench.
    """

    id: int = None
    athlete_id: int = None
    name: str = None
    short_name: str = None
    jersey_number: int = None
    status_text: str = None
    position: str = None
    rating: float | None = None
    heatmap_url: str = None
    stats: list[PlayerStat] = field(default_factory=list)


@dataclass
class TeamLineup:
    """
    Formation and player list for one side in a match.
    """

    status: str = None
    formation: str = None
    starters: list[LineupPlayer] = field(default_factory=list)
    substitutes: list[LineupPlayer] = field(default_factory=list)


@dataclass
class Game:
    """
    A 365Scores match.
    """

    id: int = None
    competition_id: int = None
    competition_name: str = None
    season_num: int = None
    stage_num: int = None
    round_num: int = None
    round_name: str = None
    start_time: str = None
    status_group: int = None
    status_text: str = None
    short_status_text: str = None
    game_time: float | None = None
    game_time_display: str = None
    home_team: Competitor = field(default_factory=Competitor)
    away_team: Competitor = field(default_factory=Competitor)
    events: list[GameEvent] = field(default_factory=list)
    home_lineup: TeamLineup | None = None
    away_lineup: TeamLineup | None = None


def parse_competitor(data: dict) -> Competitor:
    """
    Parse a competitor dictionary.
    """
    if not data:
        return Competitor()
    raw_score = data.get("score")
    score = (
        int(raw_score)
        if isinstance(raw_score, (int, float)) and raw_score >= 0
        else None
    )
    return Competitor(
        id=data.get("id"),
        name=data.get("name"),
        short_name=data.get("shortName") or data.get("name"),
        symbolic_name=data.get("symbolicName"),
        score=score,
        red_cards=int(data.get("redCards", 0) or 0),
        is_winner=bool(data.get("isWinner", False)),
        color=data.get("color"),
        away_color=data.get("awayColor"),
        country_id=data.get("countryId"),
    )


def _parse_lineup(comp_data: dict, member_lookup: dict[int, dict]) -> TeamLineup | None:
    lineup_data = comp_data.get("lineups") if isinstance(comp_data, dict) else None
    if not isinstance(lineup_data, dict):
        return None
    starters: list[LineupPlayer] = []
    substitutes: list[LineupPlayer] = []
    for item in lineup_data.get("members", []) or []:
        pid = item.get("id")
        meta = member_lookup.get(pid, {})
        pos_data = item.get("position") or {}
        stats = [
            PlayerStat(
                type_id=s.get("type"),
                name=s.get("name"),
                short_name=s.get("shortName") or s.get("name"),
                value=str(s.get("value", "")),
            )
            for s in item.get("stats", []) or []
        ]
        raw_ranking = item.get("ranking")
        rating = (
            float(raw_ranking)
            if isinstance(raw_ranking, (int, float)) and raw_ranking > 0
            else None
        )
        player = LineupPlayer(
            id=pid,
            athlete_id=meta.get("athleteId"),
            name=meta.get("name"),
            short_name=meta.get("shortName") or meta.get("name"),
            jersey_number=meta.get("jerseyNumber"),
            status_text=item.get("statusText"),
            position=pos_data.get("name") or pos_data.get("shortName"),
            rating=rating,
            heatmap_url=item.get("heatMap"),
            stats=stats,
        )
        if item.get("status") == 1:
            starters.append(player)
        else:
            substitutes.append(player)

    return TeamLineup(
        status=lineup_data.get("status"),
        formation=lineup_data.get("formation"),
        starters=starters,
        substitutes=substitutes,
    )


def parse_game(data: dict) -> Game:
    """
    Parse a single 365Scores game object.
    """
    if not data:
        return Game()

    member_lookup: dict[int, dict] = {
        m["id"]: m for m in data.get("members", []) or [] if "id" in m
    }

    events: list[GameEvent] = []
    for ev in data.get("events", []) or []:
        ev_type = ev.get("eventType") or {}
        pid = ev.get("playerId")
        player_meta = member_lookup.get(pid, {})
        raw_time = ev.get("gameTime")
        events.append(
            GameEvent(
                competitor_id=ev.get("competitorId"),
                player_id=pid,
                player_name=player_meta.get("name"),
                minute=int(raw_time) if isinstance(raw_time, (int, float)) else 0,
                added_time=int(ev.get("addedTime", 0) or 0),
                time_display=ev.get("gameTimeDisplay"),
                event_type_id=ev_type.get("id"),
                event_type_name=ev_type.get("name"),
                sub_type_name=ev_type.get("subTypeName"),
                is_major=bool(ev.get("isMajor", False)),
            )
        )

    home_raw = data.get("homeCompetitor") or {}
    away_raw = data.get("awayCompetitor") or {}
    raw_game_time = data.get("gameTime")
    game_time = (
        float(raw_game_time)
        if isinstance(raw_game_time, (int, float)) and raw_game_time >= 0
        else None
    )

    return Game(
        id=data.get("id"),
        competition_id=data.get("competitionId"),
        competition_name=data.get("competitionDisplayName"),
        season_num=data.get("seasonNum"),
        stage_num=data.get("stageNum"),
        round_num=data.get("roundNum"),
        round_name=data.get("roundName"),
        start_time=data.get("startTime"),
        status_group=data.get("statusGroup"),
        status_text=data.get("statusText"),
        short_status_text=data.get("shortStatusText"),
        game_time=game_time,
        game_time_display=data.get("gameTimeDisplay"),
        home_team=parse_competitor(home_raw),
        away_team=parse_competitor(away_raw),
        events=events,
        home_lineup=_parse_lineup(home_raw, member_lookup),
        away_lineup=_parse_lineup(away_raw, member_lookup),
    )


def parse_games(data: dict) -> list[Game]:
    """
    Parse a list of games from an ``allscores`` payload.
    """
    if not data:
        return []
    return [parse_game(g) for g in data.get("games", []) or []]
