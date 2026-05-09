"""
SofaScore top tournament players data types.
"""

from dataclasses import dataclass, field

from .player import Player, parse_player
from .team import Team, parse_team


@dataclass
class TopPlayerStat:
    """
    Top player statistics.
    """

    value: float | int = field(default=0)
    id: int = field(default=0)
    type: str = field(default="")
    appearances: int = field(default=0)


@dataclass
class TopPlayerItem:
    """
    Top player item.
    """

    stat: TopPlayerStat = field(default_factory=TopPlayerStat)
    played_enough: bool = field(default=False)
    player: Player = field(default_factory=Player)
    team: Team = field(default_factory=Team)


@dataclass
class TopTournamentPlayers:
    """
    Available top tournament players criteria.
    """

    rating: list[TopPlayerItem] = field(default_factory=list)
    goals: list[TopPlayerItem] = field(default_factory=list)
    expected_goals: list[TopPlayerItem] = field(default_factory=list)
    assists: list[TopPlayerItem] = field(default_factory=list)
    expected_assists: list[TopPlayerItem] = field(default_factory=list)
    goals_assists_sum: list[TopPlayerItem] = field(default_factory=list)
    penalty_goals: list[TopPlayerItem] = field(default_factory=list)
    free_kick_goals: list[TopPlayerItem] = field(default_factory=list)
    scoring_frequency: list[TopPlayerItem] = field(default_factory=list)
    total_shots: list[TopPlayerItem] = field(default_factory=list)
    shots_on_target: list[TopPlayerItem] = field(default_factory=list)
    big_chances_missed: list[TopPlayerItem] = field(default_factory=list)
    big_chances_created: list[TopPlayerItem] = field(default_factory=list)
    accurate_passes: list[TopPlayerItem] = field(default_factory=list)
    key_passes: list[TopPlayerItem] = field(default_factory=list)
    accurate_long_balls: list[TopPlayerItem] = field(default_factory=list)
    successful_dribbles: list[TopPlayerItem] = field(default_factory=list)
    penalty_won: list[TopPlayerItem] = field(default_factory=list)
    tackles: list[TopPlayerItem] = field(default_factory=list)
    interceptions: list[TopPlayerItem] = field(default_factory=list)
    clearances: list[TopPlayerItem] = field(default_factory=list)
    possession_lost: list[TopPlayerItem] = field(default_factory=list)
    yellow_cards: list[TopPlayerItem] = field(default_factory=list)
    red_cards: list[TopPlayerItem] = field(default_factory=list)
    saves: list[TopPlayerItem] = field(default_factory=list)
    goals_prevented: list[TopPlayerItem] = field(default_factory=list)
    most_conceded: list[TopPlayerItem] = field(default_factory=list)
    least_conceded: list[TopPlayerItem] = field(default_factory=list)
    clean_sheet: list[TopPlayerItem] = field(default_factory=list)


def parse_top_tournament_players(data: dict) -> TopTournamentPlayers:
    """
    Parse the top tournament players data.
    """

    def parse_category(key: str) -> list[TopPlayerItem]:
        """
        Parse a category from the top criteria.
        """
        items = []
        for item in data.get(key, []):
            player = parse_player(item.get("player", {}))
            team = parse_team(item.get("team", {}))
            stats_data = item.get("statistics", {})
            stat = TopPlayerStat(
                value=stats_data.get(key),
                appearances=stats_data.get("appearances", 0),
                type=stats_data.get("type", 0),
            )
            items.append(TopPlayerItem(player=player, team=team, stat=stat))
        return items

    return TopTournamentPlayers(
        rating=parse_category("rating"),
        goals=parse_category("goals"),
        expected_goals=parse_category("expectedGoals"),
        assists=parse_category("assists"),
        expected_assists=parse_category("expectedAssists"),
        goals_assists_sum=parse_category("goalsAssistsSum"),
        penalty_goals=parse_category("penaltyGoals"),
        free_kick_goals=parse_category("freeKickGoal"),
        scoring_frequency=parse_category("scoringFrequency"),
        total_shots=parse_category("totalShots"),
        shots_on_target=parse_category("shotsOnTarget"),
        big_chances_missed=parse_category("bigChancesMissed"),
        big_chances_created=parse_category("bigChancesCreated"),
        accurate_passes=parse_category("accuratePasses"),
        key_passes=parse_category("keyPasses"),
        accurate_long_balls=parse_category("accurateLongBalls"),
        successful_dribbles=parse_category("successfulDribbles"),
        penalty_won=parse_category("penaltyWon"),
        tackles=parse_category("tackles"),
        interceptions=parse_category("interceptions"),
        clearances=parse_category("clearances"),
        possession_lost=parse_category("possessionLost"),
        yellow_cards=parse_category("yellowCards"),
        red_cards=parse_category("redCards"),
        saves=parse_category("saves"),
        goals_prevented=parse_category("goalsPrevented"),
        most_conceded=parse_category("mostConceded"),
        least_conceded=parse_category("leastConceded"),
        clean_sheet=parse_category("cleanSheet"),
    )
