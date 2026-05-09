"""
This module contains the dataclass for the comment object.
"""

from dataclasses import dataclass, field
from enum import Enum

from .player import Player, parse_player


class CommentType(Enum):
    """
    Enum for the comment type.
    """

    MATCH_STARTED = "matchStarted"
    MATCH_ENDED = "matchEnded"
    MATCH_POSTPONED = "postponed"
    END_FIRST_HALF = "endFirstHalf"
    END_SECOND_HALF = "endSecondHalf"
    END_PERIOD = "periodEnd"
    ADDED_TIME = "addedTime"
    DELAY_START = "startDelay"
    DELAY_END = "endDelay"
    OFFSIDE = "offside"
    SUBSTITUTION = "substitution"
    YELLOW_CARD = "yellowCard"
    SHOT_SAVE = "shotSaved"
    SHOT_BLOCKED = "shotBlocked"
    SHOT_OFF_TARGET = "shotOffTarget"
    PENALTY_LOST = "penaltyLost"
    PENALTY_SCORED = "penaltyScored"
    PENALTY_MISSED = "penaltyMissed"
    PENALTY_AWARDED = "penaltyAwarded"
    PENALTY_SAVE = "penaltySaved"
    CORNER_KICK = "cornerKick"
    FREE_KICK_LOST = "freeKickLost"
    FREE_KICK_WON = "freeKickWon"
    SCORE_UPDATE = "scoreChange"
    UNKNOWN = "unknown"


@dataclass
class Comment:
    """
    Main comment dataclass.
    """

    period: str = field(default="")
    text: str = field(default="")
    player: Player = field(default=None)
    time: int = field(default=0)
    type: CommentType = field(default=CommentType.UNKNOWN)
    is_home: bool = field(default=False)
    player_in: Player = field(default=None)
    player_out: Player = field(default=None)


def parse_comment_type(type_str: str) -> CommentType:
    """
    Parse the comment type.
    """
    try:
        return CommentType(type_str)
    except ValueError:
        return CommentType.UNKNOWN


def parse_comment(data: dict) -> Comment:
    """
    Parse the comment data.
    """
    return Comment(
        period=data.get("periodName", ""),
        text=data.get("text", ""),
        player=parse_player(data.get("player", {})),
        time=data.get("time", 0),
        type=parse_comment_type(data.get("type", "unknown")),
        is_home=data.get("isHome", False),
        player_in=parse_player(data.get("playerIn", {})),
        player_out=parse_player(data.get("playerOut", {})),
    )


def parse_comments(data: list) -> list[Comment]:
    """
    Parse the comments data.
    """
    return [parse_comment(item) for item in data]
