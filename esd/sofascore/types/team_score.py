"""Sofascore team scores by period and parser."""

from dataclasses import dataclass, field


@dataclass
class TeamScore:
    """A team's current score and available period scores."""

    current: int = field(default=0)
    first_period: int = field(default=0)  # 1st half
    second_period: int = field(default=0)  # 2nd half


def parse_team_score(data: dict) -> TeamScore:
    """
    Parse the team score data.

    Args:
        data (dict): The team score data.

    Returns:
        TeamScore: Parsed current and period scores.
    """
    return TeamScore(
        current=data.get("current", 0),
        first_period=data.get("period1", 0),
        second_period=data.get("period2", 0),
    )
