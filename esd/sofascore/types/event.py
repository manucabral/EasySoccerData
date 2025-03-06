import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from .team import TeamSummary, parse_team_summary, TeamScore, parse_team_score


@dataclass
class Category:
    id: int
    country: Dict
    name: str
    slug: str
    flag: str


@dataclass
class UniqueTournament:
    name: str
    slug: str
    category: Category
    userCount: int
    hasPerformanceGraphFeature: bool
    id: int
    hasEventPlayerStatistics: bool
    displayInverseHomeAwayTeams: bool


@dataclass
class Tournament:
    name: str
    slug: str
    category: Category
    uniqueTournament: UniqueTournament
    priority: int
    id: int


@dataclass
class Season:
    name: str
    year: str
    editor: bool
    seasonCoverageInfo: Dict
    id: int


@dataclass
class RoundInfo:
    round: int
    name: str
    cup_round_type: int


@dataclass
class Status:
    code: int = 0
    description: str = "n/a"
    type: str = "n/a"


@dataclass
class TimeEvent:
    first_injury_time: int = 0
    second_injury_time: int = 0
    third_injury_time: int = 0
    quarter_injury_time: int = 0
    current_period_start: int = 0


@dataclass
class StatusTime:
    initial: int = 0
    max: int = 0
    timestamp: int = 0
    extra: int = 0


@dataclass
class Event:
    id: int = field(default=0)
    status: Status = field(default_factory=Status)
    home_team: TeamSummary = field(default_factory=TeamSummary)
    home_score: TeamScore = field(default_factory=TeamScore)
    away_team: TeamSummary = field(default_factory=TeamSummary)
    away_score: TeamScore = field(default_factory=TeamScore)
    time: TimeEvent = field(default_factory=TimeEvent)
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
    def current_period_start(self):
        return datetime.fromtimestamp(self.time.current_period_start)

    @property
    def total_elapsed_minutes(self):
        return int((time.time() - self.start_timestamp) / 60)

    @property
    def current_elapsed_minutes(self):
        return int((time.time() - self.time.current_period_start) / 60)


def parse_status_time(data: Dict) -> StatusTime:
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


def parse_time_event(data: Dict) -> TimeEvent:
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


def parse_round_info(data: Dict) -> RoundInfo:
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


def parse_status(data: Dict) -> Status:
    """
    Parse the status data.

    Args:
        data (dict): The status data.

    Returns:
        Status: The status object.
    """
    return Status(
        code=data.get("code", 0),
        description=data.get("description", "n/a"),
        type=data.get("type", "n/a"),
    )


def parse_events(events: List[Dict]) -> List[Event]:
    """
    Parse the events data.

    Args:
        events (list): The events data.

    Returns:
        list[Event]: The parsed events data.
    """
    return [
        Event(
            id=event.get("id"),
            start_timestamp=event.get("startTimestamp"),
            slug=event.get("slug"),
            # custom_id=event.get("customId"),
            # feed_locked=event.get("feedLocked"),
            # final_result_only=event.get("finalResultOnly"),
            # coverage=event.get("coverage"),
            time=parse_time_event(event.get("time", {})),
            status_time=parse_status_time(event.get("statusTime", {})),
            home_team=parse_team_summary(event.get("homeTeam", {})),
            away_team=parse_team_summary(event.get("awayTeam", {})),
            home_score=parse_team_score(event.get("homeScore", {})),
            away_score=parse_team_score(event.get("awayScore", {})),
            status=parse_status(event.get("status", {})),
            round_info=parse_round_info(event.get("roundInfo", {})),
        )
        for event in events
    ]
