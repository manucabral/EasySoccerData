"""
Endpoints for BeSoccer.
"""

from urllib.parse import quote


class BeSoccerEndpoints:
    """
    Endpoints for BeSoccer web pages.
    """

    def __init__(self, base_url: str = "https://es.besoccer.com") -> None:
        self.base_url = base_url.rstrip("/")

    def livescore(self, date: str | None = None) -> str:
        """
        Return the livescore URL for ``"today"`` or a ``"YYYY-MM-DD"`` date.
        """
        if not date or date.lower() == "today":
            return f"{self.base_url}/livescore"
        return f"{self.base_url}/livescore/{quote(date)}"

    def standings(self, competition_slug: str, season: int | str | None = None) -> str:
        """
        Return the competition standings URL (e.g. ``"torneo_final"``,
        ``"primera_division"``, ``"premier_league"``).
        """
        url = f"{self.base_url}/competicion/clasificacion/{quote(competition_slug)}"
        if season is not None:
            url += f"/{season}"
        return url
