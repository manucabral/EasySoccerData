"""
Transfermarkt service module.
"""

from __future__ import annotations

from ..utils import TTLCache, get_api_json, get_text
from .endpoints import TransfermarktEndpoints
from .types import (
    TMClub,
    TMMarketValueEntry,
    TMPlayer,
    TMSearchItem,
    TMTransfer,
    parse_club,
    parse_market_value_history,
    parse_player,
    parse_search_html,
    parse_transfer_history,
)


class TransfermarktService:
    """
    Service layer for fetching and parsing Transfermarkt data.
    """

    def __init__(self, proxies: dict | None = None) -> None:
        self.proxies = proxies
        self.endpoints = TransfermarktEndpoints()
        self._cache = TTLCache(ttl=60.0)

    def _fetch_json(self, url: str) -> dict:
        cached = self._cache.get(url)
        if cached is not None:
            return cached
        data = get_api_json(url, proxies=self.proxies)
        self._cache.set(url, data)
        return data

    def get_player(self, player_id: int | str) -> TMPlayer:
        """
        Get player profile and current market valuation by Transfermarkt player ID.
        """
        data = self._fetch_json(self.endpoints.player_profile(player_id))
        return parse_player(data)

    def get_player_market_value_history(
        self, player_id: int | str
    ) -> list[TMMarketValueEntry]:
        """
        Get historical market value timeline for a player ID.
        """
        data = self._fetch_json(self.endpoints.player_market_value_history(player_id))
        return parse_market_value_history(data)

    def get_player_transfers(self, player_id: int | str) -> list[TMTransfer]:
        """
        Get complete transfer history for a player ID.
        """
        data = self._fetch_json(self.endpoints.player_transfer_history(player_id))
        return parse_transfer_history(data)

    def get_club(self, club_id: int | str) -> TMClub:
        """
        Get club profile and squad valuation summary by club ID.
        """
        data = self._fetch_json(self.endpoints.club_profile(club_id))
        return parse_club(data)

    def search(self, query: str) -> list[TMSearchItem]:
        """
        Search players, clubs and competitions by name.
        """
        url = self.endpoints.search(query)
        cached = self._cache.get(url)
        if cached is None:
            cached = get_text(url, proxies=self.proxies)
            self._cache.set(url, cached)
        return parse_search_html(cached)
