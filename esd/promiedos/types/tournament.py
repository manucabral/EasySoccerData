"""
This module contains the
"""

from dataclasses import dataclass, field

from .league import League, parse_league


@dataclass
class Stage:
    """
    The tournament filter class.
    """

    id: str = field(default=None)
    name: str = field(default=None)
    selected: bool = field(default=False)


@dataclass
class Tournament:
    """
    The tournament class.
    """

    league: League = field(default_factory=None)
    stages: list[Stage] = field(default_factory=list)

    def current_stage(self) -> Stage:
        """
        Get the current stage of the tournament.
        Useful to get the matches.
        """
        return next(filter(lambda f: f.selected, self.stages), None)


def parse_tournament_stage(data: dict) -> Stage:
    """
    Parse the tournament stage data.
    """
    return Stage(
        id=data.get("key"), name=data.get("name"), selected=data.get("selected", False)
    )


def parse_tournament(data: dict) -> Tournament:
    """
    Parse the tournament data.
    """
    stages = []
    games = data.get("games")
    if games:
        stages = [parse_tournament_stage(stage) for stage in games.get("filters", {})]
    return Tournament(league=parse_league(data.get("league", {})), stages=stages)
