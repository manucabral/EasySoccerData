"""
365Scores search dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SearchEntity:
    """
    An entity returned by 365Scores search.
    """

    id: int = None
    name: str = None
    short_name: str = None
    sport_id: int = None
    country_id: int = None
    entity_type: str = None


@dataclass
class SearchResult:
    """
    Grouped search results from 365Scores.
    """

    competitions: list[SearchEntity] = field(default_factory=list)
    competitors: list[SearchEntity] = field(default_factory=list)
    athletes: list[SearchEntity] = field(default_factory=list)


def _parse_entities(items: list[dict], entity_type: str) -> list[SearchEntity]:
    return [
        SearchEntity(
            id=item.get("id"),
            name=item.get("name"),
            short_name=item.get("shortName") or item.get("name"),
            sport_id=item.get("sportId"),
            country_id=item.get("countryId"),
            entity_type=entity_type,
        )
        for item in (items or [])
    ]


def parse_search(data: dict) -> SearchResult:
    """
    Parse a 365Scores search response.
    """
    if not data:
        return SearchResult()
    return SearchResult(
        competitions=_parse_entities(data.get("competitions", []), "competition"),
        competitors=_parse_entities(data.get("competitors", []), "competitor"),
        athletes=_parse_entities(data.get("athletes", []), "athlete"),
    )
