"""Bounded match-detail datasets and source-specific statistic mappings."""

from __future__ import annotations

import math
from collections.abc import Sequence

from .espn.endpoints import ESPNEndpoints
from .espn.types import parse_scoreboard
from .exceptions import SourceError
from .normalized import NormalizedMatchStats, normalize_match
from .scores365.endpoints import Scores365Endpoints
from .scores365.types import parse_games
from .sofascore.endpoints import SofascoreEndpoints
from .sofascore.types import parse_events

ESPN_METRICS = {
    "possessionPct": "possession_pct", "totalShots": "shots", "shotsOnTarget": "shots_on_target",
    "wonCorners": "corners", "foulsCommitted": "fouls", "offsides": "offsides",
    "yellowCards": "yellow_cards", "redCards": "red_cards", "saves": "saves",
    "totalPasses": "passes", "accuratePasses": "accurate_passes",
}
SCORES_METRICS = {
    10: "possession_pct", 76: "xg", 3: "shots", 4: "shots_on_target", 8: "corners",
    12: "fouls", 9: "offsides", 1: "yellow_cards", 2: "red_cards", 23: "saves",
    21: "passes", 19: "accurate_passes",
}
SOFA_METRICS = {
    "ballPossession": "possession_pct", "expectedGoals": "xg", "totalShotsOnGoal": "shots",
    "shotsOnGoal": "shots_on_target", "cornerKicks": "corners", "fouls": "fouls",
    "offsides": "offsides", "yellowCards": "yellow_cards", "redCards": "red_cards",
    "goalkeeperSaves": "saves", "passes": "passes", "accuratePasses": "accurate_passes",
}


def _object(value, name):
    if not isinstance(value, dict):
        raise SourceError(f"Match statistics response is missing {name}")
    return value


def _list(value, name):
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise SourceError(f"Match statistics response is missing its {name} list")
    return value


def _checked(parse):
    def validate(data):
        try:
            return parse(_object(data, "response"))
        except (TypeError, ValueError, KeyError, AttributeError, IndexError, OverflowError) as exc:
            raise SourceError(f"Invalid match statistics response: {exc}") from exc
    return validate


def _number(value, metric):
    if value is None or isinstance(value, str) and value.strip() in ("", "-", "--", "N/A", "n/a"):
        return None
    if type(value) not in (str, int, float):
        raise SourceError(f"Invalid value for {metric}")
    text = str(value).strip()
    if metric == "possession_pct":
        text = text.removesuffix("%")
    try:
        number = float(text)
    except ValueError as exc:
        raise SourceError(f"Invalid numeric value for {metric}") from exc
    if not math.isfinite(number) or number < 0:
        raise SourceError(f"Invalid numeric value for {metric}")
    if metric == "possession_pct" and number > 100:
        raise SourceError("Possession must use percentage points from 0 to 100")
    if metric in ("xg", "possession_pct"):
        return number
    if not number.is_integer() or number > 2**63 - 1:
        raise SourceError(f"Invalid count for {metric}")
    return int(number)


def _put(values, side, metric, raw):
    key = f"{side}_{metric}"
    number = _number(raw, metric)
    if key in values and values[key] != number:
        raise SourceError(f"Conflicting source statistics for {key}")
    values[key] = number


def _match_identity(match, options, identifier):
    if (match.match_id != identifier or match.competition_id != options["league"]
            or not match.home_team_id or not match.away_team_id or match.home_team_id == match.away_team_id
            or match.kickoff is None):
        raise SourceError("Match statistics do not identify the selected match and its two teams")
    return match


def _espn(data, options, identifier):
    header = _object(data.get("header"), "ESPN header")
    if (str(header.get("id")) != identifier or _object(header.get("league"), "league").get("slug") != options["league"]
            or _object(header.get("season"), "season").get("year") != options["season"]):
        raise SourceError("ESPN summary does not match the requested event, league and season")
    competitions = _list(header.get("competitions"), "competitions")
    if len(competitions) != 1 or str(competitions[0].get("id")) != identifier:
        raise SourceError("ESPN summary does not identify one selected competition event")
    competitors = _list(competitions[0].get("competitors"), "competitors")
    if len(competitors) != 2 or {row.get("homeAway") for row in competitors} != {"home", "away"}:
        raise SourceError("ESPN summary must identify home and away teams")
    event = dict(header, date=competitions[0].get("date"))
    match = _match_identity(normalize_match(parse_scoreboard({"events": [event]})[0],
                                          competition_id=options["league"], season=options["season"]), options, identifier)
    teams = _list(_object(data.get("boxscore"), "boxscore").get("teams"), "boxscore teams")
    sides = {match.home_team_id: "home", match.away_team_id: "away"}
    seen, values = set(), {}
    for group in teams:
        team_id = str(_object(group.get("team"), "boxscore team").get("id"))
        if team_id not in sides or team_id in seen or group.get("homeAway", sides.get(team_id)) != sides.get(team_id):
            raise SourceError("ESPN boxscore has an unknown, repeated or conflicting team")
        seen.add(team_id)
        for item in _list(group.get("statistics"), "team statistics"):
            if not isinstance(item.get("name"), str) or not item["name"]:
                raise SourceError("ESPN statistic is missing its native name")
            metric = ESPN_METRICS.get(item.get("name"))
            if metric:
                _put(values, sides[team_id], metric, item.get("displayValue"))
    return match, NormalizedMatchStats("espn", identifier, source_period="boxscore", **values)


def _scores(data, options, identifier):
    games = _list(data.get("games"), "games")
    if len(games) != 1:
        raise SourceError("365Scores statistics must identify exactly one match")
    game = games[0]
    if (str(game.get("id")) != identifier or str(game.get("competitionId")) != options["league"]
            or str(game.get("seasonNum")) != str(options["season_id"])
            or type(game.get("sportId")) is not int or game["sportId"] != 1):
        raise SourceError("365Scores statistics do not match the requested football competition and native season")
    match = _match_identity(normalize_match(parse_games({"games": games})[0], season=options["season"]), options, identifier)
    actual = data.get("actualGameStatistics")
    if actual is not None and _object(actual, "actualGameStatistics").get("filterId") != -1:
        raise SourceError("365Scores statistics do not describe the whole match")
    sides = {match.home_team_id: "home", match.away_team_id: "away"}
    values = {}
    for item in _list(data.get("statistics"), "statistics"):
        if type(item.get("id")) is not int:
            raise SourceError("365Scores statistic is missing its numeric native ID")
        metric = SCORES_METRICS.get(item.get("id"))
        if metric is not None:
            team_id = str(item.get("competitorId"))
            if team_id not in sides:
                raise SourceError("365Scores statistic belongs to an unknown team")
            _put(values, sides[team_id], metric, item.get("value"))
    return match, NormalizedMatchStats("scores365", identifier, source_period="-1" if actual is not None else None, **values)


def _sofa_event(data, options, identifier):
    event = _object(data.get("event"), "event")
    if (_object(event.get("season"), "season").get("id") != int(options["season_id"])
            or _object(_object(event.get("tournament"), "tournament").get("uniqueTournament"), "uniqueTournament").get("id") != int(options["league"])):
        raise SourceError("Sofascore event does not match the selected tournament and native season")
    return _match_identity(normalize_match(parse_events([event])[0], competition_id=options["league"],
                                          season=options["season"]), options, identifier)


def _sofa_stats(data, identifier):
    periods = _list(data.get("statistics"), "statistics")
    totals = [period for period in periods if period.get("period") == "ALL"]
    if periods and len(totals) != 1:
        raise SourceError("Sofascore statistics must contain exactly one ALL period")
    values = {}
    for period in totals:
        for group in _list(period.get("groups"), "groups"):
            for item in _list(group.get("statisticsItems"), "statisticsItems"):
                if not isinstance(item.get("key"), str) or not item["key"]:
                    raise SourceError("Sofascore statistic is missing its native key")
                metric = SOFA_METRICS.get(item.get("key"))
                if metric:
                    for side in ("home", "away"):
                        _put(values, side, metric, item.get(f"{side}Value"))
    return NormalizedMatchStats("sofascore", identifier, source_period="ALL", **values)


def load_match_statistics(**options):
    """Fetch only explicit IDs; budget endpoint reads before normal transport retries."""
    from ._provider_datasets import _Download

    source = options["source"]
    identifiers = options["match_ids"]
    if (not isinstance(identifiers, Sequence) or isinstance(identifiers, (str, bytes)) or not identifiers
            or any(type(value) not in (str, int) or not str(value).isascii()
                   or not str(value).isdigit() or int(value) < 1 for value in identifiers)):
        raise ValueError("match_stats requires a nonempty sequence of positive native match_ids")
    identifiers = tuple(dict.fromkeys(str(int(value)) for value in identifiers))
    budget = options["max_match_requests"]
    cost = len(identifiers) * (2 if source == "sofascore" else 1)
    if type(budget) is not int or budget < 1 or cost > budget:
        raise ValueError(f"Selected match details require {cost} endpoint reads, exceeding max_match_requests={budget}")
    if any(options[key] is not None for key in ("start_date", "end_date", "anchor_date", "source_timezone", "source_season", "club_ids", "player_ids")) or options["max_pages"] != 100:
        raise ValueError("Explicit match statistics do not accept calendar, date-range or entity filters")
    if any(table not in ("matches", "teams", "match_stats") for table in options["tables"]):
        raise ValueError("Load standings and other tables separately from explicit match statistics")
    if source == "espn":
        if options["season_id"] is not None:
            raise ValueError("ESPN uses its season year instead of season_id")
    else:
        for key in ("season_id", "league"):
            value = options[key]
            if type(value) not in (str, int) or not str(value).isascii() or not str(value).isdigit() or int(value) < 1:
                raise ValueError(f"{source} match statistics require a positive native {key}")
        options["league"] = str(int(options["league"]))
        options["season_id"] = str(int(options["season_id"]))
    options["coverage_scope"] = "match_ids"
    download = _Download(options)
    download.requested_ids = identifiers
    for identifier in identifiers:
        if source == "sofascore":
            download.expect("match", identifier)
        download.expect("match_stats", identifier)
    endpoints = (Scores365Endpoints(timezone_name="UTC") if source == "scores365" else
                 {"espn": ESPNEndpoints, "sofascore": SofascoreEndpoints}[source]())
    for identifier in identifiers:
        def commit(value):
            match, stats = value
            download.add("matches", [match], "match_id")
            download.add("match_stats", [stats], "match_id")

        def parse(data, identifier=identifier):
            data = _object(data, "response")
            return {"espn": _espn, "scores365": _scores}[source](data, options, identifier)

        if source == "sofascore":
            match = download.run("match", identifier, endpoints.event_endpoint(int(identifier)),
                                 _checked(lambda data, identifier=identifier: _sofa_event(data, options, identifier)),
                                 lambda row: download.add("matches", [row], "match_id"), download.policy.live_ttl)
            if match is None:
                download.report("match_stats", identifier, SourceError("Statistics require verified match context"))
                continue
            download.run("match_stats", identifier, endpoints.match_stats_endpoint(int(identifier)),
                         _checked(lambda data, identifier=identifier: _sofa_stats(data, identifier)),
                         lambda row: download.add("match_stats", [row], "match_id"), download.policy.live_ttl)
        else:
            url = endpoints.summary(identifier, options["league"]) if source == "espn" else endpoints.game_stats(int(identifier))
            download.run("match_stats", identifier, url, _checked(parse), commit, download.policy.live_ttl)
    return download.snapshot()
