"""Sofascore country metadata and parser."""

from dataclasses import dataclass, field


@dataclass
class Country:
    """
    Country metadata reported by Sofascore.
    """

    name: str = field(default="")
    slug: str = field(default="")


def parse_country(data: dict) -> Country:
    """
    Parse the country data.

    Args:
        data (dict): The country data.

    Returns:
        Country: The country object.
    """
    return Country(
        name=data.get("name", ""),
        slug=data.get("slug", ""),
    )
