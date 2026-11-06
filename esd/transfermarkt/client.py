"""
Client for interacting with Transfermarkt.
"""

from __future__ import annotations

from .service import TransfermarktService
from .types import (
    TMClub,
    TMMarketValueEntry,
    TMPlayer,
    TMSearchItem,
    TMTransfer,
)


class TransfermarktClient:
    """
    Client for fetching player market values, transfer histories and club
    valuations from Transfermarkt.
    """

    def __init__(self, proxies: dict | None = None) -> None:
        """
        Initialize the Transfermarkt client.

        Args:
            proxies: Optional proxy dictionary.
        """
        self.__service = TransfermarktService(proxies=proxies)

    def get_player(self, player_id: int | str) -> TMPlayer:
        """
        Get a player's profile and current market valuation (e.g. ``"28003"``).
        """
        return self.__service.get_player(player_id)

    def get_player_market_value_history(
        self, player_id: int | str
    ) -> list[TMMarketValueEntry]:
        """
        Get historical market value progression for a player.
        """
        return self.__service.get_player_market_value_history(player_id)

    def get_player_transfers(self, player_id: int | str) -> list[TMTransfer]:
        """
        Get complete transfer history for a player.
        """
        return self.__service.get_player_transfers(player_id)

    def get_club(self, club_id: int | str) -> TMClub:
        """
        Get club details and squad market valuation summary (e.g. ``"281"``).
        """
        return self.__service.get_club(club_id)

    def search(self, query: str) -> list[TMSearchItem]:
        """
        Search for players, clubs and competitions on Transfermarkt.
        """
        return self.__service.search(query)
