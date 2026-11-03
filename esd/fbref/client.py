"""
This module contains the client class for interacting with the FBref website.
"""

from __future__ import annotations

from ..logger import get_logger
from .service import FBrefService
from .types import Match, MatchDetails
from .types.league import LeaguePlayerStandard

_logger = get_logger("fbref.client")


class FBrefClient:
    """
    A class to represent the client for interacting with the FBref website.
    """

    def __init__(
        self,
        language: str = "en",
        proxies: dict = None,
        use_playwright: bool = False,
        chrome_path: str = None,
        use_curl_cffi: bool = True,
        impersonate: str = "chrome",
        delay: float = 3.0,
        headless: bool = False,
    ) -> None:
        """
        Initializes the FBref client.

        Args:
            language: The language for FBref URLs (e.g. 'en', 'es').
            proxies: Optional proxy dict.
            use_playwright: If True, uses Playwright with system Chrome
                instead of httpx. No 'playwright install' needed.
                Defaults to False (curl_cffi is preferred for FBref).
            chrome_path: Optional path to Chrome executable.
            use_curl_cffi: If True, uses curl_cffi with browser impersonation
                to bypass Cloudflare. Defaults to True.
            impersonate: Browser fingerprint for curl_cffi (default "chrome").
            delay: Minimum seconds between requests (default 3.0).
            headless: Run Playwright headless. Defaults to False. Headful
                Chrome is required to pass Cloudflare's challenge.
        """
        self.__service = FBrefService(
            language=language,
            proxies=proxies,
            use_playwright=use_playwright,
            chrome_path=chrome_path,
            use_curl_cffi=use_curl_cffi,
            impersonate=impersonate,
            delay=delay,
            headless=headless,
        )
        _logger.debug(
            "initialized with language=%s playwright=%s cffi=%s",
            language,
            use_playwright,
            use_curl_cffi,
        )

    def get_matchs(self, date: str = None) -> list[Match]:
        """
        Get the scheduled matchs.

        Args:
            date (str): The date of the matchs in the format "YYYY-MM-DD".

        Returns:
            list[Match]: The scheduled matchs.
        """
        return self.__service.get_matchs(date)

    def get_match_details(self, match_id: str) -> MatchDetails:
        """
        Get the match report.

        Args:
            match_id (str): The match id.

        Returns:
            MatchDetails: The match details.
        """
        return self.__service.get_match_details(match_id)

    def get_league_players(
        self,
        comp_id: int,
        league_slug: str,
        table_id: str = "stats_standard",
    ) -> list[LeaguePlayerStandard]:
        """
        Get player statistics for a league/competition.

        Args:
            comp_id: The competition ID on FBref (e.g. 9 for Premier League).
            league_slug: The league slug (e.g. "Premier-League").
            table_id: The HTML table id to parse (default "stats_standard").
                Other options: "stats_shooting", "stats_passing", etc.

        Returns:
            list[LeaguePlayerStandard]: Parsed player statistics rows.
        """
        return self.__service.get_league_players(comp_id, league_slug, table_id=table_id)

    def close(self) -> None:
        """Close the reused browser, if any."""
        self.__service.close()
