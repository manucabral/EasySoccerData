"""
Sofascore match statistics grouped by category and period.
"""

from dataclasses import dataclass, field
from typing import Optional

from .lineup import Lineups


@dataclass
class StatisticItem:
    """One statistic's home and away values, totals and source type."""

    home_value: float = field(default=0.0)
    away_value: float = field(default=0.0)
    stat_type: str = field(default="")
    home_total: Optional[int] = field(default=None)
    away_total: Optional[int] = field(default=None)


def parse_statistic_item(item: dict[str, any]) -> StatisticItem:
    """
    Parse a statistic item.

    Args:
        item (dict): The statistic item.

    Returns:
        StatisticItem: The parsed statistic item.
    """
    return StatisticItem(
        stat_type=item.get("statisticsType", ""),
        home_value=item.get("homeValue", 0.0),
        away_value=item.get("awayValue", 0.0),
        home_total=item.get("homeTotal"),
        away_total=item.get("awayTotal"),
    )


@dataclass
class MatchOverviewStats:
    """Possession, expected goals and big-chance totals for both teams."""

    ball_possession: StatisticItem = field(default_factory=StatisticItem)
    expected_goals: StatisticItem = field(default_factory=StatisticItem)
    big_chance_created: StatisticItem = field(default_factory=StatisticItem)
    total_shots_on_goal: StatisticItem = field(default_factory=StatisticItem)
    goalkeeper_saves: StatisticItem = field(default_factory=StatisticItem)
    corner_kicks: StatisticItem = field(default_factory=StatisticItem)
    fouls: StatisticItem = field(default_factory=StatisticItem)
    passes: StatisticItem = field(default_factory=StatisticItem)
    total_tackle: StatisticItem = field(default_factory=StatisticItem)
    free_kicks: StatisticItem = field(default_factory=StatisticItem)
    yellow_cards: StatisticItem = field(default_factory=StatisticItem)


def parse_match_overview_stats(items: list[dict[str, any]]) -> MatchOverviewStats:
    """
    Parse match overview statistics.

    Args:
        items (list[dict]): The statistics items.

    Returns:
        MatchOverviewStats: The parsed match overview statistics.
    """
    mapping = {item["key"]: parse_statistic_item(item) for item in items}
    return MatchOverviewStats(
        ball_possession=mapping.get("ballPossession", StatisticItem()),
        expected_goals=mapping.get("expectedGoals", StatisticItem()),
        big_chance_created=mapping.get("bigChanceCreated", StatisticItem()),
        total_shots_on_goal=mapping.get("totalShotsOnGoal", StatisticItem()),
        goalkeeper_saves=mapping.get("goalkeeperSaves", StatisticItem()),
        corner_kicks=mapping.get("cornerKicks", StatisticItem()),
        fouls=mapping.get("fouls", StatisticItem()),
        passes=mapping.get("passes", StatisticItem()),
        total_tackle=mapping.get("totalTackle", StatisticItem()),
        free_kicks=mapping.get("freeKicks", StatisticItem()),
        yellow_cards=mapping.get("yellowCards", StatisticItem()),
    )


@dataclass
class ShotsStats:
    """Shot totals and shot outcomes for both teams."""

    total_shots_on_goal: StatisticItem = field(default_factory=StatisticItem)
    shots_on_goal: StatisticItem = field(default_factory=StatisticItem)
    hit_woodwork: StatisticItem = field(default_factory=StatisticItem)
    shots_off_goal: StatisticItem = field(default_factory=StatisticItem)
    blocked_scoring_attempt: StatisticItem = field(default_factory=StatisticItem)
    total_shots_inside_box: StatisticItem = field(default_factory=StatisticItem)
    total_shots_outside_box: StatisticItem = field(default_factory=StatisticItem)


def parse_shots_stats(items: list[dict[str, any]]) -> ShotsStats:
    """
    Parse shots statistics.

    Args:
        items (list[dict]): The statistics items.

    Returns:
        ShotsStats: The parsed shots statistics.
    """
    mapping = {item["key"]: parse_statistic_item(item) for item in items}
    return ShotsStats(
        total_shots_on_goal=mapping.get("totalShotsOnGoal", StatisticItem()),
        shots_on_goal=mapping.get("shotsOnGoal", StatisticItem()),
        hit_woodwork=mapping.get("hitWoodwork", StatisticItem()),
        shots_off_goal=mapping.get("shotsOffGoal", StatisticItem()),
        blocked_scoring_attempt=mapping.get("blockedScoringAttempt", StatisticItem()),
        total_shots_inside_box=mapping.get("totalShotsInsideBox", StatisticItem()),
        total_shots_outside_box=mapping.get("totalShotsOutsideBox", StatisticItem()),
    )


@dataclass
class AttackStats:
    """Attacking statistics for both teams."""

    big_chance_scored: StatisticItem = field(default_factory=StatisticItem)
    big_chance_missed: StatisticItem = field(default_factory=StatisticItem)
    touches_in_opp_box: StatisticItem = field(default_factory=StatisticItem)
    fouled_final_third: StatisticItem = field(default_factory=StatisticItem)
    offsides: StatisticItem = field(default_factory=StatisticItem)


def parse_attack_stats(items: list[dict[str, any]]) -> AttackStats:
    """
    Parse attack statistics.

    Args:
        items (list[dict]): The statistics items.

    Returns:
        AttackStats: Parsed attacking statistics.
    """
    mapping = {item["key"]: parse_statistic_item(item) for item in items}
    return AttackStats(
        big_chance_scored=mapping.get("bigChanceScored", StatisticItem()),
        big_chance_missed=mapping.get("bigChanceMissed", StatisticItem()),
        touches_in_opp_box=mapping.get("touchesInOppBox", StatisticItem()),
        fouled_final_third=mapping.get("fouledFinalThird", StatisticItem()),
        offsides=mapping.get("offsides", StatisticItem()),
    )


@dataclass
class PassesStats:
    """Passing totals and accuracy values for both teams."""

    accurate_passes: StatisticItem = field(default_factory=StatisticItem)
    throw_ins: StatisticItem = field(default_factory=StatisticItem)
    final_third_entries: StatisticItem = field(default_factory=StatisticItem)
    final_third_phase_statistic: StatisticItem = field(default_factory=StatisticItem)
    accurate_long_balls: StatisticItem = field(default_factory=StatisticItem)
    accurate_cross: StatisticItem = field(default_factory=StatisticItem)


def parse_passes_stats(items: list[dict[str, any]]) -> PassesStats:
    """
    Parse passes statistics.

    Args:
        items (list[dict]): The statistics items.

    Returns:
        PassesStats: The parsed passes statistics.
    """
    mapping = {item["key"]: parse_statistic_item(item) for item in items}
    return PassesStats(
        accurate_passes=mapping.get("accuratePasses", StatisticItem()),
        throw_ins=mapping.get("throwIns", StatisticItem()),
        final_third_entries=mapping.get("finalThirdEntries", StatisticItem()),
        final_third_phase_statistic=mapping.get(
            "finalThirdPhaseStatistic", StatisticItem()
        ),
        accurate_long_balls=mapping.get("accurateLongBalls", StatisticItem()),
        accurate_cross=mapping.get("accurateCross", StatisticItem()),
    )


@dataclass
class DuelsStats:
    """Duel, dribble and aerial-contest statistics for both teams."""

    duel_won_percent: StatisticItem = field(default_factory=StatisticItem)
    dispossessed: StatisticItem = field(default_factory=StatisticItem)
    ground_duels_percentage: StatisticItem = field(default_factory=StatisticItem)
    aerial_duels_percentage: StatisticItem = field(default_factory=StatisticItem)
    dribbles_percentage: StatisticItem = field(default_factory=StatisticItem)


def parse_duels_stats(items: list[dict[str, any]]) -> DuelsStats:
    """
    Parse duels statistics.

    Args:
        items (list[dict]): The statistics items.

    Returns:
        DuelsStats: The parsed duels statistics.
    """
    mapping = {item["key"]: parse_statistic_item(item) for item in items}
    return DuelsStats(
        duel_won_percent=mapping.get("duelWonPercent", StatisticItem()),
        dispossessed=mapping.get("dispossessed", StatisticItem()),
        ground_duels_percentage=mapping.get("groundDuelsPercentage", StatisticItem()),
        aerial_duels_percentage=mapping.get("aerialDuelsPercentage", StatisticItem()),
        dribbles_percentage=mapping.get("dribblesPercentage", StatisticItem()),
    )


@dataclass
class DefendingStats:
    """Tackles, interceptions, clearances and other defensive statistics."""

    won_tackle_percent: StatisticItem = field(default_factory=StatisticItem)
    total_tackle: StatisticItem = field(default_factory=StatisticItem)
    interception_won: StatisticItem = field(default_factory=StatisticItem)
    ball_recovery: StatisticItem = field(default_factory=StatisticItem)
    total_clearance: StatisticItem = field(default_factory=StatisticItem)


def parse_defending_stats(items: list[dict[str, any]]) -> DefendingStats:
    """
    Parse defending statistics.

    Args:
        items (list[dict]): The statistics items.

    Returns:
        DefendingStats: The parsed defending statistics.
    """
    mapping = {item["key"]: parse_statistic_item(item) for item in items}
    return DefendingStats(
        won_tackle_percent=mapping.get("wonTacklePercent", StatisticItem()),
        total_tackle=mapping.get("totalTackle", StatisticItem()),
        interception_won=mapping.get("interceptionWon", StatisticItem()),
        ball_recovery=mapping.get("ballRecovery", StatisticItem()),
        total_clearance=mapping.get("totalClearance", StatisticItem()),
    )


@dataclass
class GoalkeepingStats:
    """Goalkeeping statistics for both teams."""

    goalkeeper_saves: StatisticItem = field(default_factory=StatisticItem)
    goals_prevented: StatisticItem = field(default_factory=StatisticItem)
    goal_kicks: StatisticItem = field(default_factory=StatisticItem)


def parse_goalkeeping_stats(items: list[dict[str, any]]) -> GoalkeepingStats:
    """
    Parse goalkeeping statistics.

    Args:
        items (list[dict]): The statistics items.

    Returns:
        GoalkeepingStats: The parsed goalkeeping statistics.
    """
    mapping = {item["key"]: parse_statistic_item(item) for item in items}
    return GoalkeepingStats(
        goalkeeper_saves=mapping.get("goalkeeperSaves", StatisticItem()),
        goals_prevented=mapping.get("goalsPrevented", StatisticItem()),
        goal_kicks=mapping.get("goalKicks", StatisticItem()),
    )


@dataclass
class PeriodStats:
    """Statistics for one match period, grouped by category."""

    match_overview: MatchOverviewStats = field(default_factory=MatchOverviewStats)
    shots: ShotsStats = field(default_factory=ShotsStats)
    attack: AttackStats = field(default_factory=AttackStats)
    passes: PassesStats = field(default_factory=PassesStats)
    duels: DuelsStats = field(default_factory=DuelsStats)
    defending: DefendingStats = field(default_factory=DefendingStats)
    goalkeeping: GoalkeepingStats = field(default_factory=GoalkeepingStats)


def _group_items(group_mapping: dict, name: str) -> list:
    return (group_mapping.get(name) or {}).get("statisticsItems") or []


def parse_period_stats(groups: list[dict[str, any]]) -> PeriodStats:
    """
    Parse period statistics.

    Args:
        groups (list[dict]): The statistics groups.

    Returns:
        PeriodStats: The parsed period statistics.
    """
    group_mapping = {
        group["groupName"].lower(): group
        for group in groups
        if isinstance(group, dict) and "groupName" in group
    }
    return PeriodStats(
        match_overview=parse_match_overview_stats(
            _group_items(group_mapping, "match overview")
        ),
        shots=parse_shots_stats(_group_items(group_mapping, "shots")),
        attack=parse_attack_stats(_group_items(group_mapping, "attack")),
        passes=parse_passes_stats(_group_items(group_mapping, "passes")),
        duels=parse_duels_stats(_group_items(group_mapping, "duels")),
        defending=parse_defending_stats(_group_items(group_mapping, "defending")),
        goalkeeping=parse_goalkeeping_stats(_group_items(group_mapping, "goalkeeping")),
    )


@dataclass
class WinProbability:
    """Home-win, draw and away-win probabilities reported by Sofascore."""

    home: float = field(default=0.0)
    draw: float = field(default=0.0)
    away: float = field(default=0.0)


@dataclass
class MatchStats:
    """Match statistics by period, with win probabilities and optional lineups."""

    all: Optional[PeriodStats] = field(default=None)
    first_half: Optional[PeriodStats] = field(default=None)
    second_half: Optional[PeriodStats] = field(default=None)
    lineups: Optional[Lineups] = field(default=None)
    win_probability: Optional[WinProbability] = field(default=None)


def parse_match_probabilities(data: dict[str, any]) -> WinProbability:
    """
    Parse match probabilities.

    Args:
        data (dict): The match probabilities data.

    Returns:
        WinProbability: The parsed match probabilities.
    """
    return WinProbability(
        home=data.get("homeWin", 0.0),
        draw=data.get("draw", 0.0),
        away=data.get("awayWin", 0.0),
    )


def parse_match_stats(
    data: list[dict[str, any]], win_probabilities: dict[str, any]
) -> MatchStats:
    """
    Parse match statistics.

    Args:
        data (list[dict]): The match statistics data.
        win_probabilities (dict): The win probabilities data.

    Returns:
        MatchStats: Parsed period statistics and win probabilities.
    """
    match_stats = MatchStats()
    match_stats.win_probability = parse_match_probabilities(win_probabilities or {})
    if not data:
        return match_stats
    for stat in data:
        period = stat.get("period", "").upper()
        groups = stat.get("groups", [])
        period_stats = parse_period_stats(groups)
        if period == "ALL":
            match_stats.all = period_stats
        elif period == "1ST":
            match_stats.first_half = period_stats
        elif period == "2ND":
            match_stats.second_half = period_stats
    return match_stats
