from dataclasses import dataclass, field
from typing import List, Optional, Dict
from .country import Country, parse_country


@dataclass
class Manager:
    id: int = field(default=0)
    country: Country = field(default_factory=Country)
    name: str = field(default=None)
    slug: str = field(default=None)
    short_name: str = field(default=None)


def parse_manager(data: Dict) -> Manager:
    """
    Parse the manager data.

    Args:
        data (dict): The manager data.

    Returns:
        Manager: The manager object.
    """
    return Manager(
        id=data.get("id", 0),
        country=parse_country(data.get("country", {})),
        name=data.get("name"),
        slug=data.get("slug"),
        short_name=data.get("shortName"),
    )
