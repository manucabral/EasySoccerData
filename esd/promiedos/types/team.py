"""
This module contains the Team class and its parser.
"""

from dataclasses import dataclass, field

from .color import Color, parse_color


@dataclass
class TeamGoal:
    """
    The goals of a team.
    """

    full_name: str = field(default="")
    short_name: str = field(default="")
    time: int = field(default=0.0)
    time_to_display: str = field(default="")
    is_penalty: bool = field(default=False)


def parse_team_goal(data: dict) -> TeamGoal:
    """
    Parse the team goal data.
    """
    goal_type = data.get("goal_type", None)
    return TeamGoal(
        full_name=data.get("player_name"),
        short_name=data.get("player_sname"),
        time=int(data.get("time", 0.0)),
        time_to_display=data.get("time_to_display", ""),
        is_penalty=goal_type == "Pen",
    )


@dataclass
class Team:
    """
    The team of a match.
    """

    id: str = field(default=None)
    name: str = field(default=None)
    slug: str = field(default=None)
    short_name: str = field(default=None)
    country_id: str = field(default=None)
    color: Color = field(default_factory=Color)
    red_cards: int = field(default=0)
    goals: list[TeamGoal] = field(default_factory=list)


def parse_team(data: dict) -> Team:
    """
    Parse the team data.
    """
    return Team(
        name=data.get("name"),
        short_name=data.get("short_name"),
        slug=data.get("url_name"),
        id=data.get("id"),
        country_id=data.get("country_id"),
        color=parse_color(data.get("colors", {})),
        red_cards=data.get("red_cards", 0),
        goals=[parse_team_goal(goal) for goal in data.get("goals", [])],
    )
