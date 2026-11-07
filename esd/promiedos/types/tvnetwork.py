"""
Promiedos match broadcasters and parser.
"""

from dataclasses import dataclass, field


@dataclass
class TVNetwork:
    """
    The TV network of a match.
    """

    id: str = field(default="")
    name: str = field(default="")


def parse_tv_network(data: dict) -> TVNetwork:
    """
    Parse the TV network data.
    """
    return TVNetwork(id=data.get("id", ""), name=data.get("name", ""))
