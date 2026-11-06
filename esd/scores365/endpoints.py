"""
This module contains the endpoints of the 365Scores API.
"""

from __future__ import annotations

from urllib.parse import quote


class Scores365Endpoints:
    """
    Endpoints of the 365Scores web API.
    """

    def __init__(
        self,
        base_url: str = "https://webws.365scores.com/web",
        lang_id: int = 14,
        timezone_name: str = "America/Argentina/Buenos_Aires",
        country_id: int = 31,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.lang_id = lang_id
        self.timezone_name = timezone_name
        self.country_id = country_id

    @property
    def _common_params(self) -> str:
        tz = quote(self.timezone_name, safe="/")
        return (
            f"appTypeId=5&langId={self.lang_id}"
            f"&timezoneName={tz}&userCountryId={self.country_id}"
        )

    def games_allscores(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        competition_id: int | None = None,
    ) -> str:
        """
        Return the allscores URL for a given date range or competition.
        Dates use ``DD/MM/YYYY`` format.
        """
        url = f"{self.base_url}/games/allscores/?{self._common_params}&sports=1"
        if start_date:
            url += f"&startDate={quote(start_date)}"
        if end_date:
            url += f"&endDate={quote(end_date)}"
        if competition_id is not None:
            url += f"&competitions={competition_id}"
        return url

    def game_detail(self, game_id: int) -> str:
        """
        Return the detail URL for a single match.
        """
        return f"{self.base_url}/game/?{self._common_params}&gameId={game_id}"

    def game_stats(self, game_id: int) -> str:
        """
        Return the match statistics URL for a single match.
        """
        return f"{self.base_url}/game/stats/?{self._common_params}&games={game_id}"

    def standings(self, competition_id: int) -> str:
        """
        Return the standings URL for a competition.
        """
        return (
            f"{self.base_url}/standings/?"
            f"{self._common_params}&competitions={competition_id}"
        )

    def search(self, query: str) -> str:
        """
        Return the search URL for teams, competitions and athletes.
        """
        return f"{self.base_url}/search/?{self._common_params}&query={quote(query)}"
