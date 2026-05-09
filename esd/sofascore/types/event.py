"""
Contains the event data types and parsers (also known as matches).
"""

import time
from dataclasses import dataclass, field
from datetime import datetime

from .status import Status, parse_status
from .team import Team, parse_team
from .team_score import TeamScore, parse_team_score
from .tournament import Tournament, parse_tournament


@dataclass
class Season:
    """
    Season data class (also will be moved to season.py).
    """

    name: str
    year: str
    editor: bool
    season_coverage_info: dict
    id: int


@dataclass
class RoundInfo:
    """
    Round info data class.
    """

    round: int
    name: str
    cup_round_type: int


@dataclass
class TimeEvent:
    """
    Time event data class, half time, extra time, etc.
    """

    first_injury_time: int = 0
    second_injury_time: int = 0
    third_injury_time: int = 0
    quarter_injury_time: int = 0
    current_period_start: int = 0


@dataclass
class StatusTime:
    """
    Current status time data class.
    """

    initial: int = 0
    max: int = 0
    timestamp: int = 0
    extra: int = 0


@dataclass
class Event:
    """
    Event data class also known as match.
    """

    id: int = field(default=0)
    status: Status = field(default_factory=Status)
    home_team: Team = field(default_factory=Team)
    home_score: TeamScore = field(default_factory=TeamScore)
    away_team: Team = field(default_factory=Team)
    away_score: TeamScore = field(default_factory=TeamScore)
    time: TimeEvent = field(default_factory=TimeEvent)
    tournament: Tournament = field(default_factory=Tournament)
    status_time: StatusTime = field(default_factory=StatusTime)
    start_timestamp: int = field(default=0)
    slug: str = field(default="")
    round_info: RoundInfo = field(default_factory=RoundInfo)

    # some fields are not included
    # custom_id: int = field(default=0)
    # tournament: Tournament
    # season: Season
    # coverage: int = 0
    # final_result_only: bool = False
    # feed_locked: bool = False
    # changes: Optional[Dict] = field(default_factory=dict)
    # has_global_highlights: bool = False
    # is_editor: bool = False
    # detail_id: int = 1
    # crowdsourcingDataDisplayEnabled: bool = False

    @property
    def current_period_start(self) -> datetime:
        """
        Get the current period start time.

        Returns:
            datetime: The current period start time.
        """
        return datetime.fromtimestamp(self.time.current_period_start)

    @property
    def total_elapsed_minutes(self) -> int:
        """
        Get the total elapsed minutes.

        Returns:
            int: The total elapsed minutes.
        """
        return int((time.time() - self.start_timestamp) / 60)

    @property
    def current_elapsed_minutes(self) -> int:
        """
        Get the current elapsed period minutes.

        Returns:
            int: The current elapsed minutes.
        """
        return int((time.time() - self.time.current_period_start) / 60)


def parse_status_time(data: dict) -> StatusTime:
    """
    Parse the status time data.

    Args:
        data (dict): The status time data.

    Returns:
        StatusTime: The status time object.
    """
    return StatusTime(
        initial=data.get("initial", 0),
        max=data.get("max", 2700),  # 45 minutes
        extra=data.get("extra", 9),  # 9 minutes
        timestamp=data.get("timestamp", 0),
    )


def parse_time_event(data: dict) -> TimeEvent:
    """
    Parse the time event data.

    Args:
        data (dict): The time event data.

    Returns:
        TimeEvent: The time event object.
    """
    return TimeEvent(
        first_injury_time=data.get(
            "injuryTime1", 0
        ),  # example 4 -> aggregate 4 minutes
        second_injury_time=data.get("injuryTime2", 0),
        third_injury_time=data.get("injuryTime3", 0),
        quarter_injury_time=data.get("injuryTime4", 0),
        current_period_start=data.get("currentPeriodStartTimestamp", 0),
    )


def parse_round_info(data: dict) -> RoundInfo:
    """
    Parse the round info data.

    Args:
        data (dict): The round info data.

    Returns:
        RoundInfo: The round info object.
    """
    return RoundInfo(
        round=data.get("round", 0),
        name=data.get("name", "n/a"),
        cup_round_type=data.get("cupRoundType", 0),
    )


def parse_event(data: dict) -> Event:
    """
    Parse the event data.

    Args:
        data (dict): The event data.

    Returns:
        Event: The event object.
    """
    return Event(
        id=data.get("id"),
        start_timestamp=data.get("startTimestamp"),
        slug=data.get("slug"),
        # custom_id=data.get("customId"),
        # feed_locked=data.get("feedLocked"),
        # final_result_only=data.get("finalResultOnly"),
        # coverage=data.get("coverage"),
        tournament=parse_tournament(data.get("tournament", {})),
        time=parse_time_event(data.get("time", {})),
        status_time=parse_status_time(data.get("statusTime", {})),
        home_team=parse_team(data.get("homeTeam", {})),
        away_team=parse_team(data.get("awayTeam", {})),
        home_score=parse_team_score(data.get("homeScore", {})),
        away_score=parse_team_score(data.get("awayScore", {})),
        status=parse_status(data.get("status", {})),
        round_info=parse_round_info(data.get("roundInfo", {})),
    )


def parse_events(events: list[dict]) -> list[Event]:
    """
    Parse the events data.

    Args:
        events (list): The events data.

    Returns:
        list[Event]: The parsed events data.
    """
    return [parse_event(event) for event in events]
