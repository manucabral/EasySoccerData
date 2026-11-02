"""
FBref service module.
"""

from __future__ import annotations

from ..logger import get_logger
from ..utils import (
    get_document,
    get_document_impersonate,
    get_document_playwright,
    get_today,
)
from .endpoints import FBrefEndpoints
from .exceptions import InvalidMatchId
from .types import Match, MatchDetails, parse_match_details, parse_matchs
from .types.league import LeaguePlayerStandard, parse_league_players
from .utils import rate_limit

_logger = get_logger("fbref.service")


class FBrefService:
    """
    A class to represent the FBref service.
    """

    def __init__(
        self,
        language: str = "en",
        proxies: dict = None,
        use_playwright: bool = False,
        use_curl_cffi: bool = True,
        chrome_path: str = None,
        impersonate: str = "chrome",
        delay: float = 3.0,
        headless: bool = False,
    ) -> None:
        """
        Initializes the FBref service.

        Args:
            language: The language for FBref URLs (e.g. 'en', 'es').
            proxies: Optional proxy dict.
            use_playwright: If True, uses Playwright with system Chrome.
                Defaults to False (curl_cffi is preferred for FBref).
            use_curl_cffi: If True, uses curl_cffi with browser impersonation
                to bypass Cloudflare. Defaults to True.
            chrome_path: Optional path to Chrome executable.
            impersonate: Browser fingerprint string for curl_cffi
                (default "chrome").
            delay: Minimum seconds between requests (default 3.0).
            headless: Run Playwright headless. Defaults to False. Headful
                Chrome is required to pass Cloudflare's challenge.
        """
        self.proxies: dict = proxies or None
        self.use_playwright: bool = use_playwright
        self.use_curl_cffi: bool = use_curl_cffi
        self.chrome_path: str = chrome_path
        self.impersonate: str = impersonate
        self.delay: float = delay
        self.headless: bool = headless
        self.endpoints: FBrefEndpoints = FBrefEndpoints(language=language)

    def _fetch_document(self, url: str):
        """Fetch a document using configured backends with fallback."""
        from lxml import html as lxml_html

        from .exceptions import CloudflareBlock

        backends = []
        blocked_backends = []
        if self.use_curl_cffi:
            backends.append(("curl_cffi", lambda: get_document_impersonate(
                self.proxies, url, impersonate=self.impersonate, delay=self.delay,
            )))
        if self.use_playwright:
            backends.append(("playwright", lambda: get_document_playwright(
                url, self.chrome_path, self.proxies, wait_until="load",
                headless=self.headless,
            )))
        if not backends:
            backends.append(("httpx", lambda: get_document(self.proxies, url)))

        last_error = None
        for name, fetcher in backends:
            _logger.debug("trying backend: %s for %s", name, url)
            try:
                doc = fetcher()
                if doc is not None and doc.find(".//body") is not None:
                    return doc
                _logger.warning("backend %s returned empty/blocked for %s", name, url)
                blocked_backends.append(name)
            except Exception as exc:
                _logger.debug("backend %s failed: %s", name, exc)
                last_error = exc
                continue

        if last_error:
            raise last_error
        if blocked_backends:
            raise CloudflareBlock(
                f"All backends blocked by Cloudflare or returned empty: "
                f"{', '.join(blocked_backends)}. "
                f"Try a VPN, proxy, or non-headless browser. URL: {url}"
            )
        return lxml_html.fromstring("<html><body></body></html>")

    @rate_limit(calls=9, period=60)
    def get_matchs(self, date: str = None) -> list[Match]:
        """
        Get the scheduled matchs.

        Args:
            date (str): The date of the matchs in the format "YYYY-MM-DD".

        Returns:
            list[Match]: The scheduled
        """
        try:
            if not date:
                date = get_today()
            url = self.endpoints.matchs_endpoint.format(date=date)
            _logger.debug(
                "fetching matches from %s (playwright=%s, cffi=%s)",
                url, self.use_playwright, self.use_curl_cffi,
            )
            document = self._fetch_document(url)
            matches = parse_matchs(document)
            _logger.debug("parsed %d matches from %s", len(matches), url)
            return matches
        except Exception as exc:
            raise exc

    @rate_limit(calls=9, period=60)
    def get_match_details(self, match_id: str) -> MatchDetails:
        """
        Get the match details.

        Args:
            match_id (str): The match id.

        Returns:
            MatchDetails: The match details.

        Raises:
            InvalidMatchId: If the match id is invalid.
        """
        if "matches" not in match_id:
            raise InvalidMatchId(match_id)
        try:
            url = self.endpoints.match_details_endpoint.format(match_id=match_id)
            _logger.debug(
                "fetching match details from %s (playwright=%s, cffi=%s)",
                url, self.use_playwright, self.use_curl_cffi,
            )
            document = self._fetch_document(url)
            return parse_match_details(document)
        except Exception as exc:
            raise exc

    @rate_limit(calls=9, period=60)
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
        try:
            url = self.endpoints.league_players_endpoint.format(
                comp_id=comp_id, league_slug=league_slug
            )
            _logger.debug(
                "fetching league players from %s (playwright=%s, cffi=%s)",
                url, self.use_playwright, self.use_curl_cffi,
            )
            document = self._fetch_document(url)
            players = parse_league_players(document, table_id=table_id)
            _logger.debug("parsed %d players from %s", len(players), url)
            return players
        except Exception as exc:
            raise exc
