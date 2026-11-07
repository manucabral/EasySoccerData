"""
The status of a match.
"""

from dataclasses import dataclass, field
from enum import Enum


class MatchStatus(Enum):
    """
    The match status.
    """

    NOT_STARTED = 1
    FINISHED = 3
    IN_PROGRESS = 2


@dataclass
class Status:
    """
    The status of a match.
    """

    value: MatchStatus = field(default=MatchStatus.NOT_STARTED)
    name: str = field(default=None)
    short_name: str = field(default=None)
    symbol_name: str = field(default=None)
    native_value: int = field(default=None)


def parse_status(data: dict) -> Status:
    """
    Parse the status data.
    """
    raw_value = data.get("enum", 0)
    try:
        status_value = MatchStatus(raw_value)
    except ValueError:
        status_value = MatchStatus.NOT_STARTED
    return Status(
        value=status_value,
        name=data.get("name"),
        short_name=data.get("short_name"),
        symbol_name=data.get("symbol_name"),
        native_value=raw_value,
    )
