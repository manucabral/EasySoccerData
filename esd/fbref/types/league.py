"""
League-level player statistics types and parsers for FBref.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import lxml.html


@dataclass
class LeaguePlayerStandard:
    """Standard stats row for a league player (from stats_standard table)."""

    player: str = field(default="")
    nationality: str = field(default="")
    position: str = field(default="")
    team: str = field(default="")
    age: str = field(default="")
    born: str = field(default="")
    matches_played: int = field(default=0)
    starts: int = field(default=0)
    minutes: int = field(default=0)
    minutes_90s: float = field(default=0.0)
    goals: int = field(default=0)
    assists: int = field(default=0)
    goals_assists: int = field(default=0)
    goals_pens: int = field(default=0)
    pens_made: int = field(default=0)
    pens_att: int = field(default=0)
    cards_yellow: int = field(default=0)
    cards_red: int = field(default=0)
    xg: float = field(default=0.0)
    npxg: float = field(default=0.0)
    xg_assist: float = field(default=0.0)
    progressive_carries: int = field(default=0)
    progressive_passes: int = field(default=0)
    goals_per90: float = field(default=0.0)
    assists_per90: float = field(default=0.0)
    goals_assists_per90: float = field(default=0.0)
    goals_pens_per90: float = field(default=0.0)
    goals_assists_pens_per90: float = field(default=0.0)
    xg_per90: float = field(default=0.0)
    xg_assist_per90: float = field(default=0.0)
    xg_xg_assist_per90: float = field(default=0.0)
    npxg_per90: float = field(default=0.0)
    npxg_xg_assist_per90: float = field(default=0.0)
    match_log_url: str = field(default="")


def _cast(value: str, target_type: type):
    """Cast a string value to the target type, returning default on failure."""
    if not value or value.strip() == "":
        if target_type is int:
            return 0
        if target_type is float:
            return 0.0
        return ""
    try:
        return target_type(value.replace(",", ""))
    except (ValueError, TypeError):
        if target_type is int:
            return 0
        if target_type is float:
            return 0.0
        return value


def parse_league_players(
    document: lxml.html.HtmlElement,
    table_id: str = "stats_standard",
) -> list[LeaguePlayerStandard]:
    """
    Parse a league player stats table from an FBref HTML document.

    Also searches inside HTML comments for nested tables (common on FBref).

    Args:
        document: The parsed lxml HTML document.
        table_id: The HTML id of the table to parse (default "stats_standard").

    Returns:
        list[LeaguePlayerStandard]: Parsed player statistics rows.
    """
    table = document.find(f".//table[@id='{table_id}']")
    if table is None:
        from bs4 import BeautifulSoup, Comment

        html_str = lxml.html.tostring(document, encoding="unicode")
        soup = BeautifulSoup(html_str, "lxml")
        for comment in soup.find_all(text=lambda t: isinstance(t, Comment)):
            inner = BeautifulSoup(comment, "lxml")
            found = inner.find("table", id=table_id)
            if found:
                table_html = lxml.html.fromstring(str(found))
                return _parse_table_rows(table_html)
        return []

    return _parse_table_rows(table)


def _extract_href(cell: lxml.html.HtmlElement) -> str:
    href = cell.xpath(".//a/@href")
    return href[0] if href else ""


def _extract_text(cell: lxml.html.HtmlElement) -> str:
    return cell.text_content().strip()


def _parse_table_rows(table: lxml.html.HtmlElement) -> list[LeaguePlayerStandard]:
    rows = []
    tbody = table.find(".//tbody")
    if tbody is None:
        return rows
    for tr in tbody.findall(".//tr"):
        if "class" in tr.attrib and "thead" in tr.attrib["class"]:
            continue
        player = LeaguePlayerStandard()
        for cell in tr.findall(".//th | .//td"):
            stat = cell.get("data-stat", "")
            value = _extract_text(cell)
            if stat == "player":
                player.player = value
                player.match_log_url = _extract_href(cell)
            elif stat == "nationality":
                player.nationality = value.split()[-1] if value else ""
            elif stat == "position":
                player.position = value
            elif stat == "team":
                player.team = value
            elif stat == "age":
                player.age = value
            elif stat == "birth_year":
                player.born = value
            elif stat == "games":
                player.matches_played = _cast(value, int)
            elif stat == "games_starts":
                player.starts = _cast(value, int)
            elif stat == "minutes":
                player.minutes = _cast(value.replace(",", ""), int)
            elif stat == "minutes_90s":
                player.minutes_90s = _cast(value, float)
            elif stat == "goals":
                player.goals = _cast(value, int)
            elif stat == "assists":
                player.assists = _cast(value, int)
            elif stat == "goals_assists":
                player.goals_assists = _cast(value, int)
            elif stat == "goals_pens":
                player.goals_pens = _cast(value, int)
            elif stat == "pens_made":
                player.pens_made = _cast(value, int)
            elif stat == "pens_att":
                player.pens_att = _cast(value, int)
            elif stat == "cards_yellow":
                player.cards_yellow = _cast(value, int)
            elif stat == "cards_red":
                player.cards_red = _cast(value, int)
            elif stat == "xg":
                player.xg = _cast(value, float)
            elif stat == "npxg":
                player.npxg = _cast(value, float)
            elif stat == "xg_assist":
                player.xg_assist = _cast(value, float)
            elif stat == "progressive_carries":
                player.progressive_carries = _cast(value, int)
            elif stat == "progressive_passes":
                player.progressive_passes = _cast(value, int)
            elif stat == "goals_per90":
                player.goals_per90 = _cast(value, float)
            elif stat == "assists_per90":
                player.assists_per90 = _cast(value, float)
            elif stat == "goals_assists_per90":
                player.goals_assists_per90 = _cast(value, float)
            elif stat == "goals_pens_per90":
                player.goals_pens_per90 = _cast(value, float)
            elif stat == "goals_assists_pens_per90":
                player.goals_assists_pens_per90 = _cast(value, float)
            elif stat == "xg_per90":
                player.xg_per90 = _cast(value, float)
            elif stat == "xg_assist_per90":
                player.xg_assist_per90 = _cast(value, float)
            elif stat == "xg_xg_assist_per90":
                player.xg_xg_assist_per90 = _cast(value, float)
            elif stat == "npxg_per90":
                player.npxg_per90 = _cast(value, float)
            elif stat == "npxg_xg_assist_per90":
                player.npxg_xg_assist_per90 = _cast(value, float)
        if player.player:
            rows.append(player)
    return rows
