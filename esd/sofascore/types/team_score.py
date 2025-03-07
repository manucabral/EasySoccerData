from dataclasses import dataclass, field
from typing import Dict


@dataclass
class TeamScore:
    current: int = field(default=0)
    # display: int = field(default=0)
    first_period: int = field(default=0)  # 1st half
    second_period: int = field(default=0)  # 2nd half
    # normaltime: int = field(default=0) # Full time


def parse_team_score(data: Dict) -> TeamScore:
    """
    Parse the team score data.

    Args:
        data (dict): The team score data.

    Returns:
        Score: The team score object.
    """
    return TeamScore(
        current=data.get("current", 0),
        # display=data.get("display", 0),
        first_period=data.get("period1", 0),
        second_period=data.get("period2", 0),
        # normaltime=data.get("normaltime", 0),
    )
