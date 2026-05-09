"""
Player attributes dataclass and parser.
"""

from dataclasses import dataclass, field

from ...utils import current_year


@dataclass
class Attributes:
    """
    Attributes dataclass
    """

    attacking: int = field(default=0)
    technical: int = field(default=0)
    tactical: int = field(default=0)
    defending: int = field(default=0)
    creativity: int = field(default=0)
    year: int = field(default_factory=current_year)
    position: str = field(default=None)


@dataclass
class PlayerAttributes:
    """
    Player attributes dataclass
    """

    average: Attributes = field(default=None)
    overview: list[Attributes] = field(default=list)


def parse_attributes(data: dict) -> Attributes:
    """
    Parse attributes data.

    Args:
        data (dict): Attributes data.

    Returns:
        Attributes: Attributes dataclass.
    """
    return Attributes(
        attacking=data.get("attacking", 0),
        technical=data.get("technical", 0),
        tactical=data.get("tactical", 0),
        defending=data.get("defending", 0),
        creativity=data.get("creativity", 0),
        position=data.get("position", None),
        year=current_year(-data.get("yearShift", 0)),
    )


def parse_player_attributes(data: dict) -> PlayerAttributes:
    """
    Parse player data attributes.

    Args:
        data (dict): Player data attributes.

    Returns:
        PlayerAttributes: Player attributes
    """
    average_attr = data.get("averageAttributeOverviews", {})
    overviews_attr = data.get("playerAttributeOverviews", [])
    if not average_attr or not overviews_attr:
        return PlayerAttributes()
    return PlayerAttributes(
        average=parse_attributes(average_attr[0]),
        overview=[parse_attributes(attr) for attr in overviews_attr],
    )
