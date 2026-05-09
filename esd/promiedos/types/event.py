"""
This module contains the Event class for Promiedos.
"""

from dataclasses import dataclass, field

from .league import League, parse_league
from .match import Match, parse_match


@dataclass
class Event:
    """
    The event of a match.
    """

    date: str = field(default=None)
    league: League = field(default_factory=League)
    matches: list[Match] = field(default_factory=list)


def parse_event(date: str, league_data: dict) -> Event:
    """
    Parse the event data.

    Args:
        date (str): The date of the event.
        league_data (dict): The league data.

    Returns:
        Event: The event data.
    """
    games = league_data.pop("games", [])
    league = parse_league(league_data)
    matches = [parse_match(game) for game in games]
    return Event(date=date, league=league, matches=matches)


def parse_events(date: str, data: dict) -> list[Event]:
    """
    Parse the events data.

    Args:
        date (str): The date of the events.
        data (dict): The events data.

    Returns:
        list[Event]: The events data.
    """
    return [parse_event(date, league) for league in data]
