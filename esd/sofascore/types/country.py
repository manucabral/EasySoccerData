"""
Contains the country dataclass and the function to parse the country data.
"""

from dataclasses import dataclass, field


@dataclass
class Country:
    """
    A class to represent a country.
    """

    # alpha2: str = field(default="")
    # alpha3: str = field(default="")
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
        # alpha2=data.get("alpha2", ""),
        # alpha3=data.get("alpha3", ""),
        name=data.get("name", ""),
        slug=data.get("slug", ""),
    )
