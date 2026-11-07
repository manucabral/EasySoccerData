"""
This module contains the Match dataclass which is used to store information about a match.
"""

import re
from dataclasses import dataclass, field

import lxml

_LANG_PREFIX_RE = re.compile(r"^/[a-z]{2}(?:-[a-z]{2})?(?=/)")
_DIGITS_RE = re.compile(r"\d+")


@dataclass
class Match:
    """
    A class to represent a match.
    """

    id: str = field(default=None)
    id_type: str = field(default=None)
    round: str = field(default="")
    gameweek: str = field(default="")
    start_time: str = field(default="")
    home_team: str = field(default="")
    home_xg: float = field(default=0.0)
    home_score: int = field(default=0)
    away_xg: float = field(default=0.0)
    away_team: str = field(default="")
    away_score: int = field(default=0)
    attendance: str = field(default="")
    venue: str = field(default="")
    referee: str = field(default="")
    notes: str = field(default="")
    date: str = field(default=None)
    home_team_id: str = field(default=None)
    away_team_id: str = field(default=None)
    competition_id: str = field(default=None)
    raw_score: str = field(default=None)


def extract_text(cell: lxml.html.HtmlElement) -> str:
    """
    Extract the text content from the cell.
    """
    return cell.text_content().strip()


def extract_href(cell: lxml.html.HtmlElement) -> str:
    """
    Extract the href attribute from the cell.
    """
    href = cell.xpath(".//a/@href")
    return href[0] if href else ""


def extract_team(cell: lxml.html.HtmlElement) -> str:
    """
    Extract the team name from the cell.
    """
    team = cell.xpath(".//a/text()")
    return team[0] if team else extract_text(cell)


def extract_score(cell: lxml.html.HtmlElement) -> tuple[int, int]:
    """
    Extract the home and away scores from the cell.
    """
    text = extract_text(cell)
    score = re.search(r"(\d+)(?:\s*\(\d+\))?\s*[–-]\s*(?:\(\d+\)\s*)?(\d+)", text)
    if score:
        return int(score.group(1)), int(score.group(2))
    scores = _DIGITS_RE.findall(text)
    home = int(scores[0]) if len(scores) > 0 else 0
    away = int(scores[1]) if len(scores) > 1 else 0
    return home, away


def extract_float(cell: lxml.html.HtmlElement) -> float:
    """
    Extract a float value from the cell.
    """
    txt = extract_text(cell)
    try:
        return float(txt) if txt else 0.0
    except ValueError:
        return 0.0


def parse_matchs(data: lxml.html.HtmlElement) -> list[Match]:
    """
    Parse the match data and convert it to a list of Match instances.

    Args:
        data (lxml.html.HtmlElement): The HTML data.

    Returns:
        list[Match]: A list of Match instances with extracted data.
    """
    matches = []
    # Only the schedule tables (id="sched_*") hold match rows; the page also
    # contains standings/leaderboard tables without data-stat attributes.
    rows = data.xpath("//table[starts-with(@id, 'sched')]//tbody/tr")

    for row in rows:
        if "thead" in (row.get("class") or ""):
            continue
        data_stat = {}
        cells = row.xpath("./th | ./td")
        for cell in cells:
            stat = cell.get("data-stat")
            if not stat:
                continue

            if stat == "match_report":
                url = extract_href(cell)
                if url:
                    url = _LANG_PREFIX_RE.sub("", url)
                data_stat["id"] = url
                if "/matches/" in url:
                    data_stat["id_type"] = "matches"
                if "/stathead/" in url:
                    data_stat["id_type"] = "stathead"

            elif stat in {"home_team", "away_team"}:
                data_stat[stat] = extract_team(cell)
                team_link = re.search(r"/squads/([^/]+)", extract_href(cell))
                data_stat[stat + "_id"] = team_link.group(1) if team_link else None
            elif stat == "score":
                data_stat["raw_score"] = extract_text(cell)
                home_score, away_score = extract_score(cell)
                data_stat["home_score"] = home_score
                data_stat["away_score"] = away_score
            elif stat in {"home_xg", "away_xg"}:
                data_stat[stat] = extract_float(cell)
            else:
                data_stat[stat] = extract_text(cell) or None
                if stat == "comp":
                    comp_link = re.search(r"/comps/(\d+)", extract_href(cell))
                    data_stat["competition_id"] = comp_link.group(1) if comp_link else None

        match = Match(
            id=data_stat.get("id", ""),
            id_type=data_stat.get("id_type", ""),
            round=data_stat.get("round", ""),
            gameweek=data_stat.get("gameweek", ""),
            start_time=data_stat.get("start_time", ""),
            home_team=data_stat.get("home_team", ""),
            home_xg=data_stat.get("home_xg", 0.0),
            home_score=data_stat.get("home_score", 0),
            away_xg=data_stat.get("away_xg", 0.0),
            away_team=data_stat.get("away_team", ""),
            away_score=data_stat.get("away_score", 0),
            attendance=data_stat.get("attendance", ""),
            venue=data_stat.get("venue", ""),
            referee=data_stat.get("referee", ""),
            # match_report=data_stat.get("match_report", ""),
            notes=data_stat.get("notes", ""),
            date=data_stat.get("date"),
            home_team_id=data_stat.get("home_team_id"),
            away_team_id=data_stat.get("away_team_id"),
            competition_id=data_stat.get("competition_id"),
            raw_score=data_stat.get("raw_score"),
        )
        matches.append(match)

    return matches
