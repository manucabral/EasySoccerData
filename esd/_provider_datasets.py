"""Provider-specific dataset plans sharing validated caching and task coverage."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ._response_reader import ResponseReader
from .cache import CachePolicy, ResponseCache
from .datasets import (
    DatasetIssue,
    DatasetLoadError,
    DatasetMetadata,
    DatasetProgress,
    SoccerDataset,
)
from .exceptions import SourceError
from .normalized import (
    NormalizedTeam,
    normalize_match,
    normalize_match_stats,
    normalize_player_stats,
    normalize_shot,
    normalize_standings,
)
from .normalized.schema import TABLE_MODELS
from .scores365.endpoints import Scores365Endpoints
from .scores365.types import parse_games
from .scores365.types import parse_standings as parse_scores_standings
from .sofascore.endpoints import SofascoreEndpoints
from .sofascore.types import parse_events
from .sofascore.types import parse_standings as parse_sofa_standings
from .understat.endpoints import UnderstatEndpoints
from .understat.service import extract_embedded_json
from .understat.types import parse_league_matches, parse_match_shots, parse_players
from .utils import get_api_json, get_text


class _Download:
    def __init__(self, options):
        self.options = options
        self.policy = options["cache_policy"] or CachePolicy()
        self.started = datetime.now(timezone.utc)
        self.expected = []
        self.successful = []
        self.errors = []
        self.response_times = {}
        self.cached_tasks = []
        self.rows = {name: {} for name in TABLE_MODELS}
        self.observed = {}
        self.completed = 0
        cache = ResponseCache(options["cache_dir"]) if options["cache_dir"] is not None else None
        fetch = self._understat_fetch if options["source"] == "understat" else self._fetch
        self.reader = ResponseReader(fetch, cache=cache, refresh=options["refresh"],
                                     request_delay=options["request_delay"])
        self.requested_ids = ()

    def _fetch(self, url):
        return get_api_json(url, proxies=self.options["proxies"])

    def _understat_fetch(self, url):
        try:
            data = get_api_json(url, proxies=self.options["proxies"],
                                headers={"X-Requested-With": "XMLHttpRequest", "Referer": "https://understat.com/"})
            if not isinstance(data, dict) or not data:
                raise SourceError("Understat API returned no data")
        except SourceError:
            page = url.replace("/getLeagueData/", "/league/").replace("/getMatchData/", "/match/")
            data = extract_embedded_json(get_text(page, proxies=self.options["proxies"]))
            if not data:
                raise SourceError("Understat returned maintenance or no embedded data") from None
        data = dict(data)
        for alias, canonical in (("datesData", "dates"), ("playersData", "players"),
                                 ("teamsData", "teams"), ("shotsData", "shots")):
            if alias in data and canonical not in data:
                data[canonical] = data[alias]
        return data

    def expect(self, step, target):
        key = f"{step}:{target}"
        if key not in self.expected:
            self.expected.append(key)

    def snapshot(self):
        opt = self.options
        return SoccerDataset(
            metadata=DatasetMetadata(
                source=opt["source"], league=opt["league"], season=opt["season"], tables=opt["tables"],
                started_at=self.started, finished_at=datetime.now(timezone.utc),
                expected_tasks=tuple(self.expected), successful_tasks=tuple(self.successful),
                response_fetched_at=tuple(self.response_times.items()), cached_tasks=tuple(self.cached_tasks),
                coverage_scope=("entities" if opt["source"] == "transfermarkt" else "date_range"
                                if opt["source"] in ("scores365", "fbref", "promiedos", "besoccer") and any(table in opt["tables"] for table in ("matches", "match_stats")) else "season"),
                source_season_id=str(opt["season_id"]) if opt["season_id"] is not None else None,
                start_date=opt["start_date"], end_date=opt["end_date"],
                source_timezone=opt["source_timezone"], requested_match_ids=self.requested_ids,
                source_season=opt["source_season"],
                requested_club_ids=tuple(str(item) for item in opt["club_ids"] or ()),
                requested_player_ids=tuple(str(item) for item in opt["player_ids"] or ()),
                standings_loaded=any(key.startswith("standings:") for key in self.successful),
            ),
            match_records=tuple(self.rows["matches"].values()), team_records=tuple(self.rows["teams"].values()),
            standing_records=tuple(self.rows["standings"].values()), errors=tuple(self.errors),
            match_stat_records=tuple(self.rows["match_stats"].values()),
            player_stat_records=tuple(self.rows["player_stats"].values()), shot_records=tuple(self.rows["shots"].values()),
            player_records=tuple(self.rows["players"].values()),
            market_value_records=tuple(self.rows["market_values"].values()),
            transfer_records=tuple(self.rows["transfers"].values()),
        )

    def report(self, step, target, error=None):
        key = f"{step}:{target}"
        self.completed += 1
        if error is not None:
            self.errors.append(DatasetIssue(step, target, type(error).__name__, str(error)))
        else:
            self.successful.append(key)
        info = self.reader.last_response if error is None else None
        if info is not None:
            self.response_times[key] = datetime.fromtimestamp(info.fetched_at, timezone.utc).isoformat()
            if info.cached:
                self.cached_tasks.append(key)
        callback = self.options["progress"]
        if callback is not None:
            callback(DatasetProgress(self.completed, len(self.expected), step, target, error is None,
                                     len(self.rows["matches"]), bool(info and info.cached)))
        if error is not None and self.options["on_error"] == "raise":
            raise DatasetLoadError(self.snapshot()) from error

    def run(self, step, target, url, parse, commit=None, ttl=None):
        self.expect(step, target)
        error = result = None
        try:
            data = self.reader.read(url, ttl=self.policy.calendar_ttl if ttl is None else ttl, validate=parse)
            result = parse(data)
            if commit is not None:
                commit(result)
        except Exception as exc:
            error = exc
        self.report(step, target, error)
        return result if error is None else None

    def add(self, table, rows, field):
        timestamp = self.reader.last_response.fetched_at
        for row in rows:
            key = field(row) if callable(field) else getattr(row, field)
            if table == "standings":
                key = (row.table_id, row.table_name, row.stage_id, row.group_id, row.team_id)
            if timestamp >= self.observed.get((table, key), float("-inf")):
                self.rows[table][key] = row
                self.observed[table, key] = timestamp
        if table == "matches" and "teams" in self.options["tables"]:
            teams = [NormalizedTeam(row.source, team_id, name) for row in rows
                     for team_id, name in ((row.home_team_id, row.home_team_name), (row.away_team_id, row.away_team_name))
                     if team_id is not None]
            self.add("teams", teams, "team_id")


def _require_ids(rows, field):
    if any(not getattr(row, field) for row in rows):
        raise SourceError(f"Source record is missing {field}")
    return rows


def _options(options):
    source = options["source"]
    if source in ("fbref", "goaloo", "promiedos", "besoccer", "transfermarkt"):
        from ._remaining_datasets import validate_options

        validate_options(options)
        return
    if any(options[key] is not None for key in ("source_season", "club_ids", "player_ids")):
        raise ValueError("source_season and entity selections are not supported by this source")
    if options["anchor_date"] is not None:
        raise ValueError("anchor_date is supported only for ESPN")
    if type(options["max_pages"]) is not int or options["max_pages"] < 1:
        raise ValueError("max_pages must be a positive integer")
    native = options["season_id"]
    if native is not None and (isinstance(native, bool) or not str(native).isdigit() or int(native) < 1):
        raise ValueError("season_id must be a positive native ID")
    if source in ("scores365", "sofascore") and (not options["league"].isdigit() or int(options["league"]) < 1):
        raise ValueError("This source requires a positive numeric league ID")
    if source == "sofascore" and native is None:
        raise ValueError("Sofascore requires its native season_id, separate from the season year label")
    if source == "scores365":
        if "matches" in options["tables"]:
            if not options["start_date"] or not options["end_date"]:
                raise ValueError("365Scores matches require explicit start_date and end_date")
            start = datetime.strptime(options["start_date"], "%Y-%m-%d").date()
            end = datetime.strptime(options["end_date"], "%Y-%m-%d").date()
            if not 0 <= (end - start).days <= 730:
                raise ValueError("Date range must be ordered and at most 731 days")
        if "standings" in options["tables"] and native is None:
            raise ValueError("365Scores standings require a native season_id to validate the source snapshot")
    elif options["start_date"] is not None or options["end_date"] is not None:
        raise ValueError("Explicit date ranges are supported only for 365Scores")
    if source != "understat" and (options["source_timezone"] is not None or options["match_ids"] is not None):
        raise ValueError("source_timezone and match_ids are supported only for Understat")
    if source == "understat":
        if native is not None:
            raise ValueError("Understat uses the season year, not a separate season_id")
        if options["source_timezone"] not in (None, "UTC"):
            ZoneInfo(options["source_timezone"])
        if options["match_ids"] is not None:
            if "shots" not in options["tables"] or not options["match_ids"] or isinstance(options["match_ids"], str):
                raise ValueError("match_ids requires a nonempty shot selection")
            if any(isinstance(item, bool) or not str(item).isdigit() or int(item) < 1 for item in options["match_ids"]):
                raise ValueError("match_ids must be positive native IDs")


def _scores(download):
    opt = download.options
    endpoints = Scores365Endpoints(timezone_name="UTC")
    league = int(opt["league"])
    dates = []
    if "matches" in opt["tables"]:
        start = datetime.strptime(opt["start_date"], "%Y-%m-%d").date()
        end = datetime.strptime(opt["end_date"], "%Y-%m-%d").date()
        dates = [(start + timedelta(days=offset)).isoformat() for offset in range((end - start).days + 1)]
        for day in dates:
            download.expect("matches", day)
    if "standings" in opt["tables"]:
        download.expect("standings", str(opt["season_id"]))
    for day in dates:
        formatted = datetime.strptime(day, "%Y-%m-%d").strftime("%d/%m/%Y")
        url = endpoints.games_allscores(formatted, formatted, league)

        def parse(data, day=day):
            if not isinstance(data, dict) or not isinstance(data.get("games"), list):
                raise SourceError("365Scores did not return an explicit games list for this date")
            games = [game for game in parse_games(data) if game.competition_id == league]
            if opt["season_id"] is not None and any(str(game.season_num) != str(opt["season_id"]) for game in games):
                raise SourceError("365Scores returned another native season")
            rows = _require_ids([normalize_match(game, season=opt["season"]) for game in games], "match_id")
            if any(row.kickoff is None or row.kickoff.date().isoformat() != day for row in rows):
                raise SourceError("365Scores returned games outside the requested UTC date")
            return rows

        def ttl(data, day=day):
            events = [{"status": {"type": {"completed": game.get("statusGroup") == 4}}}
                      for game in data.get("games", []) if game.get("competitionId") == league]
            return download.policy.scoreboard_ttl(day, {"events": events})

        download.run("matches", day, url, parse, lambda rows: download.add("matches", rows, "match_id"), ttl)
    if "standings" in opt["tables"]:
        def parse(data):
            if not isinstance(data, dict) or not isinstance(data.get("standings"), list):
                raise SourceError("365Scores did not return standings")
            tables = [table for table in parse_scores_standings(data) if table.competition_id == league]
            if not tables or any(str(table.season_num) != str(opt["season_id"]) for table in tables):
                raise SourceError("365Scores standings do not match the requested native season")
            return _require_ids([row for table in tables for row in normalize_standings(table, season=opt["season"])], "team_id")

        download.run("standings", str(opt["season_id"]), endpoints.standings(league), parse,
                     lambda rows: download.add("standings", rows, "team_id"), download.policy.standings_ttl)


def _sofa(download):
    opt = download.options
    league, native = int(opt["league"]), int(opt["season_id"])
    endpoints = SofascoreEndpoints()
    if "matches" in opt["tables"]:
        for direction in ("last", "next"):
            download.expect("matches", f"{direction}/0")
    if "standings" in opt["tables"]:
        download.expect("standings", str(native))
    if "matches" in opt["tables"]:
        for direction in ("last", "next"):
            seen_pages = set()
            for page in range(opt["max_pages"]):
                def parse(data, seen_pages=seen_pages):
                    if not isinstance(data, dict) or not isinstance(data.get("events"), list) or type(data.get("hasNextPage")) is not bool:
                        raise SourceError("Sofascore page is missing events or explicit pagination metadata")
                    for event in data["events"]:
                        if (event.get("season") or {}).get("id") != native:
                            raise SourceError("Sofascore returned another native season")
                        tournament = ((event.get("tournament") or {}).get("uniqueTournament") or {}).get("id")
                        if tournament != league:
                            raise SourceError("Sofascore returned another unique tournament")
                    rows = _require_ids([normalize_match(event, competition_id=league, season=opt["season"])
                                         for event in parse_events(data["events"])], "match_id")
                    ids = tuple(sorted(row.match_id for row in rows))
                    if data["hasNextPage"] and (not rows or ids in seen_pages):
                        raise SourceError("Sofascore pagination did not advance")
                    return rows, data["hasNextPage"]

                def commit(value, seen_pages=seen_pages, direction=direction, page=page):
                    rows, more = value
                    ids = tuple(sorted(row.match_id for row in rows))
                    seen_pages.add(ids)
                    download.add("matches", rows, "match_id")
                    if more:
                        download.expect("matches", f"{direction}/{page + 1}")

                result = download.run("matches", f"{direction}/{page}",
                                      endpoints.tournament_events_endpoint(league, native, direction == "next", page),
                                      parse, commit, download.policy.calendar_ttl)
                if result is None or not result[1]:
                    break
            else:
                target = f"{direction}/{opt['max_pages']}"
                download.expect("matches", target)
                download.report("matches", target, SourceError("Sofascore pagination reached max_pages before its end"))
    if "standings" in opt["tables"]:
        def parse(data):
            if not isinstance(data, dict) or not isinstance(data.get("standings"), list):
                raise SourceError("Sofascore did not return standings")
            return _require_ids([replace(row, source_season_id=str(native)) for table in parse_sofa_standings(data["standings"])
                                 for row in normalize_standings(table, competition_id=league, season=opt["season"])], "team_id")

        download.run("standings", str(native), endpoints.tournament_standings_endpoint(league, native), parse,
                     lambda rows: download.add("standings", rows, "team_id"), download.policy.standings_ttl)


def _understat(download):
    opt = download.options
    endpoints = UnderstatEndpoints()
    league_url = endpoints.league_data(opt["league"], opt["season"])
    discovery = any(table in opt["tables"] for table in ("matches", "teams", "match_stats", "shots"))
    if discovery:
        download.expect("season", str(opt["season"]))
    if "player_stats" in opt["tables"]:
        download.expect("player_stats", str(opt["season"]))
    if discovery:
        def parse(data):
            if not isinstance(data, dict) or not isinstance(data.get("dates"), list):
                raise SourceError("Understat season response is missing its match list")
            matches = parse_league_matches(data)
            _require_ids(matches, "id")
            rows = [normalize_match(match, competition_id=opt["league"], season=opt["season"],
                                     source_timezone=opt["source_timezone"]) for match in matches] if "matches" in opt["tables"] else []
            if opt["match_ids"] is not None:
                available = {str(match.id) for match in matches if match.is_result}
                if not {str(item) for item in opt["match_ids"]} <= available:
                    raise SourceError("Requested shot match IDs are not completed matches in this league season")
            return matches, rows

        def commit(value):
            matches, rows = value
            if "matches" in opt["tables"]:
                download.add("matches", rows, "match_id")
            if "match_stats" in opt["tables"]:
                download.add("match_stats", [normalize_match_stats(match) for match in matches], "match_id")
            if "shots" in opt["tables"]:
                requested = {str(item) for item in opt["match_ids"]} if opt["match_ids"] is not None else None
                download.requested_ids = tuple(str(match.id) for match in matches if match.is_result
                                               and (requested is None or str(match.id) in requested))
                for match_id in download.requested_ids:
                    download.expect("shots", match_id)

        result = download.run("season", str(opt["season"]), league_url, parse, commit, download.policy.calendar_ttl)
        if result is not None and "shots" in opt["tables"]:
            for match_id in download.requested_ids:
                def parse(data, match_id=match_id):
                    if not isinstance(data, dict) or not isinstance(data.get("shots"), (dict, list)):
                        raise SourceError("Understat match response is missing shots")
                    if isinstance(data["shots"], dict) and any(
                        not isinstance(data["shots"].get(side), list) for side in ("h", "a")
                    ):
                        raise SourceError("Understat shots are missing home/away lists")
                    shots = _require_ids([normalize_shot(shot) for shot in parse_match_shots(data)], "shot_id")
                    if any(shot.match_id != match_id for shot in shots):
                        raise SourceError("Understat returned shots for another match")
                    return shots

                download.run("shots", match_id, endpoints.match_data(match_id), parse,
                             lambda rows: download.add("shots", rows, "shot_id"), download.policy.historical_ttl)
    if "player_stats" in opt["tables"]:
        def parse(data):
            if not isinstance(data, dict) or not isinstance(data.get("players"), list):
                raise SourceError("Understat season response is missing players")
            return _require_ids([normalize_player_stats(player, competition_id=opt["league"], season=opt["season"])
                                 for player in parse_players(data["players"])], "player_id")

        download.run("player_stats", str(opt["season"]), league_url, parse,
                     lambda rows: download.add("player_stats", rows, "player_id"), download.policy.calendar_ttl)


def load_provider_dataset(**options):
    _options(options)
    download = _Download(options)
    if options["source"] in ("scores365", "sofascore", "understat"):
        {"scores365": _scores, "sofascore": _sofa, "understat": _understat}[options["source"]](download)
    else:
        from ._remaining_datasets import load_remaining

        load_remaining(download)
    return download.snapshot()
