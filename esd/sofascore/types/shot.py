"""
Shot dataclass and parser.
"""

from dataclasses import dataclass, field

from .player import Player, parse_player


@dataclass
class Shot:
    """
    Shot dataclass.
    """

    player: Player = field(default=None)
    is_home: bool = field(default=False)
    type: str = field(default=None)
    situation: str = field(default=None)
    body_part: str = field(default=None)
    goal_mouth_location: str = field(default=None)
    xg: float = field(default=None)
    xg_got: float = field(default=None)
    time: int = field(default=None)
    time_in_seconds: int = field(default=None)


def parse_shot(data: dict) -> Shot:
    """
    Parse shot data.

    Args:
        data (dict): Shot data.

    Returns:
        Shot: Shot dataclass
    """
    return Shot(
        player=parse_player(data.get("player", {})),
        is_home=data.get("isHome", False),
        type=data.get("shotType", None),
        situation=data.get("situation", None),
        body_part=data.get("bodyPart", None),
        goal_mouth_location=data.get("goalMouthLocation", None),
        xg=data.get("xg", None),
        xg_got=data.get("xgot", None),
        time=data.get("time", None),
        time_in_seconds=data.get("timeSeconds", None),
    )


def parse_shots(data: dict) -> list[Shot]:
    """
    Parse shots data.

    Args:
        data (dict): Shots data.

    Returns:
        list[Shot]: List of Shot dataclass
    """
    return [parse_shot(shot) for shot in data]
