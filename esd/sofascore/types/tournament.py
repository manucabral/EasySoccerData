"""
Sofascore tournament metadata and parsers.
"""

from dataclasses import dataclass, field


@dataclass
class Tournament:
    """Tournament metadata reported by Sofascore."""

    id: int = field(default=None)
    name: str = field(default=None)
    slug: str = field(default=None)


def parse_tournament(data: dict) -> Tournament:
    """
    Parse tournament data.

    Args:
        data (dict): Tournament data.

    Returns:
        Tournament: Tournament dataclass
    """
    return Tournament(
        id=data.get("id", None),
        name=data.get("name", None),
        slug=data.get("slug", None),
    )


def parse_tournaments(data: dict) -> list[Tournament]:
    """
    Parse tournament data.

    Args:
        data (dict): Tournament data.

    Returns:
        list[Tournament]: List of Tournament dataclass
    """
    return [parse_tournament(tournament) for tournament in data]
