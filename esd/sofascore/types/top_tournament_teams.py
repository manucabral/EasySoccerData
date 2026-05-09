"""
Contains top tournament teams data.
"""

from dataclasses import dataclass, field

from .team import Team, parse_team


@dataclass
class TopTeamStat:
    """
    Top team statistics.
    """

    value: float | int = field(default=0)
    matches: int = field(default=0)


@dataclass
class TopTeamItem:
    """
    Top team item.
    """

    team: Team = field(default_factory=Team)
    stats: TopTeamStat = field(default_factory=TopTeamStat)


@dataclass
class TopTournamentTeams:
    """
    Available top tournament teams criteria.
    """

    average_rating: list[TopTeamItem] = field(default_factory=list)
    goals_scored: list[TopTeamItem] = field(default_factory=list)
    goals_conceded: list[TopTeamItem] = field(default_factory=list)
    big_chances: list[TopTeamItem] = field(default_factory=list)
    big_chances_missed: list[TopTeamItem] = field(default_factory=list)
    hit_woodwork: list[TopTeamItem] = field(default_factory=list)
    yellow_cards: list[TopTeamItem] = field(default_factory=list)
    red_cards: list[TopTeamItem] = field(default_factory=list)
    average_ball_possession: list[TopTeamItem] = field(default_factory=list)
    accurate_passes: list[TopTeamItem] = field(default_factory=list)
    accurate_long_balls: list[TopTeamItem] = field(default_factory=list)
    accurate_crosses: list[TopTeamItem] = field(default_factory=list)
    shots: list[TopTeamItem] = field(default_factory=list)
    shots_on_target: list[TopTeamItem] = field(default_factory=list)
    successful_dribbles: list[TopTeamItem] = field(default_factory=list)
    tackles: list[TopTeamItem] = field(default_factory=list)
    interceptions: list[TopTeamItem] = field(default_factory=list)
    clearances: list[TopTeamItem] = field(default_factory=list)
    corners: list[TopTeamItem] = field(default_factory=list)
    fouls: list[TopTeamItem] = field(default_factory=list)
    penalty_goals: list[TopTeamItem] = field(default_factory=list)
    penalty_goals_conceded: list[TopTeamItem] = field(default_factory=list)
    clean_sheets: list[TopTeamItem] = field(default_factory=list)


def parse_top_tournament_teams(data: dict) -> TopTournamentTeams:
    """
    Parse the top tournament teams data.
    """

    def parse_category(key: str) -> list[TopTeamItem]:
        """
        Parse a category from the top criteria.
        """
        items = []
        for item in data.get(key, []):
            team = parse_team(item.get("team", {}))
            stats_data = item.get("statistics", {})
            stat = TopTeamStat(
                value=stats_data.get(key), matches=stats_data.get("matches", 0)
            )
            items.append(TopTeamItem(team=team, stats=stat))
        return items

    return TopTournamentTeams(
        average_rating=parse_category("avgRating"),
        goals_scored=parse_category("goalsScored"),
        goals_conceded=parse_category("goalsConceded"),
        big_chances=parse_category("bigChances"),
        big_chances_missed=parse_category("bigChancesMissed"),
        hit_woodwork=parse_category("hitWoodwork"),
        yellow_cards=parse_category("yellowCards"),
        red_cards=parse_category("redCards"),
        average_ball_possession=parse_category("averageBallPossession"),
        accurate_passes=parse_category("accuratePasses"),
        accurate_long_balls=parse_category("accurateLongBalls"),
        accurate_crosses=parse_category("accurateCrosses"),
        shots=parse_category("shots"),
        shots_on_target=parse_category("shotsOnTarget"),
        successful_dribbles=parse_category("successfulDribbles"),
        tackles=parse_category("tackles"),
        interceptions=parse_category("interceptions"),
        clearances=parse_category("clearances"),
        corners=parse_category("corners"),
        fouls=parse_category("fouls"),
        penalty_goals=parse_category("penaltyGoals"),
        penalty_goals_conceded=parse_category("penaltyGoalsConceded"),
        clean_sheets=parse_category("cleanSheets"),
    )
