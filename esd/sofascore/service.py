"""
Sofascore service module
"""

from __future__ import annotations
import playwright
from ..utils import get_json, get_today
from .endpoints import SofascoreEndpoints
from .types import (
    Event,
    parse_event,
    parse_events,
    parse_player,
    parse_player_attributes,
    parse_transfer_history,
    parse_team,
    parse_tournament,
    parse_tournaments,
    parse_seasons,
    parse_brackets,
    parse_standings,
    parse_incidents,
    parse_top_players_match,
    parse_comments,
    parse_shots,
    parse_top_tournament_teams,
    parse_top_tournament_players,
    TopTournamentPlayers,
    TopTournamentTeams,
    Shot,
    Comment,
    TopPlayersMatch,
    Incident,
    Bracket,
    Season,
    Tournament,
    Standing,
    Team,
    Player,
    PlayerAttributes,
    TransferHistory,
    MatchStats,
    parse_match_stats,
    Lineups,
    parse_lineups,
    EntityType,
    Category,
)


class SofascoreService:
    """
    A class to represent the SofaScore service.
    """

    def __init__(self, browser_path: str):
        """
        Initializes the SofaScore service.
        """
        self.browser_path = (
            browser_path or r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        )
        self.endpoints = SofascoreEndpoints()
        self.playwright = self.browser = self.page = None
        self.__init_playwright()

    def __init_playwright(self):
        """
        Initialize the Playwright and browser instances.
        """
        try:
            self.playwright = playwright.sync_api.sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=True, executable_path=self.browser_path
            )
            self.page = self.browser.new_page()
        except Exception as exc:
            message = (
                f'{self.browser_path} is not a valid browser path. Is installed?'
            )
            raise RuntimeError(message) from exc

    def close(self):
        """
        Close the browser and playwright instances.
        """
        try:
            if self.page:
                self.page.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as exc:
            raise RuntimeError("Failed to close browser") from exc

    def __del__(self):
        """
        Destructor to ensure resources are released.
        """
        self.close()

    def get_event(self, event_id: int) -> Event:
        """
        Get the event information.

        Args:
            event_id (int): The event id.

        Returns:
            Event: The event information.
        """
        try:
            url = self.endpoints.event_endpoint(event_id)
            data = get_json(self.page, url)["event"]
            return parse_event(data)
        except Exception as exc:
            raise exc

    def get_events(self, date: str = 'today') -> list[Event]:
        """
        Get the scheduled events.

        Args:
            date (str): The date of the events in the format "YYYY-MM-DD".

        Returns:
            dict: The scheduled events.
        """
        if date is 'today':
            date = get_today()
        try:
            url = self.endpoints.events_endpoint.format(date=date)
            return parse_events(get_json(self.page, url)["events"])
        except Exception as exc:
            raise exc

    def get_live_events(self) -> list[Event]:
        """
        Get the live events.

        Returns:
            list[Event]: The live events.
        """
        try:
            url = self.endpoints.live_events_endpoint
            return parse_events(get_json(self.page, url)["events"])
        except Exception as exc:
            raise exc

    def get_player(self, player_id: int) -> Player:
        """
        Get the player information.

        Args:
            player_id (int): The player id.

        Returns:
            Player: The player information.
        """
        try:
            url = self.endpoints.player_endpoint(player_id)
            data = get_json(self.page, url)
            if "player" in data:
                player = parse_player(data["player"])
                player.attributes = self.get_player_attributes(player_id)
                player.transfer_history = self.get_player_transfer_history(player_id)
                return player
            return Player()
        except Exception as exc:
            raise exc

    def get_player_attributes(self, player_id: int) -> PlayerAttributes:
        """
        Get the player attributes.

        Args:
            player_id (int): The player id.

        Returns:
            dict: The player attributes.
        """
        try:
            url = self.endpoints.player_attributes_endpoint(player_id)
            data = get_json(self.page, url)
            if "playerAttributes" in data:
                return parse_player_attributes(data["playerAttributes"])
            return PlayerAttributes()
        except Exception as exc:
            raise exc

    def get_player_transfer_history(self, player_id: int) -> TransferHistory:
        """
        Get the player transfer history.

        Args:
            player_id (int): The player id.

        Returns:
            TransferHistory: The player transfer history.
        """
        try:
            url = self.endpoints.player_transfer_history_endpoint(player_id)
            data = get_json(self.page, url)
            if data is not None:
                return parse_transfer_history(data)
            return TransferHistory()
        except Exception as exc:
            raise exc

    def get_player_stats(self, player_id: int) -> dict:
        """
        TODO: Get the player statistics.

        Args:
            player_id (int): The player id.

        Returns:
            dict: The player statistics.
        """
        try:
            url = self.endpoints.player_stats_endpoint(player_id)
            return get_json(self.page, url)
        except Exception as exc:
            raise exc

    def get_match_lineups(self, event_id: int) -> Lineups:
        """
        Get the match lineups.

        Args:
            event_id (int): The event id.

        Returns:
            dict: The match lineups.
        """
        try:
            url = self.endpoints.match_lineups_endpoint(event_id)
            return parse_lineups(get_json(self.page, url))
        except Exception as exc:
            raise exc

    def get_match_incidents(self, event_id: int) -> list[Incident]:
        """
        Get the match incidents.

        Args:
            event_id (int): The event id.

        Returns:
            list[Incident]: The match incidents.
        """
        try:
            url = self.endpoints.match_events_endpoint(event_id)
            data = get_json(self.page, url)["incidents"]
            return parse_incidents(data)
        except Exception as exc:
            raise exc

    def get_match_top_players(self, event_id: int) -> TopPlayersMatch:
        """
        Get the top players of a match.

        Args:
            event_id (int): The event id.

        Returns:
            TopPlayersMatch: The top players of the match.
        """
        try:
            url = self.endpoints.match_top_players_endpoint(event_id)
            return parse_top_players_match(get_json(self.page, url))
        except Exception as exc:
            raise exc

    def get_match_comments(self, event_id: int) -> list[Comment]:
        """
        Get the match comments.

        Args:
            event_id (int): The event id.

        Returns:
            list[Comment]: The match comments.
        """
        try:
            url = self.endpoints.match_comments_endpoint(event_id)
            data = get_json(self.page, url)["comments"]
            return parse_comments(data)
        except Exception as exc:
            raise exc

    def get_match_stats(self, event_id: int) -> MatchStats:
        """
        Get the match statistics.

        Args:
            event_id (int): The event id.

        Returns:
            MatchStats: The match statistics.
        """
        try:
            url = self.endpoints.match_stats_endpoint(event_id)
            data = get_json(self.page, url).get("statistics", {})
            url = self.endpoints.match_probabilities_endpoint(event_id)
            win_probabilities = get_json(self.page, url).get("winProbability", {})
            return parse_match_stats(data, win_probabilities)
        except Exception as exc:
            raise exc

    def get_match_shots(self, event_id: int) -> dict:
        """
        Get the match shots.

        Args:
            event_id (int): The event id.

        Returns:
            dict: The match shots.
        """
        try:
            url = self.endpoints.match_shots_endpoint(event_id)
            data = get_json(self.page, url)
            if "shotmap" in data:
                return parse_shots(data["shotmap"])
            return Shot()
        except Exception as exc:
            raise exc

    def get_team(self, team_id: int) -> Team:
        """
        Get the team information.

        Args:
            team_id (int): The team id.

        Returns:
            Team: The team information
        """
        try:
            url = self.endpoints.team_endpoint(team_id)
            data = get_json(self.page, url)["team"]
            return parse_team(data)
        except Exception as exc:
            raise exc

    def get_team_players(self, team_id: int) -> list[Player]:
        """
        Get the team players.

        Args:
            team_id (int): The team id.

        Returns:
            list[Player]: The players of the team.
        """
        try:
            url = self.endpoints.team_players_endpoint(team_id)
            return [
                parse_player(player["player"])
                for player in get_json(self.page, url)["players"]
            ]
        except Exception as exc:
            raise exc

    def get_team_events(self, team_id: int, upcoming: bool, page: int) -> list[Event]:
        """
        Get the team events.

        Args:
            team_id (int): The team id.
            upcoming (bool): The upcoming events.
            page (int): The page number.

        Returns:
            list[Event]: The team events.
        """
        try:
            url = self.endpoints.team_events_endpoint(team_id, upcoming, page)
            data = get_json(self.page, url)
            if "events" in data:
                return parse_events(data["events"])
            return []
        except Exception as exc:
            raise exc

    def get_tournaments_by_category(self, category_id: Category) -> list[Tournament]:
        """
        Get the tournaments by category id.

        Args:
            category_id (Category): The category id.

        Returns:
            list[Tournament]: The tournaments.
        """
        if not isinstance(category_id, Category):
            raise ValueError("category_id must be an instance of Category Enum")
        try:
            url = self.endpoints.tournaments_endpoint(category_id.value)
            data = get_json(self.page, url)["groups"][0].get("uniqueTournaments", [])
            return parse_tournaments(data)
        except Exception as exc:
            raise exc

    def get_tournament_seasons(self, tournament_id: int) -> list[Season]:
        """
        Get the seasons of a tournament.

        Args:
            tournament_id (int): The tournament id.

        Returns:
            list[Season]: The seasons of the tournament.
        """
        try:
            url = self.endpoints.tournament_seasons_endpoint(tournament_id)
            data = get_json(self.page, url)["seasons"]
            return parse_seasons(data)
        except Exception as exc:
            raise exc

    def get_tournament_bracket(
        self, tournament_id: int | Tournament, season_id: int | Season
    ) -> list[Bracket]:
        """
        Get the tournament bracket.

        Args:
            tournament_id (int, Tournament): The tournament id.
            season_id (int, Season): The season id.

        Returns:
            dict: The tournament bracket.
        """
        try:
            if isinstance(tournament_id, Tournament):
                tournament_id = tournament_id.id
            if isinstance(season_id, Season):
                season_id = season_id.id
            url = self.endpoints.tournament_bracket_endpoint(tournament_id, season_id)
            data = get_json(self.page, url)["cupTrees"]
            return parse_brackets(data)
        except Exception as exc:
            raise exc

    def get_tournament_standings(
        self, tournament_id: int | Tournament, season_id: int | Season
    ) -> list[Standing]:
        """
        Get the tournament standings.

        Args:
            tournament_id (int, Tournament): The tournament id.
            season_id (int, Season): The season id.

        Returns:
            list[Standing]: The tournament standings.
        """
        try:
            if isinstance(tournament_id, Tournament):
                tournament_id = tournament_id.id
            if isinstance(season_id, Season):
                season_id = season_id.id
            url = self.endpoints.tournament_standings_endpoint(tournament_id, season_id)
            data = get_json(self.page, url)["standings"]
            return parse_standings(data)
        except Exception as exc:
            raise exc

    def get_tournament_top_teams(
        self, tournament_id: int | Tournament, season_id: int | Season
    ) -> TopTournamentTeams:
        """
        Get different top teams of a tournament.

        Args:
            tournament_id (int, Tournament): The tournament id.
            season_id (int, Season): The season id.

        Returns:
            TopTournamentTeams: The top teams of the tournament.
        """
        try:
            if isinstance(tournament_id, Tournament):
                tournament_id = tournament_id.id
            if isinstance(season_id, Season):
                season_id = season_id.id
            url = self.endpoints.tournament_topteams_endpoint(tournament_id, season_id)
            response = get_json(self.page, url)
            if "topTeams" in response:
                return parse_top_tournament_teams(response["topTeams"])
            return TopTournamentTeams()
        except Exception as exc:
            raise exc

    def get_tournament_top_players(
        self, tournament_id: int | Tournament, season_id: int | Season
    ) -> TopTournamentPlayers:
        """
        Get the top players of the tournament.

        Args:
            tournament_id (int, Tournament): The tournament id.
            season_id (int, Season): The season id.

        Returns:
            TopTournamentPlayers: The top players of the tournament.
        """
        try:
            if isinstance(tournament_id, Tournament):
                tournament_id = tournament_id.id
            if isinstance(season_id, Season):
                season_id = season_id.id
            url = self.endpoints.tournament_topplayers_endpoint(
                tournament_id, season_id
            )
            data = get_json(self.page, url)
            if "topPlayers" in data:
                return parse_top_tournament_players(data["topPlayers"])
            return TopTournamentPlayers()
        except Exception as exc:
            raise exc

    def get_tournament_events(
        self, tournament_id: int, season_id: int, upcoming: bool, page: int
    ) -> list[Event]:
        """
        Get the events of a tournament.

        Args:
            tournament_id (int): The tournament id.
            season_id (int): The season id.
            upcoming (bool): The upcoming events.
            page (int): The page number.

        Returns:
            list[Event]: The events of the tournament.
        """
        try:
            url = self.endpoints.tournament_events_endpoint(
                tournament_id, season_id, upcoming, page
            )
            if "events" in get_json(self.page, url):
                return parse_events(get_json(self.page, url)["events"])
            return []
        except Exception as exc:
            raise exc

    def search(
        self, query: str, entity: EntityType = EntityType.ALL
    ) -> list[Event | Team | Player | Tournament]:
        """
        Search query for matches, teams, players, and tournaments.

        Args:
            query (str): The search query.
            entity (EntityType): The entity type to search for.

        Returns:
            list[Event | Team | Player | Tournament]: The search results.
        """
        try:
            entity_type = entity.value
            url = self.endpoints.search_endpoint(query=query, entity_type=entity_type)
            results = get_json(self.page, url)["results"]

            specific_parsers = {
                EntityType.TEAM: parse_team,
                EntityType.PLAYER: parse_player,
                EntityType.EVENT: parse_event,
                EntityType.TOURNAMENT: parse_tournament,
            }

            if entity == EntityType.ALL:
                type_parsers = {
                    "team": parse_team,
                    "player": parse_player,
                    "event": parse_events,
                    "uniqueTournament": parse_tournament,
                }
                entities = []
                for result in results:
                    result_type = result.get("type")
                    entity_data = result.get("entity")
                    parser = type_parsers.get(result_type, lambda x: x)
                    entities.append(parser(entity_data))
                return entities
            parser = specific_parsers.get(entity, lambda x: x)
            return [parser(result.get("entity")) for result in results]
        except Exception as exc:
            raise exc
