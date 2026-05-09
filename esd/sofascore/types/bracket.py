"""
This module contains the dataclasses for the UEFA Champions League cupTree.
"""

from dataclasses import dataclass, field
from typing import Optional

from .team import Team, parse_team
from .tournament import Tournament, parse_tournament


@dataclass
class Participant:
    """
    A class to represent a participant in a bracket.
    """

    team: Team = field(default=None)
    winner: bool = field(default=False)
    order: int = field(default=None)
    id: int = field(default=None)
    source_block_id: Optional[int] = field(default=None)  # may not exist in all cases


def parse_participant(data: dict) -> Participant:
    """
    Parse the participant data.

    Args:
        data (dict): The participant data.

    Returns:
        Participant: The participant.
    """
    return Participant(
        team=parse_team(data.get("team", {})),
        winner=data.get("winner", False),
        order=data.get("order"),
        id=data.get("id"),
        source_block_id=data.get("sourceBlockId"),
    )


@dataclass
class Block:
    """
    A class to represent a block in a bracket.
    """

    block_id: int = field(default=None)
    finished: bool = field(default=False)
    matches_in_round: int = field(default=0)
    order: int = field(default=None)
    result: Optional[str] = field(default=None)
    home_team_score: Optional[str] = field(default=None)
    away_team_score: Optional[str] = field(default=None)
    participants: list[Participant] = field(default_factory=list)
    events: list[int] = field(default_factory=list)
    in_progress: bool = field(default=False)
    # hasNextRoundLink, id, events, seriesStartDateTimestamp, automaticProgression


def parse_block(data: dict) -> Block:
    """
    Parse the block data.

    Args:
        data (dict): The block data.

    Returns:
        Block: The block.
    """
    return Block(
        block_id=data.get("blockId"),
        finished=data.get("finished", False),
        matches_in_round=data.get("matchesInRound", 0),
        order=data.get("order"),
        result=data.get("result"),
        home_team_score=data.get("homeTeamScore"),
        away_team_score=data.get("awayTeamScore"),
        participants=[parse_participant(p) for p in data.get("participants", [])],
        events=data.get("events", []),
        in_progress=data.get("eventInProgress", False),
    )


@dataclass
class Round:
    """
    A class to represent a round in a bracket.
    """

    order: int = field(default=None)
    # type: int = field(default=None)
    description: Optional[str] = field(default=None)
    blocks: list[Block] = field(default_factory=list)


def parse_round(data: dict) -> Round:
    """
    Parse the round data.

    Args:
        data (dict): The round data.

    Returns:
        Round: The round.
    """
    return Round(
        order=data.get("order"),
        # type=data.get("type"),
        description=data.get("description"),
        blocks=[parse_block(b) for b in data.get("blocks", [])],
    )


@dataclass
class Bracket:
    """
    A class to represent a bracket.
    """

    id: int = field(default=None)
    name: str = field(default=None)
    tournament: Tournament = field(default=None)
    current_round: Optional[int] = field(default=None)
    rounds: list[Round] = field(default_factory=list)


def parse_bracket(data: dict) -> Bracket:
    """
    Parse the bracket data.

    Args:
        data (dict): The bracket data.

    Returns:
        Bracket: The bracket.
    """
    return Bracket(
        id=data.get("id"),
        name=data.get("name"),
        tournament=parse_tournament(data.get("tournament", {})),
        current_round=data.get("currentRound"),
        rounds=[parse_round(r) for r in data.get("rounds", [])],
    )


def parse_brackets(data: dict) -> list[Bracket]:
    """
    Parse the brackets data.

    Args:
        data (dict): The brackets data.

    Returns:
        list[Bracket]: The brackets.
    """
    return [parse_bracket(c) for c in data]
