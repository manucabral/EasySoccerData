"""
SofaScore top players types.
"""

from dataclasses import dataclass, field

from .player import Player, parse_player


@dataclass
class TopPlayersMatch:
    """
    Top players match dataclass.
    """

    best: Player = field(default=None)
    home_team: list[Player] = field(default_factory=list)
    away_team: list[Player] = field(default_factory=list)


def parse_top_player_match(data: dict) -> TopPlayersMatch:
    """
    Parse top players match data.
    """
    players = []
    for item in data:
        players.append(parse_player(item.get("player", {})))
    return players


def parse_top_players_match(data: dict) -> TopPlayersMatch:
    """
    Parse top players match data.
    """
    if not data:
        return TopPlayersMatch()
    best_player = data.get("playerOfTheMatch").get("player", {})
    return TopPlayersMatch(
        best=parse_player(best_player),
        home_team=parse_top_player_match(data.get("bestHomeTeamPlayers", [])),
        away_team=parse_top_player_match(data.get("bestAwayTeamPlayers", [])),
    )
