"""
This module defines classes and functions for parsing and representing match events.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Union


class EventType(Enum):
    """
    Enumeration of possible event types in a match.
    """

    GOAL = 1
    PENALTY = 7
    HIT_WOODWORK = 10
    YELLOW_CARD = 4
    SUBSTITUTION = 15
    PENALTY_SCORED = 3
    PENALTY_NOT_SCORED = 17


@dataclass
class Substitution:
    """
    Represents a substitution event in a match.
    """

    player_in: str
    player_out: str


@dataclass
class EventItem:
    """
    Represents a single event that occurred during a match.
    """

    time: str
    is_home: bool
    details: Optional[Union[str, Substitution]]
    event_type: EventType


@dataclass
class MatchEvents:
    """
    Aggregates all events that occurred during the different phases of a match.
    """

    first_half: list[EventItem] = field(default_factory=list)
    second_half: list[EventItem] = field(default_factory=list)
    extra_time: list[EventItem] = field(default_factory=list)
    penalties: list[EventItem] = field(default_factory=list)


def get_event_type_by_id(event_id: int) -> Optional[EventType]:
    """
    Retrieves the EventType corresponding to a given event ID.
    """
    try:
        return EventType(event_id)
    except ValueError:
        return None


def parse_event_data(event_data: dict) -> EventItem:
    """
    Parses a single event data dictionary into an EventItem object.

    Args:
        event_data (dict): The dictionary containing event information.

    Returns:
        EventItem: The parsed EventItem object.
    """
    event_type_value = event_data.get("type")
    event_type = get_event_type_by_id(event_type_value)
    texts = event_data.get("texts") or []

    if event_type is None:
        value = texts[0] if texts else None
    elif event_type == EventType.SUBSTITUTION:
        value = Substitution(
            player_in=texts[0] if len(texts) > 0 else None,
            player_out=texts[1] if len(texts) > 1 else None,
        )
    else:
        value = texts[0] if texts else None

    return EventItem(
        time=event_data.get("time"),
        is_home=event_data.get("team") == 1,
        details=value,
        event_type=event_type,
    )


def parse_event_items(data: dict) -> list[EventItem]:
    """
    Parses a list of event data dictionaries into a list of EventItem objects.
    """
    events = []
    for row in data.get("rows", []):
        for event_data in row.get("events", []):
            events.append(parse_event_data(event_data))
    return events


def parse_match_events(data: list[dict]) -> MatchEvents:
    """
    Parses match events data into a MatchEvents object.

    Args:
        data (list[dict]): A list of dictionaries, each representing events from a match phase.

    Returns:
        MatchEvents: An object containing all parsed match events.
    """
    length = len(data)
    return MatchEvents(
        first_half=parse_event_items(data[0]) if length > 0 else [],
        second_half=parse_event_items(data[1]) if length > 1 else [],
        extra_time=parse_event_items(data[2]) if length > 2 else [],
        penalties=parse_event_items(data[3]) if length > 3 else [],
    )
