"""
This module contains the data types and functions for parsing match details.
"""

from dataclasses import dataclass, field

import lxml.html


@dataclass
class PlayerStatRow:
    """
    Base class for player statistics rows.
    """

    player: str = field(default="")
    shirtnumber: str = field(default="")
    nationality: str = field(default="")
    position: str = field(default="")
    age: str = field(default="")
    minutes: int = field(default=0)


@dataclass
class PlayerStatsRow(PlayerStatRow):
    """
    Player statistics for a match is not switch case.
    """

    minutes: int = field(default=0)
    goals: int = field(default=0)
    assists: int = field(default=0)
    pens_made: int = field(default=0)
    pens_att: int = field(default=0)
    shots: int = field(default=0)
    shots_on_target: int = field(default=0)
    yellow_cards: int = field(default=0)
    red_cards: int = field(default=0)
    fouls_committed: int = field(default=0)
    fouls_drawn: int = field(default=0)
    offsides: int = field(default=0)
    crosses: int = field(default=0)
    tackles_won: int = field(default=0)
    interceptions: int = field(default=0)
    own_goals: int = field(default=0)
    pens_won: int = field(default=None)
    pens_conceded: int = field(default=None)


@dataclass
class PlayerSummaryRow(PlayerStatRow):
    """
    Player summary statistics.
    """

    goals: int = field(default=0)
    assists: int = field(default=0)
    pens_made: int = field(default=0)
    pens_att: int = field(default=0)
    shots: int = field(default=0)
    shots_on_target: int = field(default=0)
    cards_yellow: int = field(default=0)
    cards_red: int = field(default=0)
    touches: int = field(default=0)
    tackles: int = field(default=0)
    interceptions: int = field(default=0)
    blocks: int = field(default=0)
    xg: float = field(default=0.0)
    npxg: float = field(default=0.0)
    xg_assist: float = field(default=0.0)
    sca: int = field(default=0)
    gca: int = field(default=0)
    passes_completed: int = field(default=0)
    passes: int = field(default=0)
    passes_pct: float = field(default=0.0)
    progressive_passes: int = field(default=0)
    carries: int = field(default=0)
    progressive_carries: int = field(default=0)
    take_ons: int = field(default=0)
    take_ons_won: int = field(default=0)


@dataclass
class PlayerPassRow(PlayerStatRow):
    """
    Player passing statistics.
    """

    passes_completed: int = field(default=0)
    passes: int = field(default=0)
    passes_pct: float = field(default=0.0)
    passes_total_distance: int = field(default=0)
    passes_progressive_distance: int = field(default=0)
    passes_completed_short: int = field(default=0)
    passes_short: int = field(default=0)
    passes_pct_short: float = field(default=0.0)
    passes_completed_medium: int = field(default=0)
    passes_medium: int = field(default=0)
    passes_pct_medium: float = field(default=0.0)
    passes_completed_long: int = field(default=0)
    passes_long: int = field(default=0)
    passes_pct_long: float = field(default=0.0)
    assists: int = field(default=0)
    xg_assist: float = field(default=0.0)
    pass_xa: float = field(default=0.0)
    assisted_shots: int = field(default=0)
    passes_into_final_third: int = field(default=0)
    passes_into_penalty_area: int = field(default=0)
    crosses_into_penalty_area: int = field(default=0)
    progressive_passes: int = field(default=0)


@dataclass
class PlayerPassTypesRow(PlayerStatRow):
    """
    Player passing types statistics.
    """

    passes: int = field(default=0)
    passes_live: int = field(default=0)
    passes_dead: int = field(default=0)
    passes_free_kicks: int = field(default=0)
    through_balls: int = field(default=0)
    passes_switches: int = field(default=0)
    crosses: int = field(default=0)
    throw_ins: int = field(default=0)
    corner_kicks: int = field(default=0)
    corner_kicks_in: int = field(default=0)
    corner_kicks_out: int = field(default=0)
    corner_kicks_straight: int = field(default=0)
    passes_completed: int = field(default=0)
    passes_offsides: int = field(default=0)
    passes_blocked: int = field(default=0)


@dataclass
class PlayerDefensiveActionsRow(PlayerStatRow):
    """
    Player defensive actions statistics.
    """

    tackles: int = field(default=0)
    tackles_won: int = field(default=0)
    tackles_def_3rd: int = field(default=0)
    tackles_mid_3rd: int = field(default=0)
    tackles_att_3rd: int = field(default=0)
    challenge_tackles: int = field(default=0)
    challenges: int = field(default=0)
    challenge_tackles_pct: float = field(default=0.0)
    challenges_lost: int = field(default=0)
    blocks: int = field(default=0)
    blocked_shots: int = field(default=0)
    blocked_passes: int = field(default=0)
    interceptions: int = field(default=0)
    tackles_interceptions: int = field(default=0)
    clearances: int = field(default=0)
    errors: int = field(default=0)


@dataclass
class PlayerPossessionRow(PlayerStatRow):
    """
    Player possession statistics.
    """

    touches: int = field(default=0)
    touches_def_pen_area: int = field(default=0)
    touches_def_3rd: int = field(default=0)
    touches_mid_3rd: int = field(default=0)
    touches_att_3rd: int = field(default=0)
    touches_att_pen_area: int = field(default=0)
    touches_live_ball: int = field(default=0)
    take_ons: int = field(default=0)
    take_ons_won: int = field(default=0)
    take_ons_won_pct: float = field(default=0.0)
    take_ons_tackled: int = field(default=0)
    take_ons_tackled_pct: float = field(default=0.0)
    carries: int = field(default=0)
    carries_distance: int = field(default=0)
    carries_progressive_distance: int = field(default=0)
    progressive_carries: int = field(default=0)
    carries_into_final_third: int = field(default=0)
    carries_into_penalty_area: int = field(default=0)
    miscontrols: int = field(default=0)
    dispossessed: int = field(default=0)
    passes_received: int = field(default=0)
    progressive_passes_received: int = field(default=0)


@dataclass
class PlayerMiscellaneousRow(PlayerStatRow):
    """
    Player miscellaneous statistics.
    """

    cards_yellow: int = field(default=0)
    cards_red: int = field(default=0)
    cards_yellow_red: int = field(default=0)
    fouls: int = field(default=0)
    fouled: int = field(default=0)
    offsides: int = field(default=0)
    crosses: int = field(default=0)
    interceptions: int = field(default=0)
    tackles_won: int = field(default=0)
    pens_won: int = field(default=0)
    pens_conceded: int = field(default=0)
    own_goals: int = field(default=0)
    ball_recoveries: int = field(default=0)
    aerials_won: int = field(default=0)
    aerials_lost: int = field(default=0)
    aerials_won_pct: float = field(default=0.0)


@dataclass
class KeeperStatsRow:
    """
    Goalkeeper statistics for a match is not switch case.
    """

    keeper_stats_id: str = field(default="")
    player: str = field(default="")
    age: str = field(default="")
    minutes: int = field(default=0)
    gk_shots_on_target_against: int = field(default=0)
    gk_goals_against: int = field(default=0)
    gk_saves: int = field(default=0)
    gk_save_pct: float = field(default=0.0)


@dataclass
class TableDetails:
    """
    Base class for table details.
    """

    id: str
    name: str
    # data: list[lxml.html.HtmlElement] = field(default_factory=list)


@dataclass
class PlayerStatsTableDetails(TableDetails):
    """
    Player statistics table details.
    """

    rows: list[PlayerStatsRow] = field(default_factory=list)
    summary: PlayerSummaryRow = field(default_factory=PlayerSummaryRow)
    passing: PlayerPassRow = field(default_factory=PlayerPassRow)
    passtypes: PlayerPassTypesRow = field(default_factory=PlayerPassTypesRow)
    defensive_actions: PlayerDefensiveActionsRow = field(
        default_factory=PlayerDefensiveActionsRow
    )
    possessions: PlayerPossessionRow = field(default_factory=PlayerPossessionRow)
    miscellaneous: PlayerMiscellaneousRow = field(
        default_factory=PlayerMiscellaneousRow
    )


@dataclass
class MatchDetails:
    """
    Match details for a football match.
    """

    is_table_wrapper: bool = False  # maybe the name changes
    content: list[TableDetails] = field(default_factory=dict)
    home_players: PlayerStatsTableDetails = field(default_factory=dict)
    home_keeper: PlayerStatsTableDetails = field(default_factory=dict)
    away_players: PlayerStatsTableDetails = field(default_factory=dict)
    away_keeper: PlayerStatsTableDetails = field(default_factory=dict)


def get_all_tables(data: lxml.html.HtmlElement) -> list[lxml.html.HtmlElement]:
    """
    Get all tables from the HTML data.
    """
    return data.xpath("//table")


def get_switchers(data: lxml.html.HtmlElement) -> list[lxml.html.HtmlElement]:
    """
    Get all switchers from the HTML data.
    """
    return data.xpath("//*[contains(@id, 'switcher')]")


def get_table_wrappers(data: lxml.html.HtmlElement) -> list[lxml.html.HtmlElement]:
    """
    Get all table wrappers from the HTML data.
    """
    return data.xpath(
        "//*[contains(concat(' ', normalize-space(@class), ' '), ' table_wrapper ')]"
    )


def parse_match_details(data: lxml.html.HtmlElement) -> MatchDetails:
    """
    Parse match details from the HTML data.
    """
    is_table_wrapper = False
    content = get_switchers(data)
    if not content:
        # so we have a simple table wrapper without switchers
        is_table_wrapper = True
        content = get_table_wrappers(data)

    match_details = MatchDetails(is_table_wrapper=is_table_wrapper)
    is_home = True
    found_tables = []
    for child in content:
        element_id = child.get("id").strip() if child.get("id") else "unknown"
        if is_table_wrapper:
            continue
        found_tables = child.xpath(".//table")
        if "shots" in element_id:
            # ... add shots parser
            continue
        target_key = "home_players" if is_home else "away_players"
        setattr(
            match_details,
            target_key,
            PlayerStatsTableDetails(
                id=element_id,
                name=element_id,
                summary=parse_table(found_tables, 0, PlayerSummaryRow),
                passing=parse_table(found_tables, 1, PlayerPassRow),
                passtypes=parse_table(found_tables, 2, PlayerPassTypesRow),
                defensive_actions=parse_table(
                    found_tables, 3, PlayerDefensiveActionsRow
                ),
                possessions=parse_table(found_tables, 4, PlayerPossessionRow),
                miscellaneous=parse_table(found_tables, 5, PlayerMiscellaneousRow),
            ),
        )
        is_home = False

    if is_table_wrapper:
        match_details.home_players = parse_table_wrapped(found_tables, 0)
        match_details.home_keeper = parse_table_wrapped(found_tables, 1)
        match_details.away_players = parse_table_wrapped(found_tables, 2)
        match_details.away_keeper = parse_table_wrapped(found_tables, 3)

    # ... mix wrappered goalkeeper stats if is switcher
    # mixed_content = get_table_wrappers(data)
    # found_tables = []
    # for child in mixed_content:
    # tables = child.xpath(".//table")
    # for table in tables:
    # table_id = table.get("id", "unknown")
    # if "keeper" in table_id:
    # found_tables.append(table)
    # match_details.home_keeper = parse_table_wrapped(found_tables, 0)
    # match_details.away_keeper = parse_table_wrapped(found_tables, 1)
    return match_details


def parse_table(data: list[lxml.html.HtmlElement], index: int, instance: type) -> list:
    """
    Parse a table from the HTML data.
    """
    table = data[index]
    # caption = table.xpath(".//caption")
    # table_id = table.get("id", "unknown")
    # table_name = caption[0].text_content().strip() if caption else "unknown"
    rows = []
    tbody = table.xpath(".//tbody")
    for tr in tbody[0].xpath(".//tr"):
        player = instance()
        for cell in tr.xpath(".//th | .//td"):
            data_stat = cell.get("data-stat")
            value = cell.text_content().strip()
            attr = data_stat.strip()
            setattr(player, attr, value)
        rows.append(player)
    return rows


def parse_table_wrapped(
    data: list[lxml.html.HtmlElement], index: int
) -> PlayerStatsTableDetails:
    """
    Parse a wrapped table from the HTML data.
    """
    table = data[index]
    table_id = table.get("id", "unknown")
    caption = table.xpath(".//caption")
    table_name = caption[0].text_content().strip() if caption else "unknown"
    rows = []
    tbody = table.xpath(".//tbody")
    for tr in tbody[0].xpath(".//tr"):
        player = PlayerStatsRow() if "keeper" not in table_id else KeeperStatsRow()
        for cell in tr.xpath(".//th | .//td"):
            data_stat = cell.get("data-stat")
            value = cell.text_content().strip()
            attr = data_stat.strip()
            setattr(player, attr, value)
        rows.append(player)
    # header = [th.text_content().strip() for th in table.xpath(".//thead/tr/th")]
    return PlayerStatsTableDetails(id=table_id, name=table_name, rows=rows)
