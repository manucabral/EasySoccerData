"""
This module contains the dataclass for the incident object.
"""

from dataclasses import dataclass, field
from enum import Enum

from .player import Player, parse_player


class IncidentType(Enum):
    """
    Enum for the incident type.
    """

    PERIOD = "period"
    GOAL = "goal"
    SUBSTITUTION = "substitution"
    CARD = "card"
    INJURY_TIME = "injuryTime"
    PENALTY = "inGamePenalty"
    PENALTY_SHOOTOUT = "penaltyShootout"
    VAR_DECISION = "varDecision"
    UNKNOWN = "unknown"


@dataclass
class Incident:
    """
    Main incident dataclass.
    """

    # id: int = d
    # length: int = None
    time: int = field(default=None)
    reversed_period_time: int = field(default=None)
    type: str = field(default=None)
    home_score: int = field(default=None)
    away_score: int = field(default=None)
    is_home: bool = field(default=False)
    details: str = field(default=None)
    added_time: int = field(default=None)
    text: str = field(default=None)
    is_live: bool = field(default=False)
    time_in_seconds: int = field(default=None)
    reversed_period_time_in_seconds: int = field(default=None)
    reason: str = field(default=None)
    rescinded: bool = field(default=False)
    injury: bool = field(default=False)
    player: Player = field(default=None)
    assist_player: Player = field(default=None)
    player_in: Player = field(default=None)
    player_out: Player = field(default=None)


def parse_incident_type(type_str: str) -> IncidentType:
    """
    Parse the incident type.
    """
    try:
        return IncidentType(type_str)
    except ValueError:
        return IncidentType.UNKNOWN


def parse_incident(data: dict) -> Incident:
    """
    Parse the incident data.
    """
    return Incident(
        time=data.get("time"),
        reversed_period_time=data.get("reversedPeriodTime"),
        type=parse_incident_type(data.get("incidentType")),
        home_score=data.get("homeScore"),
        away_score=data.get("awayScore"),
        is_home=data.get("isHome", False),
        details=data.get("incidentClass"),
        added_time=data.get("addedTime"),
        text=data.get("text"),
        is_live=data.get("isLive", False),
        time_in_seconds=data.get("timeSeconds"),
        reversed_period_time_in_seconds=data.get("reversedPeriodTimeSeconds"),
        reason=data.get("reason"),
        rescinded=data.get("rescinded", False),
        injury=data.get("injury", False),
        player=parse_player(data.get("player", {})),
        assist_player=parse_player(data.get("assist1", {})),
        player_in=parse_player(data.get("playerIn", {})),
        player_out=parse_player(data.get("playerOut", {})),
    )


def parse_incidents(data: list) -> list:
    """
    Parse the incidents data.
    """
    return [parse_incident(incident) for incident in data]
