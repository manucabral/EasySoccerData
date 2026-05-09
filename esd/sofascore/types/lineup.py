"""
This module contains the dataclasses for the Lineups object.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from .player import Player, parse_player


@dataclass
class Statistics:
    """
    Player statistics data class.
    Unique for each player in the lineup.
    """

    total_pass: Optional[int] = field(default=None)
    accurate_pass: Optional[int] = field(default=None)
    total_long_balls: Optional[int] = field(default=None)
    accurate_long_balls: Optional[int] = field(default=None)
    minutes_played: Optional[int] = field(default=None)
    touches: Optional[int] = field(default=None)
    rating: Optional[float] = field(default=None)
    possession_lost_ctrl: Optional[int] = field(default=None)
    duel_won: Optional[int] = field(default=None)
    total_contest: Optional[int] = field(default=None)
    won_contest: Optional[int] = field(default=None)
    total_tackle: Optional[int] = field(default=None)
    was_fouled: Optional[int] = field(default=None)
    aerial_won: Optional[int] = field(default=None)
    total_clearance: Optional[int] = field(default=None)
    interception_won: Optional[int] = field(default=None)
    key_pass: Optional[int] = field(default=None)
    blocked_scoring_attempt: Optional[int] = field(default=None)
    duel_lost: Optional[int] = field(default=None)
    aerial_lost: Optional[int] = field(default=None)


@dataclass
class PlayerLineup:
    """
    Player lineup data class.
    It's different from the Player class.
    Also the attribute "info" is the player object.
    """

    info: Player = field(default=None)
    team_id: int = field(default=0)
    substitute: bool = field(default=False)
    captain: bool = field(default=False)
    statistics: Optional[Statistics] = field(default=None)


@dataclass
class MissingPlayer:
    """
    Missing player data class.
    """

    player: Player = field(default=None)
    reason: int = field(default=0)


@dataclass
class TeamColor:
    """
    Team color data class. Simple.
    """

    primary: str = field(default="")
    number: str = field(default="")
    outline: str = field(default="")
    fancy_number: str = field(default="")


@dataclass
class TeamLineup:
    """
    Team lineup data class.
    """

    players: list[PlayerLineup] = field(default_factory=list)
    missing_players: list[MissingPlayer] = field(default_factory=list)
    support_staff: list[Any] = field(default_factory=list)
    formation: str = field(default="")
    player_color: TeamColor = field(default=None)
    goalkeeper_color: TeamColor = field(default=None)


@dataclass
class Lineups:
    """
    Lineups data class.
    """

    confirmed: bool = field(default=False)
    home: TeamLineup = field(default=None)
    away: Optional[TeamLineup] = field(default=None)


def parse_lineups(data: dict) -> Lineups:
    """
    Parse the lineups data.

    Args:
        data (dict): The lineups data.

    Returns:
        Lineups: The lineups object.
    """

    def parse_team_color(d: dict) -> TeamColor:
        """
        Parse the team color data.

        Args:
            d (dict): The team color data.

        Returns:
            TeamColor: The team color object.
        """
        return TeamColor(
            primary=d.get("primary", ""),
            number=d.get("number", ""),
            outline=d.get("outline", ""),
            fancy_number=d.get("fancyNumber", ""),
        )

    def parse_statistics(d: dict) -> Statistics:
        """
        Parse the player statistics data.

        Args:
            d (dict): The player statistics data.

        Returns:
            Statistics: The player statistics object.
        """
        return Statistics(
            total_pass=d.get("totalPass"),
            accurate_pass=d.get("accuratePass"),
            total_long_balls=d.get("totalLongBalls"),
            accurate_long_balls=d.get("accurateLongBalls"),
            minutes_played=d.get("minutesPlayed"),
            touches=d.get("touches"),
            rating=d.get("rating"),
            possession_lost_ctrl=d.get("possessionLostCtrl"),
            duel_won=d.get("duelWon"),
            total_contest=d.get("totalContest"),
            won_contest=d.get("wonContest"),
            total_tackle=d.get("totalTackle"),
            was_fouled=d.get("wasFouled"),
            aerial_won=d.get("aerialWon"),
            total_clearance=d.get("totalClearance"),
            interception_won=d.get("interceptionWon"),
            key_pass=d.get("keyPass"),
            blocked_scoring_attempt=d.get("blockedScoringAttempt"),
            duel_lost=d.get("duelLost"),
            aerial_lost=d.get("aerialLost"),
        )

    def parse_player_item(d: dict) -> PlayerLineup:
        """
        Parse the player item data.

        Args:
            d (dict): The player item data.

        Returns:
            PlayerLineup: The player lineup object.
        """
        player_obj = parse_player(d.get("player", {}))
        return PlayerLineup(
            info=player_obj,
            team_id=d.get("teamId", 0),
            substitute=d.get("substitute", False),
            captain=d.get("captain", False),
            statistics=(
                parse_statistics(d.get("statistics", {}))
                if d.get("statistics")
                else None
            ),
        )

    def parse_missing_player(d: dict) -> MissingPlayer:
        """
        Parse the missing player data.

        Args:
            d (list): The missing player data.

        Returns:
            MissingPlayer: The missing player object.
        """
        player_obj = parse_player(d.get("player", {}))
        return MissingPlayer(player=player_obj, reason=d.get("reason", 0))

    def parse_team_lineup(d: dict) -> TeamLineup:
        """
        Parse the team lineup data.

        Args:
            d (dict): The team lineup data.

        Returns:
            TeamLineup: The team lineup object.
        """
        players = [parse_player_item(item) for item in d.get("players", [])]
        support_staff = d.get("supportStaff", [])
        formation = d.get("formation", "")
        missing_players = [
            parse_missing_player(item) for item in d.get("missingPlayers", [])
        ]
        player_color = parse_team_color(d.get("playerColor", {}))
        goalkeeper_color = parse_team_color(d.get("goalkeeperColor", {}))
        return TeamLineup(
            players=players,
            support_staff=support_staff,
            formation=formation,
            player_color=player_color,
            missing_players=missing_players,
            goalkeeper_color=goalkeeper_color,
        )

    home_obj = parse_team_lineup(data.get("home", {}))
    away_obj = parse_team_lineup(data.get("away", {})) if data.get("away") else None

    return Lineups(confirmed=data.get("confirmed", False), home=home_obj, away=away_obj)
