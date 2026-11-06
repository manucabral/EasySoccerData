"""
Transfermarkt dataclasses and parsers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from lxml import html

_HREF_ID_RE = re.compile(
    r"/(?P<slug>[^/]+)/(?:profil/spieler|startseite/verein|startseite/wettbewerb)/(?P<id>[A-Za-z0-9]+)"
)


def _format_compact(mv_dict: dict | None) -> str | None:
    if not isinstance(mv_dict, dict):
        return None
    compact = mv_dict.get("compact")
    if isinstance(compact, dict):
        prefix = compact.get("prefix") or ""
        content = compact.get("content") or ""
        suffix = compact.get("suffix") or ""
        res = f"{prefix}{content}{suffix}".strip()
        return res or None
    return None


@dataclass
class TMPlayer:
    """
    A player profile from Transfermarkt.
    """

    id: str = None
    name: str = None
    full_name: str = None
    age: int | None = None
    date_of_birth: str = None
    height: float | None = None
    preferred_foot: str = None
    position: str = None
    position_short: str = None
    position_group: str = None
    contract_until: str = None
    current_club_id: str = None
    shirt_number: int | None = None
    is_captain: bool = False
    market_value: int | None = None
    market_value_currency: str = None
    market_value_display: str = None
    highest_market_value: int | None = None
    highest_market_value_date: str = None
    portrait_url: str = None
    relative_url: str = None


@dataclass
class TMMarketValueEntry:
    """
    A single point in a player's market value history.
    """

    player_id: str = None
    club_id: str = None
    season_id: int | None = None
    age: int | None = None
    date: str = None
    value: int | None = None
    currency: str = None
    display: str = None


@dataclass
class TMTransfer:
    """
    A single transfer in a player's transfer history.
    """

    id: str = None
    player_id: str = None
    season: str = None
    date: str = None
    age: int | None = None
    from_club_id: str = None
    from_competition_id: str = None
    to_club_id: str = None
    to_competition_id: str = None
    market_value: int | None = None
    market_value_display: str = None
    fee: int | None = None
    fee_display: str = None
    is_pending: bool = False
    transfer_type: str = None


@dataclass
class TMClub:
    """
    A club profile and squad valuation summary from Transfermarkt.
    """

    id: str = None
    name: str = None
    short_name: str = None
    abbreviation: str = None
    country_id: int | None = None
    competition_id: str = None
    stadium_street: str = None
    city: str = None
    squad_size: int = 0
    average_age: float | None = None
    current_market_value: int | None = None
    current_market_value_display: str = None
    average_market_value: int | None = None
    crest_url: str = None
    colors: list[str] = field(default_factory=list)


@dataclass
class TMSearchItem:
    """
    An entity returned by Transfermarkt search.
    """

    id: str = None
    name: str = None
    slug: str = None
    entity_type: str = None
    relative_url: str = None


def parse_player(payload: dict) -> TMPlayer:
    """
    Parse a Transfermarkt player API response.
    """
    data = (payload or {}).get("data") or payload or {}
    if not data:
        return TMPlayer()
    life = data.get("lifeDates") or {}
    nat = data.get("nationalityDetails") or {}
    attrs = data.get("attributes") or {}
    foot_obj = attrs.get("preferredFoot") or {}
    pos_obj = attrs.get("position") or {}
    mv_details = data.get("marketValueDetails") or {}
    curr_mv = mv_details.get("current") or {}
    high_mv = mv_details.get("highest") or {}
    assignments = data.get("clubAssignments") or []
    current_assign = next(
        (a for a in assignments if a.get("type") == "current"),
        assignments[0] if assignments else {},
    )
    return TMPlayer(
        id=str(data.get("id")) if data.get("id") is not None else None,
        name=data.get("name"),
        full_name=nat.get("passportName") or data.get("name"),
        age=life.get("age"),
        date_of_birth=life.get("dateOfBirth"),
        height=attrs.get("height"),
        preferred_foot=foot_obj.get("name"),
        position=pos_obj.get("name"),
        position_short=pos_obj.get("shortName"),
        position_group=attrs.get("positionGroupName") or attrs.get("positionGroup"),
        contract_until=attrs.get("contractUntil"),
        current_club_id=current_assign.get("clubId") or data.get("lastClubId"),
        shirt_number=current_assign.get("shirtNumber"),
        is_captain=bool(current_assign.get("isCaptain", False)),
        market_value=curr_mv.get("value"),
        market_value_currency=curr_mv.get("currency"),
        market_value_display=_format_compact(curr_mv),
        highest_market_value=high_mv.get("value"),
        highest_market_value_date=high_mv.get("determined"),
        portrait_url=data.get("portraitUrl"),
        relative_url=data.get("relativeUrl"),
    )


def parse_market_value_history(payload: dict) -> list[TMMarketValueEntry]:
    """
    Parse a player's market value history API response.
    """
    data = (payload or {}).get("data") or payload or {}
    history = data.get("history") if isinstance(data, dict) else []
    entries: list[TMMarketValueEntry] = []
    for item in history or []:
        mv = item.get("marketValue") or {}
        entries.append(
            TMMarketValueEntry(
                player_id=str(item.get("playerId"))
                if item.get("playerId") is not None
                else None,
                club_id=str(item.get("clubId"))
                if item.get("clubId") is not None
                else None,
                season_id=item.get("seasonId"),
                age=item.get("age"),
                date=mv.get("determined"),
                value=mv.get("value"),
                currency=mv.get("currency"),
                display=_format_compact(mv),
            )
        )
    return entries


def parse_transfer_history(payload: dict) -> list[TMTransfer]:
    """
    Parse a player's transfer history API response.
    """
    data = (payload or {}).get("data") or payload or {}
    hist = data.get("history") if isinstance(data, dict) else {}
    if not isinstance(hist, dict):
        return []
    raw_items = (hist.get("pending") or []) + (hist.get("terminated") or [])
    transfers: list[TMTransfer] = []
    for item in raw_items:
        src = item.get("transferSource") or {}
        dst = item.get("transferDestination") or {}
        det = item.get("details") or {}
        mv = det.get("marketValue") or {}
        fee = det.get("fee") or {}
        season = det.get("season") or {}
        t_type = item.get("typeDetails") or {}
        transfers.append(
            TMTransfer(
                id=str(item.get("id")) if item.get("id") is not None else None,
                player_id=str(det.get("playerId"))
                if det.get("playerId") is not None
                else None,
                season=season.get("display") or str(det.get("seasonId") or ""),
                date=det.get("date"),
                age=det.get("age"),
                from_club_id=str(src.get("clubId"))
                if src.get("clubId") is not None
                else None,
                from_competition_id=src.get("competitionId"),
                to_club_id=str(dst.get("clubId"))
                if dst.get("clubId") is not None
                else None,
                to_competition_id=dst.get("competitionId"),
                market_value=mv.get("value"),
                market_value_display=_format_compact(mv),
                fee=fee.get("value"),
                fee_display=_format_compact(fee),
                is_pending=bool(det.get("isPending", False)),
                transfer_type=t_type.get("type"),
            )
        )
    return transfers


def parse_club(payload: dict) -> TMClub:
    """
    Parse a Transfermarkt club API response.
    """
    data = (payload or {}).get("data") or payload or {}
    if not data:
        return TMClub()
    base = data.get("baseDetails") or {}
    sup = base.get("superiorClub") or {}
    loc = sup.get("location") or {}
    colors_dict = sup.get("colors") or {}
    colors = [
        c
        for c in (
            colors_dict.get("firstColor"),
            colors_dict.get("secondColor"),
            colors_dict.get("thirdColor"),
        )
        if c
    ]
    squad = data.get("squadDetails") or {}
    curr_mv = squad.get("currentMarketValue") or {}
    avg_mv = squad.get("averageMarketValue") or {}
    return TMClub(
        id=str(data.get("id")) if data.get("id") is not None else None,
        name=data.get("name"),
        short_name=base.get("shortName") or data.get("name"),
        abbreviation=base.get("abbreviation"),
        country_id=base.get("countryId"),
        competition_id=base.get("primaryCompetitionId")
        or data.get("relevantCompetitionId"),
        stadium_street=loc.get("street"),
        city=loc.get("city"),
        squad_size=int(squad.get("squadSize", 0) or 0),
        average_age=squad.get("averageAge"),
        current_market_value=curr_mv.get("value"),
        current_market_value_display=_format_compact(curr_mv),
        average_market_value=avg_mv.get("value"),
        crest_url=data.get("crestUrl"),
        colors=colors,
    )


def parse_search_html(html_text: str) -> list[TMSearchItem]:
    """
    Parse Transfermarkt quick-search HTML into :class:`TMSearchItem` objects.
    """
    if not html_text:
        return []
    doc = html.fromstring(html_text)
    results: list[TMSearchItem] = []
    seen: set[tuple[str, str]] = set()
    for link in doc.xpath("//td[contains(@class, 'hauptlink')]/a"):
        href = link.get("href") or ""
        match = _HREF_ID_RE.search(href)
        if not match:
            continue
        entity_id = match.group("id")
        slug = match.group("slug")
        if "/spieler/" in href:
            etype = "player"
        elif "/verein/" in href:
            etype = "club"
        else:
            etype = "competition"
        key = (etype, entity_id)
        if key in seen:
            continue
        seen.add(key)
        results.append(
            TMSearchItem(
                id=entity_id,
                name=link.text_content().strip(),
                slug=slug,
                entity_type=etype,
                relative_url=href,
            )
        )
    return results
