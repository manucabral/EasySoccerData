"""
This module contains the endpoints to interact with the FBref website.
"""


class FBrefEndpoints:
    """
    A class to represent the endpoints to interact with the FBref website.
    """

    def __init__(
        self, base_url: str = "https://fbref.com", language: str = "en"
    ) -> None:
        """
        Initializes the FBref endpoints.
        """
        self.language = language
        self.base_url = base_url + "/" + language

    @property
    def matchs_endpoint(self) -> str:
        """
        Returns the URL of the endpoint to get the scheduled matchs.
        """
        return self.base_url + "/matches/{date}"

    @property
    def match_details_endpoint(self) -> str:
        """
        Returns the URL of the endpoint to get the match details.
        """
        return self.base_url + "/{match_id}"

    @property
    def league_players_endpoint(self) -> str:
        """
        Returns the URL of the endpoint to get league player stats.
        Format args: comp_id, league_slug, stat_type.
        stat_type selects the FBref stat category (e.g. "stats",
        "shooting", "passing", "defense", "possession").
        Example: /en/comps/9/stats/Premier-League-Stats
        """
        return self.base_url + "/comps/{comp_id}/{stat_type}/{league_slug}-Stats"
