"""
Scores data type.
"""

from dataclasses import dataclass, field


@dataclass
class Scores:
    """
    Scores data type.
    """

    home: int = field(default=0)
    away: int = field(default=0)


@dataclass
class Penalties(Scores):
    """
    Penalties data type.
    """


@dataclass
class GlobalScores(Scores):
    """
    Global scores data type.
    """


def parse_scores(data: list) -> Scores:
    """
    Parse the scores data.
    """
    if not data or len(data) < 2:
        return Scores()
    return Scores(home=int(data[0]), away=int(data[1]))


def parse_penalties(data: list) -> Penalties:
    """
    Parse the penalties data.
    """
    if not data or len(data) < 2:
        return Penalties()
    return Penalties(home=int(data[0]), away=int(data[1]))


def parse_global_scores(data: list) -> GlobalScores:
    """
    Parse the global scores data.
    """
    if not data or len(data) < 2:
        return GlobalScores()
    return GlobalScores(home=int(data[0]), away=int(data[1]))
