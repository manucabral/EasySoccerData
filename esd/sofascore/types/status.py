"""
Status types for SofaScore.
"""

from dataclasses import dataclass, field
from enum import Enum


class StatusType(Enum):
    """
    Status type enum.
    """

    UNKNOWN = "unknown"
    NOT_STARTED = "notstarted"
    IN_PROGRESS = "inprogress"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"
    FINISHED = "finished"


@dataclass
class Status:
    """
    Status data class.
    """

    type: StatusType = StatusType.UNKNOWN
    """
    The status type enum.
    """
    description: str = field(default="No description")
    """
    Additional status description (e.g. "1st half"...).
    """


def get_status_type(code: int) -> StatusType:
    """
    Get the status type from the code.
    """

    try:
        return StatusType(code)
    except ValueError:
        return StatusType.UNKNOWN


def parse_status(data: dict) -> Status:
    """
    Parse status data.
    """
    return Status(
        description=data.get("description"),
        type=get_status_type(data.get("type")),
    )
