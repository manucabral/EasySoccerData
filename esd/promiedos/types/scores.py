"""Promiedos score, shootout and aggregate-score models and parsers."""

from dataclasses import dataclass, field


@dataclass
class Scores:
    """Home and away match scores."""

    home: int = field(default=0)
    away: int = field(default=0)


@dataclass
class Penalties(Scores):
    """Penalty-shootout results for both sides."""


@dataclass
class GlobalScores(Scores):
    """Home and away aggregate scores."""


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
