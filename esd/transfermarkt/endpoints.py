"""
Endpoints for Transfermarkt API and web search.
"""

from __future__ import annotations

from urllib.parse import quote


class TransfermarktEndpoints:
    """
    Endpoints for the Transfermarkt API and search page.
    """

    def __init__(
        self,
        api_base_url: str = "https://tmapi-alpha.transfermarkt.technology",
        web_base_url: str = "https://www.transfermarkt.com",
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.web_base_url = web_base_url.rstrip("/")

    def player_profile(self, player_id: int | str) -> str:
        """
        Return the player profile API endpoint.
        """
        return f"{self.api_base_url}/player/{player_id}"

    def player_market_value_history(self, player_id: int | str) -> str:
        """
        Return the player market value history API endpoint.
        """
        return f"{self.api_base_url}/player/{player_id}/market-value-history"

    def player_transfer_history(self, player_id: int | str) -> str:
        """
        Return the player transfer history API endpoint.
        """
        return f"{self.api_base_url}/transfer/history/player/{player_id}"

    def club_profile(self, club_id: int | str) -> str:
        """
        Return the club profile API endpoint.
        """
        return f"{self.api_base_url}/club/{club_id}"

    def search(self, query: str) -> str:
        """
        Return the web quick-search URL.
        """
        return (
            f"{self.web_base_url}/schnellsuche/ergebnis/schnellsuche"
            f"?query={quote(query)}"
        )
