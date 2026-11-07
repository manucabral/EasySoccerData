"""
Endpoints for the ESPN Soccer API.
"""

from __future__ import annotations

from urllib.parse import quote


class ESPNEndpoints:
    """
    Endpoints for the ESPN public soccer API.
    """

    def __init__(
        self,
        site_base_url: str = "https://site.api.espn.com/apis/site/v2/sports/soccer",
        v2_base_url: str = "https://site.api.espn.com/apis/v2/sports/soccer",
    ) -> None:
        self.site_base_url = site_base_url.rstrip("/")
        self.v2_base_url = v2_base_url.rstrip("/")

    def scoreboard(
        self, league: str = "all", dates: str | None = None, *, limit: int | None = None
    ) -> str:
        """
        Return the scoreboard URL for a league (e.g. ``"arg.1"``, ``"eng.1"``,
        ``"esp.1"``, ``"uefa.champions"``, ``"conmebol.libertadores"``, ``"all"``).
        ``dates`` uses ``YYYYMMDD`` format.
        """
        url = f"{self.site_base_url}/{quote(league)}/scoreboard"
        if dates:
            url += f"?dates={quote(dates)}"
        if limit is not None:
            url += ("&" if dates else "?") + f"limit={limit}"
        return url

    def summary(self, event_id: int | str, league: str = "all") -> str:
        """
        Return the match summary URL for an event ID.
        """
        return f"{self.site_base_url}/{quote(league)}/summary?event={event_id}"

    def standings(self, league: str = "arg.1", season: int | str | None = None) -> str:
        """
        Return the standings URL for a league.
        """
        url = f"{self.v2_base_url}/{quote(league)}/standings"
        if season is not None:
            url += f"?season={season}"
        return url

    def teams(self, league: str = "arg.1") -> str:
        """
        Return the teams list URL for a league.
        """
        return f"{self.site_base_url}/{quote(league)}/teams"
