"""
This module contains the Match dataclass and its parser.
"""

from dataclasses import dataclass, field
from datetime import datetime

from .league import League
from .match_events import MatchEvents, parse_match_events
from .match_stats import MatchStats
from .odds import MainOdds, parse_main_odds
from .players import Players
from .scores import (
    GlobalScores,
    Penalties,
    Scores,
    parse_global_scores,
    parse_penalties,
    parse_scores,
)
from .status import Status, parse_status
from .team import Team, parse_team
from .tvnetwork import TVNetwork, parse_tv_network


@dataclass
class Match:
    """
    The match data.
    """

    id: str = field(default=None)
    stage_round_name: str = field(default=None)
    winner: Team = field(default=None)
    home_team: Team = field(default_factory=Team)
    away_team: Team = field(default_factory=Team)
    scores: Scores = field(default_factory=Scores)
    penalties: Scores = field(default_factory=Penalties)
    global_scores: Scores = field(default_factory=GlobalScores)
    slug: str = field(default="")
    status: Status = field(default_factory=Status)
    start_time: float = field(default=0.0)
    current_time: int = field(default=0)
    time_to_display: str = field(default=None)
    time_status_to_display: str = field(default=None)
    tv_networks: list[TVNetwork] = field(default_factory=list)
    main_odds: MainOdds = field(default_factory=MainOdds)
    league: League = field(default_factory=League)
    players: Players = field(default_factory=Players)
    stats: MatchStats = field(default_factory=MatchStats)
    events: MatchEvents = field(default_factory=MatchEvents)


def parse_match(data: dict) -> Match:
    """
    Parse the match data.
    """
    teams_data = data.get("teams", [])
    home_team = parse_team(teams_data[0])
    away_team = parse_team(teams_data[1])
    winner_team = (
        home_team
        if data.get("winner") == 1
        else away_team if data.get("winner") == 2 else None
    )
    scores_data = data.get("scores", [])
    tv_networks_data = data.get("tv_networks", [])
    date_str = data.get("start_time", "01-01-1970 00:00")
    dt = datetime.strptime(date_str, "%d-%m-%Y %H:%M")

    return Match(
        id=data.get("id"),
        stage_round_name=data.get("stage_round_name"),
        winner=winner_team,
        scores=parse_scores(scores_data),
        penalties=parse_penalties(data.get("penalties", [])),
        global_scores=parse_global_scores(data.get("agg_scores", [])),
        home_team=home_team,
        away_team=away_team,
        slug=data.get("url_name", ""),
        status=parse_status(data.get("status", {})),
        start_time=dt.timestamp(),
        current_time=data.get("game_time", 0),
        time_to_display=data.get("game_time_to_display", ""),
        time_status_to_display=data.get("game_time_status_to_display", ""),
        tv_networks=[parse_tv_network(tv) for tv in tv_networks_data],
        main_odds=parse_main_odds(data.get("main_odds", {})),
        events=parse_match_events(data.get("events", [])),
    )
