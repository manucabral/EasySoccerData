"""
Promiedos league metadata and parser.
"""

from dataclasses import dataclass, field


@dataclass
class League:
    """
    The league of a match.
    """

    name: str = field(default=None)
    id: str = field(default=None)
    slug: str = field(default=None)
    country_id: str = field(default="")
    country_name: str = field(default="")
    is_international: bool = field(default=False)


def parse_league(data: dict) -> League:
    """
    Parse the league data.
    """
    return League(
        name=data.get("name", None),
        id=data.get("id", None),
        slug=data.get("url_name", None),
        country_id=data.get("country_id", None),
        country_name=data.get("country_name", None),
        is_international=data.get("is_international", False),
    )
