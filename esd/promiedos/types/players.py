"""
Contains all player types for a match.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PitchLocation:
    """
    The pitch location.
    """

    x: float = field(default=0.0)
    y: float = field(default=0.0)


@dataclass
class MissingDetails:
    """
    The missing details.
    """

    type: int = field(default=0)
    reason: str = field(default="")
    will_play_status: int = field(default=0)
    will_play: str = field(default="")


@dataclass
class Player:
    """
    The player.
    """

    jersey_num: int = field(default=0)
    name: str = field(default="")
    player_short_name: str = field(default="")
    position: str = field(default="")
    formation_position: str = field(default="")
    country_id: str = field(default="")
    pitch_location: PitchLocation = field(default_factory=PitchLocation)
    age: int = field(default=0)
    height: str = field(default="")
    missing_details: Optional[MissingDetails] = None


@dataclass
class LineupTeam:
    """
    The lineup team.
    """

    status: str = field(default=None)
    formation: str = field(default=None)
    team_num: int = field(default=0)
    starting: list[Player] = field(default_factory=list)
    bench: list[Player] = field(default_factory=list)
    staff: list[Player] = field(default_factory=list)


@dataclass
class Lineups:
    """
    The lineups.
    """

    # support_visual_lineups: bool = field(default=False)
    away_team: LineupTeam = field(default_factory=LineupTeam)
    home_team: LineupTeam = field(default_factory=LineupTeam)


@dataclass
class Players:
    """
    Players additional data.
    """

    lineups: Lineups = field(default_factory=Lineups)
    missing_players: list[list[Player]] = field(default_factory=list)


def parse_pitch_location(data: dict) -> PitchLocation:
    """
    Parse the pitch location data.
    """
    return PitchLocation(x=data.get("x", 0.0), y=data.get("y", 0.0))


def parse_missing_details(data: dict) -> MissingDetails:
    """
    Parse the missing details data.
    """
    return MissingDetails(
        type=data.get("type", 0),
        reason=data.get("reason", ""),
        will_play_status=data.get("will_play_status", 0),
        will_play=data.get("will_play", ""),
    )


def parse_lineup_team(data: dict) -> LineupTeam:
    """
    Parse the lineup team data.
    """
    starting = [parse_player(p) for p in data.get("starting", [])]
    bench = [parse_player(p) for p in data.get("bench", [])]
    staff = [parse_player(p) for p in data.get("staff", [])]
    return LineupTeam(
        status=data.get("status", ""),
        formation=data.get("formation", ""),
        team_num=data.get("team_num", 0),
        starting=starting,
        bench=bench,
        staff=staff,
    )


def parse_lineups(data: dict) -> Lineups:
    """
    Parse the lineups data.
    """
    teams = data.get("teams", []) or []
    home = parse_lineup_team(teams[0]) if len(teams) > 0 else LineupTeam()
    away = parse_lineup_team(teams[1]) if len(teams) > 1 else LineupTeam()
    return Lineups(home_team=home, away_team=away)


def parse_player(data: dict) -> Player:
    """
    Parse the player data.
    """
    pitch_location = (
        parse_pitch_location(data["pitch_location"])
        if "pitch_location" in data
        else PitchLocation()
    )
    missing_details = (
        parse_missing_details(data["missing_details"])
        if "missing_details" in data
        else None
    )

    return Player(
        jersey_num=data.get("jersey_num", 0),
        name=data.get("name", ""),
        player_short_name=data.get("player_short_name", ""),
        position=data.get("position", ""),
        formation_position=data.get("formation_position", ""),
        country_id=data.get("country_id", ""),
        pitch_location=pitch_location,
        age=data.get("age", 0),
        height=data.get("height", ""),
        missing_details=missing_details,
    )


def parse_missing_players(data: list) -> list[list[Player]]:
    """
    Parse the missing players data.
    """
    return [[parse_player(player) for player in group] for group in data]


def parse_players(data: dict) -> Players:
    """
    Parse the players data.
    """
    if not data:
        return Players()
    lineups = parse_lineups(data.get("lineups", {}))
    missing = parse_missing_players(data.get("missing_players", []))
    return Players(lineups=lineups, missing_players=missing)
