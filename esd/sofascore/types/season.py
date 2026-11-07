"""
Sofascore tournament seasons and parsers.
"""

from dataclasses import dataclass, field


@dataclass
class Season:
    """A tournament season's name, period and source ID."""

    id: int = field(default=None)
    name: str = field(default=None)
    period: int = field(default=None)


def parse_season(data: dict) -> Season:
    """
    Parse season data.

    Args:
        data (dict): Season data.

    Returns:
        Season: Season dataclass
    """
    return Season(
        id=data.get("id", None),
        name=data.get("name", None),
        period=data.get("year", None),
    )


def parse_seasons(data: dict) -> list[Season]:
    """
    Parse seasons data.

    Args:
        data (dict): Seasons data.

    Returns:
        list[Season]: List of Season dataclass
    """
    return [parse_season(season) for season in data]
