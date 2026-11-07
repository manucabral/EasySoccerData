"""
Endpoints for Transfermarkt API and web search.
"""

from __future__ import annotations

import re
from urllib.parse import quote, urlsplit


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

    def search(self, query: str, page: int = 1) -> str:
        """
        Return the web quick-search URL.
        """
        url = (
            f"{self.web_base_url}/schnellsuche/ergebnis/schnellsuche"
            f"?query={quote(query)}"
        )
        return url if page == 1 else f"{url}&Wettbewerb_page={page}"

    def competition_seasons(self, competition_id: str, competition_url: str) -> str:
        """Build the season-selector page from a native competition search link.

        The link supplies the slug and league/cup route, which the ID alone does
        not establish. Only an official competition URL with the selected ID is accepted.
        """
        if not isinstance(competition_url, str):
            raise ValueError("Transfermarkt seasons require competition_url from a search result")
        parsed = urlsplit(competition_url)
        match = re.fullmatch(r"/([a-zA-Z0-9-]+)/(?:startseite|gesamtspielplan)/(pokalwettbewerb|wettbewerb)/([A-Za-z0-9]+)", parsed.path)
        if (parsed.scheme != "https" or parsed.netloc != "www.transfermarkt.com"
                or parsed.query or parsed.fragment or match is None or match[3] != competition_id):
            raise ValueError("competition_url must be an official Transfermarkt competition link matching competition_id")
        action = "gesamtspielplan" if match[2] == "pokalwettbewerb" else "startseite"
        return f"{self.web_base_url}/{match[1]}/{action}/{match[2]}/{competition_id}"
