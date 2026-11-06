"""
BeSoccer dataclasses and HTML parsers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from lxml import html

_INT_RE = re.compile(r"[-+]?\d+")


def _extract_int(text: str | None, default: int | None = 0) -> int | None:
    if not text:
        return default
    m = _INT_RE.search(text)
    return int(m.group(0)) if m else default


@dataclass
class BeSoccerTeam:
    """
    A club or national team in BeSoccer.
    """

    id: int | None = None
    name: str = None
    slug: str = None
    crest_url: str = None
    score: int | None = None


@dataclass
class BeSoccerMatch:
    """
    A match parsed from BeSoccer livescore.
    """

    id: int | None = None
    competition_name: str = None
    competition_slug: str = None
    start_time: str = None
    status_id: int | None = None
    time_display: str = None
    tv_network: str = None
    url: str = None
    home_team: BeSoccerTeam = field(default_factory=BeSoccerTeam)
    away_team: BeSoccerTeam = field(default_factory=BeSoccerTeam)


@dataclass
class BeSoccerStandingRow:
    """
    A single row in a BeSoccer competition standings table.
    """

    position: int = 0
    team: BeSoccerTeam = field(default_factory=BeSoccerTeam)
    points: int = 0
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_diff: int = 0
    form: list[str] = field(default_factory=list)


def _slug_from_href(href: str | None) -> str | None:
    if not href:
        return None
    parts = [p for p in href.rstrip("/").split("/") if p]
    return parts[-1] if parts else None


def _parse_side(side_div, raw_team_id: str | None) -> BeSoccerTeam:
    team_id = _extract_int(raw_team_id, None)
    if side_div is None:
        return BeSoccerTeam(id=team_id)
    name_els = [
        d for d in side_div.iter("div") if "team-name" in (d.get("class") or "")
    ]
    imgs = list(side_div.iter("img"))
    return BeSoccerTeam(
        id=team_id,
        name=name_els[0].text_content().strip() if name_els else None,
        crest_url=imgs[0].get("src") if imgs else None,
    )


def parse_livescore_html(html_text: str) -> list[BeSoccerMatch]:
    """
    Parse matches from a BeSoccer livescore HTML document.
    """
    if not html_text:
        return []
    doc = html.fromstring(html_text)
    matches: list[BeSoccerMatch] = []
    seen_ids: set[int] = set()

    for panel in doc.iter("div"):
        if "panel" not in (panel.get("class") or ""):
            continue
        comp_links = [
            a
            for a in panel.iter("a")
            if a.get("data-cy") == "competitionName"
            or "/competicion/" in (a.get("href") or "")
        ]
        comp_link = comp_links[0] if comp_links else None
        comp_href = comp_link.get("href") if comp_link is not None else None
        comp_slug = _slug_from_href(comp_href)
        comp_name = None
        if comp_link is not None:
            spans = list(comp_link.iter("span"))
            comp_name = (
                spans[0].text_content().strip()
                if spans
                else comp_link.text_content().strip()
            )

        for link in panel.iter("a"):
            raw_id = link.get("id") or ""
            if not raw_id.startswith("match-"):
                continue
            match_id = _extract_int(raw_id.removeprefix("match-"), None)
            if match_id is not None:
                if match_id in seen_ids:
                    continue
                seen_ids.add(match_id)

            team_boxes = [
                d for d in link.iter("div") if "team-info" in (d.get("class") or "")
            ]
            home_div = team_boxes[0] if len(team_boxes) > 0 else None
            away_div = team_boxes[1] if len(team_boxes) > 1 else None

            home_team = _parse_side(home_div, link.get("data-local-id"))
            away_team = _parse_side(away_div, link.get("data-visitor-id"))

            r1_els = [s for s in link.iter("span") if "r1" in (s.get("class") or "")]
            r2_els = [s for s in link.iter("span") if "r2" in (s.get("class") or "")]
            if r1_els and r2_els:
                home_team.score = _extract_int(r1_els[0].text_content(), None)
                away_team.score = _extract_int(r2_els[0].text_content(), None)

            dates_els = [
                d for d in link.iter("div") if "dates" in (d.get("class") or "")
            ]
            dates_text = dates_els[0].text_content().strip() if dates_els else ""
            markers = [
                d for d in link.iter("div") if "marker" in (d.get("class") or "")
            ]
            marker_text = markers[0].text_content().strip() if markers else ""
            time_display = dates_text or marker_text or None

            tv_els = [
                d for d in link.iter("div") if "tv-info" in (d.get("class") or "")
            ]
            tv_network = tv_els[0].text_content().strip() if tv_els else None

            matches.append(
                BeSoccerMatch(
                    id=match_id,
                    competition_name=comp_name,
                    competition_slug=comp_slug,
                    start_time=link.get("starttime"),
                    status_id=_extract_int(link.get("data-status-id"), None),
                    time_display=time_display,
                    tv_network=tv_network or None,
                    url=link.get("href"),
                    home_team=home_team,
                    away_team=away_team,
                )
            )

    return matches


def parse_standings_html(html_text: str) -> list[BeSoccerStandingRow]:
    """
    Parse competition standings rows from a BeSoccer standings HTML document.
    """
    if not html_text:
        return []
    doc = html.fromstring(html_text)
    rows: list[BeSoccerStandingRow] = []

    for tr in doc.iter("tr"):
        if "row-body" not in (tr.get("class") or ""):
            continue
        tds = tr.findall("td")
        if len(tds) < 11:
            continue

        pos = _extract_int(tds[0].text_content(), 0)
        imgs = list(tds[1].iter("img"))
        crest_url = imgs[0].get("src") if imgs else None
        team_id = _extract_int(crest_url, None) if crest_url else None

        name_td = tds[2]
        name_spans = [
            s for s in name_td.iter("span") if "team-name" in (s.get("class") or "")
        ]
        team_name = (
            name_spans[0].text_content().strip()
            if name_spans
            else name_td.text_content().strip()
        )
        links = list(name_td.iter("a"))
        team_slug = _slug_from_href(links[0].get("href")) if links else None
        form = [
            s.text_content().strip()
            for s in name_td.iter("span")
            if "bg-match-res" in (s.get("class") or "")
        ]

        rows.append(
            BeSoccerStandingRow(
                position=pos,
                team=BeSoccerTeam(
                    id=team_id,
                    name=team_name,
                    slug=team_slug,
                    crest_url=crest_url,
                ),
                points=_extract_int(tds[3].text_content(), 0),
                played=_extract_int(tds[4].text_content(), 0),
                won=_extract_int(tds[5].text_content(), 0),
                drawn=_extract_int(tds[6].text_content(), 0),
                lost=_extract_int(tds[7].text_content(), 0),
                goals_for=_extract_int(tds[8].text_content(), 0),
                goals_against=_extract_int(tds[9].text_content(), 0),
                goal_diff=_extract_int(tds[10].text_content(), 0),
                form=form,
            )
        )

    return rows
