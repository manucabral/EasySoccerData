"""Verified HTML structures used by competition and season discovery."""

from __future__ import annotations

from urllib.parse import urljoin, urlsplit

from lxml import etree, html

from .exceptions import SourceBlocked, SourceError
from .transfermarkt.endpoints import TransfermarktEndpoints
from .transfermarkt.types import parse_search_html


def _document(data):
    raw = data.get("html") if isinstance(data, dict) else None
    if not isinstance(raw, str) or not raw.strip():
        raise SourceError("Discovery response is missing its HTML document")
    if any(marker in raw[:4000].lower() for marker in ("client challenge", "just a moment", "cf-chl-")):
        raise SourceBlocked("Discovery returned a browser challenge")
    try:
        return html.fromstring(raw)
    except (etree.ParserError, ValueError) as exc:
        raise SourceError("Invalid discovery HTML") from exc


def transfermarkt_competitions(data, page=1):
    """Read only the competition search grid, including league and cup routes."""
    doc = _document(data)
    grids = doc.xpath("//*[@id='competition-grid']")
    if not grids:
        if doc.xpath("//section[contains(concat(' ', normalize-space(@class), ' '), ' no-result ')]"):
            return {"competitions": []}
        if (doc.xpath("//form[@action='/schnellsuche/ergebnis/schnellsuche']")
                and doc.xpath("//*[@id='player-grid' or @id='club-grid' or @id='coach-grid' or @id='agent-grid']//table/tbody")):
            return {"competitions": []}
        raise SourceError("Transfermarkt response is missing its competition search grid")
    if len(grids) != 1 or not grids[0].xpath(".//table/tbody"):
        raise SourceError("Invalid Transfermarkt competition search grid")
    active = grids[0].xpath(".//*[contains(concat(' ', normalize-space(@class), ' '), ' tm-pagination__list-item--active ')]/a")
    if active:
        values = [node.text_content().strip() for node in active]
        if values != [str(page)]:
            raise SourceError("Transfermarkt returned a different competition search page")
    elif page != 1 or grids[0].xpath(".//*[contains(concat(' ', normalize-space(@class), ' '), ' tm-pagination ')]"):
        raise SourceError("Transfermarkt response does not establish the selected competition search page")
    rows = []
    for item in parse_search_html(html.tostring(grids[0], encoding="unicode")):
        if item.entity_type != "competition" or not item.name:
            raise SourceError("Invalid entry in Transfermarkt competition search grid")
        link = urljoin("https://www.transfermarkt.com", item.relative_url)
        TransfermarktEndpoints().competition_seasons(item.id, link)
        rows.append({"id": item.id, "name": item.name, "source_url": link})
    native_rows = grids[0].xpath(".//tbody/tr[td[not(contains(@class, 'empty'))]]")
    if len(rows) != len(native_rows):
        raise SourceError("Transfermarkt competition entries could not all be parsed")
    return {"competitions": rows}


def html_seasons(data, source, competition):
    """Read a provider's actual selector, checking its competition context."""
    doc = _document(data)
    if source == "besoccer":
        selects = doc.xpath("//select[@name='season'][@id='season']")
        if len(selects) != 1:
            raise SourceError("BeSoccer response is missing its season selector")
        route = urlsplit(selects[0].get("data-url", ""))
        if (route.netloc != "es.besoccer.com" or route.scheme != "https"
                or route.path != f"/competicion/clasificacion/{competition}/NNN"):
            raise SourceError("BeSoccer season selector does not belong to the selected competition")
    else:
        selects = doc.xpath("//select[@name='saison_id']")
        if len(selects) != 1:
            raise SourceError("Transfermarkt response is missing its season selector")
        forms = selects[0].xpath("ancestor::form/@action")
        if len(forms) != 1:
            raise SourceError("Transfermarkt season selector is missing its competition form")
        link = urljoin("https://www.transfermarkt.com", forms[0].removesuffix("/plus/"))
        try:
            TransfermarktEndpoints().competition_seasons(competition, link)
        except ValueError as exc:
            raise SourceError("Transfermarkt season selector does not belong to the selected competition") from exc
    rows = []
    for option in selects[0].xpath("./option"):
        value = option.get("value", "")
        name = " ".join(option.text_content().split())
        if not value.isascii() or not value.isdigit() or len(value) != 4 or not name or int(value) < 1000:
            raise SourceError(f"Invalid {source} native season option")
        rows.append({"id": value, "name": name})
    return {"seasons": rows}
