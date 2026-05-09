"""
SofaScore Standing dataclass.
"""

from dataclasses import dataclass, field

from .team import Team, parse_team
from .tournament import Tournament, parse_tournament


@dataclass
class StandingItem:
    """
    StandingItem dataclass
    """

    id: int = field(default=0)
    team: Team = field(default=None)
    descriptions: list = field(default_factory=list)
    promotion: dict = field(default_factory=dict)
    position: int = field(default=0)
    matches: int = field(default=0)
    wins: int = field(default=0)
    scores_for: int = field(default=0)
    scores_against: int = field(default=0)
    losses: int = field(default=0)
    draws: int = field(default=0)
    points: int = field(default=0)
    score_diff_formatted: str = field(default="")


def parse_standing_item(data: dict) -> StandingItem:
    """
    Parse standing item data.

    Args:
        data (dict): Standing item data.

    Returns:
        StandingItem: Standing item dataclass
    """
    return StandingItem(
        id=data.get("id", 0),
        team=parse_team(data.get("team", {})),
        descriptions=data.get("descriptions", []),
        promotion=data.get("promotion", {}),
        position=data.get("position", 0),
        matches=data.get("matches", 0),
        wins=data.get("wins", 0),
        scores_for=data.get("scoresFor", 0),
        scores_against=data.get("scoresAgainst", 0),
        losses=data.get("losses", 0),
        draws=data.get("draws", 0),
        points=data.get("points", 0),
        score_diff_formatted=data.get("scoreDiffFormatted", ""),
    )


def parse_standing_items(data: dict) -> list[StandingItem]:
    """
    Parse standing item data.

    Args:
        data (dict): Standing item data.

    Returns:
        list[StandingItem]: List of Standing item dataclass
    """
    return [parse_standing_item(standing_item) for standing_item in data]


@dataclass
class Standing:
    """Standing dataclass"""

    id: int = field(default=None)
    name: str = field(default=None)
    tournament: Tournament = field(default=None)
    last_updated: int = field(default=None)
    items: list[StandingItem] = field(default_factory=list)
    # description: str = field(default=None)


def parse_standing(data: dict) -> Standing:
    """
    Parse standing data.

    Args:
        data (dict): Standing data.

    Returns:
        Standing: Standing dataclass
    """
    return Standing(
        id=data.get("id", None),
        name=data.get("name", None),
        tournament=parse_tournament(data.get("tournament", {})),
        last_updated=data.get("updatedAtTimestamp", None),
        items=parse_standing_items(data.get("rows", [])),
        # description=data.get("description", None),
    )


def parse_standings(data: dict) -> list[Standing]:
    """
    Parse standing data.

    Args:
        data (dict): Standing data.

    Returns:
        list[Standing]: List of Standing dataclass
    """
    return [parse_standing(standing) for standing in data]
