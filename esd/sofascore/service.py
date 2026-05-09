"""
Sofascore service module
"""

from __future__ import annotations

from ..utils import get_api_json, get_today
from .endpoints import SofascoreEndpoints
from .types import (
    Bracket,
    Category,
    Comment,
    EntityType,
    Event,
    Incident,
    Lineups,
    MatchStats,
    Player,
    PlayerAttributes,
    Season,
    Shot,
    Standing,
    Team,
    TopPlayersMatch,
    TopTournamentPlayers,
    TopTournamentTeams,
    Tournament,
    TransferHistory,
    parse_brackets,
    parse_comments,
    parse_event,
    parse_events,
    parse_incidents,
    parse_lineups,
    parse_match_stats,
    parse_player,
    parse_player_attributes,
    parse_seasons,
    parse_shots,
    parse_standings,
    parse_team,
    parse_top_players_match,
    parse_top_tournament_players,
    parse_top_tournament_teams,
    parse_tournament,
    parse_tournaments,
    parse_transfer_history,
)


class SofascoreService:
    """
    A class to represent the SofaScore service.
    """

    def __init__(self) -> None:
        self.endpoints = SofascoreEndpoints()

    def get_event(self, event_id: int) -> Event:
        try:
            url = self.endpoints.event_endpoint(event_id)
            data = get_api_json(url)["event"]
            return parse_event(data)
        except Exception as exc:
            raise exc

    def get_events(self, date: str = "today") -> list[Event]:
        if date == "today":
            date = get_today()
        try:
            url = self.endpoints.events_endpoint.format(date=date)
            return parse_events(get_api_json(url)["events"])
        except Exception as exc:
            raise exc

    def get_live_events(self) -> list[Event]:
        try:
            url = self.endpoints.live_events_endpoint
            return parse_events(get_api_json(url)["events"])
        except Exception as exc:
            raise exc

    def get_player(self, player_id: int) -> Player:
        try:
            url = self.endpoints.player_endpoint(player_id)
            data = get_api_json(url)
            if "player" in data:
                player = parse_player(data["player"])
                player.attributes = self.get_player_attributes(player_id)
                player.transfer_history = self.get_player_transfer_history(player_id)
                return player
            return Player()
        except Exception as exc:
            raise exc

    def get_player_attributes(self, player_id: int) -> PlayerAttributes:
        try:
            url = self.endpoints.player_attributes_endpoint(player_id)
            data = get_api_json(url)
            if "playerAttributes" in data:
                return parse_player_attributes(data["playerAttributes"])
            return PlayerAttributes()
        except Exception as exc:
            raise exc

    def get_player_transfer_history(self, player_id: int) -> TransferHistory:
        try:
            url = self.endpoints.player_transfer_history_endpoint(player_id)
            data = get_api_json(url)
            if data is not None:
                return parse_transfer_history(data)
            return TransferHistory()
        except Exception as exc:
            raise exc

    def get_player_stats(self, player_id: int) -> dict:
        try:
            url = self.endpoints.player_stats_endpoint(player_id)
            return get_api_json(url)
        except Exception as exc:
            raise exc

    def get_match_lineups(self, event_id: int) -> Lineups:
        try:
            url = self.endpoints.match_lineups_endpoint(event_id)
            return parse_lineups(get_api_json(url))
        except Exception as exc:
            raise exc

    def get_match_incidents(self, event_id: int) -> list[Incident]:
        try:
            url = self.endpoints.match_events_endpoint(event_id)
            data = get_api_json(url)["incidents"]
            return parse_incidents(data)
        except Exception as exc:
            raise exc

    def get_match_top_players(self, event_id: int) -> TopPlayersMatch:
        try:
            url = self.endpoints.match_top_players_endpoint(event_id)
            return parse_top_players_match(get_api_json(url))
        except Exception as exc:
            raise exc

    def get_match_comments(self, event_id: int) -> list[Comment]:
        try:
            url = self.endpoints.match_comments_endpoint(event_id)
            data = get_api_json(url)["comments"]
            return parse_comments(data)
        except Exception as exc:
            raise exc

    def get_match_stats(self, event_id: int) -> MatchStats:
        try:
            url = self.endpoints.match_stats_endpoint(event_id)
            data = get_api_json(url).get("statistics", {})
            url = self.endpoints.match_probabilities_endpoint(event_id)
            win_probabilities = get_api_json(url).get("winProbability", {})
            return parse_match_stats(data, win_probabilities)
        except Exception as exc:
            raise exc

    def get_match_shots(self, event_id: int) -> dict:
        try:
            url = self.endpoints.match_shots_endpoint(event_id)
            data = get_api_json(url)
            if "shotmap" in data:
                return parse_shots(data["shotmap"])
            return Shot()
        except Exception as exc:
            raise exc

    def get_team(self, team_id: int) -> Team:
        try:
            url = self.endpoints.team_endpoint(team_id)
            data = get_api_json(url)["team"]
            return parse_team(data)
        except Exception as exc:
            raise exc

    def get_team_players(self, team_id: int) -> list[Player]:
        try:
            url = self.endpoints.team_players_endpoint(team_id)
            return [
                parse_player(player["player"])
                for player in get_api_json(url)["players"]
            ]
        except Exception as exc:
            raise exc

    def get_team_events(self, team_id: int, upcoming: bool, page: int) -> list[Event]:
        try:
            url = self.endpoints.team_events_endpoint(team_id, upcoming, page)
            data = get_api_json(url)
            if "events" in data:
                return parse_events(data["events"])
            return []
        except Exception as exc:
            raise exc

    def get_tournaments_by_category(self, category_id: Category) -> list[Tournament]:
        if not isinstance(category_id, Category):
            raise ValueError("category_id must be an instance of Category Enum")
        try:
            url = self.endpoints.tournaments_endpoint(category_id.value)
            data = get_api_json(url)["groups"][0].get("uniqueTournaments", [])
            return parse_tournaments(data)
        except Exception as exc:
            raise exc

    def get_tournament_seasons(self, tournament_id: int) -> list[Season]:
        try:
            url = self.endpoints.tournament_seasons_endpoint(tournament_id)
            data = get_api_json(url)["seasons"]
            return parse_seasons(data)
        except Exception as exc:
            raise exc

    def get_tournament_bracket(
        self, tournament_id: int | Tournament, season_id: int | Season
    ) -> list[Bracket]:
        try:
            if isinstance(tournament_id, Tournament):
                tournament_id = tournament_id.id
            if isinstance(season_id, Season):
                season_id = season_id.id
            url = self.endpoints.tournament_bracket_endpoint(tournament_id, season_id)
            data = get_api_json(url)["cupTrees"]
            return parse_brackets(data)
        except Exception as exc:
            raise exc

    def get_tournament_standings(
        self, tournament_id: int | Tournament, season_id: int | Season
    ) -> list[Standing]:
        try:
            if isinstance(tournament_id, Tournament):
                tournament_id = tournament_id.id
            if isinstance(season_id, Season):
                season_id = season_id.id
            url = self.endpoints.tournament_standings_endpoint(tournament_id, season_id)
            data = get_api_json(url)["standings"]
            return parse_standings(data)
        except Exception as exc:
            raise exc

    def get_tournament_top_teams(
        self, tournament_id: int | Tournament, season_id: int | Season
    ) -> TopTournamentTeams:
        try:
            if isinstance(tournament_id, Tournament):
                tournament_id = tournament_id.id
            if isinstance(season_id, Season):
                season_id = season_id.id
            url = self.endpoints.tournament_topteams_endpoint(tournament_id, season_id)
            response = get_api_json(url)
            if "topTeams" in response:
                return parse_top_tournament_teams(response["topTeams"])
            return TopTournamentTeams()
        except Exception as exc:
            raise exc

    def get_tournament_top_players(
        self, tournament_id: int | Tournament, season_id: int | Season
    ) -> TopTournamentPlayers:
        try:
            if isinstance(tournament_id, Tournament):
                tournament_id = tournament_id.id
            if isinstance(season_id, Season):
                season_id = season_id.id
            url = self.endpoints.tournament_topplayers_endpoint(
                tournament_id, season_id
            )
            data = get_api_json(url)
            if "topPlayers" in data:
                return parse_top_tournament_players(data["topPlayers"])
            return TopTournamentPlayers()
        except Exception as exc:
            raise exc

    def get_tournament_events(
        self, tournament_id: int, season_id: int, upcoming: bool, page: int
    ) -> list[Event]:
        try:
            url = self.endpoints.tournament_events_endpoint(
                tournament_id, season_id, upcoming, page
            )
            data = get_api_json(url)
            if "events" in data:
                return parse_events(data["events"])
            return []
        except Exception as exc:
            raise exc

    def search(
        self, query: str, entity: EntityType = EntityType.ALL
    ) -> list[Event | Team | Player | Tournament]:
        try:
            entity_type = entity.value
            url = self.endpoints.search_endpoint(query=query, entity_type=entity_type)
            results = get_api_json(url)["results"]

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
