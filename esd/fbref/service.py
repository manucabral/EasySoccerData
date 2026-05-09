"""
FBref service module.
"""

from __future__ import annotations

from ..utils import get_document, get_today
from .endpoints import FBrefEndpoints
from .exceptions import InvalidMatchId
from .types import Match, MatchDetails, parse_match_details, parse_matchs
from .utils import rate_limit


class FBrefService:
    """
    A class to represent the FBref service.
    """

    def __init__(self, language: str = "en", proxies: dict = None) -> None:
        """
        Initializes the FBref service.
        """
        self.proxies: dict = proxies or None
        self.endpoints: FBrefEndpoints = FBrefEndpoints(language=language)

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
            document = get_document(self.proxies, url)
            return parse_matchs(document)
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
            document = get_document(self.proxies, url)
            return parse_match_details(document)
        except Exception as exc:
            raise exc
