"""Raw match-player adapters that preserve absent flags and source identifiers."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from ..exceptions import SourceError
from .models import NormalizedLineup, NormalizedMatch, NormalizedPlayerMatchStats

ESPN_PLAYER_METRICS = {
    "appearances": "appearances", "totalGoals": "goals", "goalAssists": "assists",
    "ownGoals": "own_goals", "totalShots": "shots", "shotsOnTarget": "shots_on_target",
    "foulsCommitted": "fouls_committed", "foulsSuffered": "fouls_suffered",
    "offsides": "offsides", "yellowCards": "yellow_cards", "redCards": "red_cards",
    "saves": "saves", "goalsConceded": "goals_conceded",
}
SCORES_PLAYER_METRICS = {
    30: "minutes", 27: "goals", 26: "assists", 3: "shots", 4: "shots_on_target", 9: "offsides",
    23: "saves", 35: "goals_conceded", 37: "fouls_suffered", 41: "interceptions",
    42: "fouls_committed", 45: "touches", 46: "key_passes", 76: "xg", 78: "xa",
}
SOFA_PLAYER_METRICS = {
    "minutesPlayed": "minutes", "goals": "goals", "goalAssist": "assists",
    "onTargetScoringAttempt": "shots_on_target", "totalPass": "passes", "accuratePass": "accurate_passes",
    "keyPass": "key_passes", "touches": "touches", "totalTackle": "tackles",
    "interceptionWon": "interceptions", "fouls": "fouls_committed", "wasFouled": "fouls_suffered",
    "offsides": "offsides", "yellowCards": "yellow_cards", "redCards": "red_cards",
    "saves": "saves", "goalsConceded": "goals_conceded", "expectedGoals": "xg", "expectedAssists": "xa",
    "rating": "source_rating",
}


@dataclass(frozen=True)
class MatchPlayerRecords:
    """Listed players and observed match statistics, without downloads or profiles."""

    lineups: tuple[NormalizedLineup, ...] = ()
    player_match_stats: tuple[NormalizedPlayerMatchStats, ...] = ()


def _object(value, label):
    if not isinstance(value, dict):
        raise SourceError(f"Missing or invalid {label} object")
    return value


def _list(value, label):
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise SourceError(f"Missing or invalid {label} list")
    return value


def _text(value):
    if value is None:
        return None
    if type(value) not in (str, int):
        raise SourceError("Expected source text or identifier")
    return str(value)


def _id(value):
    result = _text(value)
    if result is None or not result.strip() or result.strip() != result or result == "0":
        raise SourceError("Player/team records require nonblank native IDs")
    return result


def _flag(value):
    if value is not None and type(value) is not bool:
        raise SourceError("Source lineup flags must be boolean or null")
    return value


def _number(value, metric):
    if value is None or isinstance(value, str) and value.strip() in ("", "-", "--", "N/A", "n/a"):
        return None
    if type(value) not in (str, int, float):
        raise SourceError(f"Invalid player metric {metric}")
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise SourceError(f"Invalid player metric {metric}") from exc
    if not number.is_finite() or number < 0:
        raise SourceError(f"Player metric {metric} must be finite and nonnegative")
    if metric in ("xg", "xa", "source_rating"):
        result = float(number)
        if not math.isfinite(result):
            raise SourceError(f"Player metric {metric} exceeds finite range")
        return result
    if number != number.to_integral_value() or number > 2**63 - 1:
        raise SourceError(f"Player metric {metric} must be an integer count")
    return int(number)


def _put(values, metric, raw):
    value = _number(raw, metric)
    if metric in values and values[metric] != value:
        raise SourceError(f"Conflicting player metric {metric}")
    values[metric] = value


def _passes(values, raw):
    if isinstance(raw, str) and "/" in raw:
        pair = re.fullmatch(r"\s*(\d+)\s*/\s*(\d+)(?:\s*\(\s*(\d+(?:\.\d+)?)%\s*\))?\s*", raw)
        if pair is None:
            raise SourceError("Invalid completed/attempted passes value")
        accurate, total, percentage = pair.groups()
        if int(accurate) > int(total) or percentage is not None and Decimal(percentage) > 100:
            raise SourceError("Invalid completed/attempted passes counts or percentage")
        _put(values, "accurate_passes", accurate)
        _put(values, "passes", total)
    else:
        _put(values, "accurate_passes", raw)


def _espn(payload, match):
    header = _object(payload.get("header"), "ESPN header")
    if (_id(header.get("id")) != match.match_id
            or _object(header.get("league"), "ESPN league").get("slug") != match.competition_id
            or match.season is not None and str(_object(header.get("season"), "ESPN season").get("year")) != match.season):
        raise SourceError("ESPN player response differs from the supplied match")
    competitions = _list(header.get("competitions"), "ESPN competitions")
    if len(competitions) != 1 or _id(competitions[0].get("id")) != match.match_id:
        raise SourceError("ESPN player response has conflicting event IDs")
    sides = {match.home_team_id: "home", match.away_team_id: "away"}
    competitors = _list(competitions[0].get("competitors"), "ESPN competitors")
    if len(competitors) != 2 or {
        (_id(_object(item.get("team"), "ESPN team").get("id")), item.get("homeAway")) for item in competitors
    } != set(sides.items()):
        raise SourceError("ESPN player response has conflicting match teams")
    groups = _list(payload.get("rosters"), "ESPN rosters")
    seen = set()
    for group in groups:
        team = _id(_object(group.get("team"), "roster team").get("id"))
        if team not in sides or team in seen or group.get("homeAway", sides[team]) != sides[team]:
            raise SourceError("ESPN roster has an unknown, repeated or conflicting team")
        seen.add(team)
        for item in _list(group.get("roster"), "ESPN roster players"):
            athlete = _object(item.get("athlete"), "ESPN athlete")
            position = _object(item.get("position") or {}, "ESPN position")
            row = NormalizedLineup(
                "espn", match.match_id, team, _id(athlete.get("id")),
                _text(athlete.get("displayName") or athlete.get("fullName")), home_away=sides[team],
                starter=_flag(item.get("starter")), captain=_flag(item.get("captain")),
                jersey_number=_text(item.get("jersey")),
                position=_text(position.get("abbreviation") or position.get("name")),
                source_position_id=_text(position.get("id")), formation=_text(group.get("formation")),
            )
            yield row, item


def _scores(payload, match):
    game = _object(payload.get("game"), "365Scores game")
    if (_id(game.get("id")) != match.match_id or _id(game.get("competitionId")) != match.competition_id
            or match.source_season_id is not None and _text(game.get("seasonNum")) != match.source_season_id):
        raise SourceError("365Scores player response differs from the supplied match")
    members = {}
    for member in _list(game.get("members", []), "365Scores members"):
        identifier = _id(member.get("id"))
        if identifier in members:
            raise SourceError("Repeated 365Scores member ID")
        members[identifier] = member
    for side, team in (("home", match.home_team_id), ("away", match.away_team_id)):
        competitor = _object(game.get(f"{side}Competitor"), "365Scores competitor")
        if _id(competitor.get("id")) != team:
            raise SourceError("365Scores lineup team differs from match context")
        lineup = competitor.get("lineups")
        if lineup is None and game.get("hasLineups") is False:
            continue
        lineup = _object(lineup, "365Scores lineups")
        for item in _list(lineup.get("members"), "365Scores lineup members"):
            role = item.get("status")
            if role is not None and (type(role) is not int or role not in (1, 2, 3, 4)):
                raise SourceError("Unknown 365Scores lineup role")
            if role in (3, 4):
                continue
            identifier = _id(item.get("id"))
            member = members.get(identifier, {})
            if member.get("competitorId") not in (None, 0) and _id(member["competitorId"]) != team:
                raise SourceError("365Scores member belongs to another team")
            position = _object(item.get("position") or {}, "365Scores position")
            row = NormalizedLineup(
                "scores365", match.match_id, team, identifier,
                _text(member.get("name") or item.get("name")),
                source_athlete_id=_text(member.get("athleteId", item.get("athleteId"))), home_away=side,
                starter=None if role is None else role == 1, captain=_flag(item.get("isCaptain")),
                jersey_number=_text(member.get("jerseyNumber", item.get("jerseyNumber"))),
                position=_text(position.get("shortName") or position.get("name")),
                source_position_id=_text(position.get("id")), formation=_text(lineup.get("formation")),
                source_lineup_status=_text(lineup.get("status")), source_role=_text(role),
            )
            yield row, item


def _sofa(payload, match):
    if payload.get("eventId") is not None and _id(payload["eventId"]) != match.match_id:
        raise SourceError("Sofascore lineup belongs to another event")
    confirmed = _flag(payload.get("confirmed"))
    for side, team in (("home", match.home_team_id), ("away", match.away_team_id)):
        lineup = _object(payload.get(side), f"Sofascore {side} lineup")
        for item in _list(lineup.get("players"), "Sofascore players"):
            if item.get("teamId") is not None and _id(item["teamId"]) != team:
                raise SourceError("Sofascore lineup player belongs to another team")
            player = _object(item.get("player"), "Sofascore player")
            substitute = _flag(item.get("substitute"))
            row = NormalizedLineup(
                "sofascore", match.match_id, team, _id(player.get("id")), _text(player.get("name")),
                home_away=side, starter=None if substitute is None else not substitute,
                captain=_flag(item.get("captain")), jersey_number=_text(item.get("shirtNumber")),
                position=_text(item.get("position", player.get("position"))),
                formation=_text(lineup.get("formation")), confirmed=confirmed,
            )
            yield row, item


def _statistics(row, item):
    values = {}
    if row.source == "sofascore":
        raw = item.get("statistics")
        if raw is None:
            return None
        raw = _object(raw, "Sofascore player statistics")
        for key, metric in SOFA_PLAYER_METRICS.items():
            if key in raw:
                _put(values, metric, raw[key])
        available = bool(raw)
    else:
        raw = item.get("stats")
        if raw is None:
            raw = []
        raw = _list(raw, "player statistics")
        mapping = ESPN_PLAYER_METRICS if row.source == "espn" else SCORES_PLAYER_METRICS
        for stat in raw:
            key = stat.get("name") if row.source == "espn" else stat.get("type")
            if row.source == "espn" and (not isinstance(key, str) or not key) or row.source == "scores365" and type(key) is not int:
                raise SourceError("Player statistic is missing its native key")
            if row.source == "scores365" and key == 19:
                _passes(values, stat.get("value"))
            elif key in mapping:
                metric, value = mapping[key], stat.get("value", stat.get("displayValue"))
                if row.source == "scores365" and metric == "minutes" and isinstance(value, str):
                    value = value.strip().removesuffix("'")
                _put(values, metric, value)
        available = bool(raw)
        if row.source == "scores365" and item.get("ranking") is not None:
            # 365Scores uses -1 for an unrated player. Reported zero stays zero.
            rating = item["ranking"]
            if type(rating) not in (int, float) or rating != -1:
                _put(values, "source_rating", rating)
            available = available or bool(values)
    if not available:
        return None
    for accurate, total in (("accurate_passes", "passes"), ("shots_on_target", "shots")):
        if values.get(accurate) is not None and values.get(total) is not None and values[accurate] > values[total]:
            raise SourceError(f"Player {accurate} exceeds {total}")
    return NormalizedPlayerMatchStats(row.source, row.match_id, row.team_id, row.player_id,
                                      row.player_name, row.source_athlete_id, **values)


def normalize_match_players(payload: dict, *, match: NormalizedMatch, include_statistics: bool = True) -> MatchPlayerRecords:
    """Adapt ESPN summaries, 365Scores game details or Sofascore lineup responses.

    match supplies verified native match/home/away context. ESPN and 365Scores
    payload identities are checked against it. Sofascore lineup responses often
    omit their event ID; callers must obtain the response from that event's URL.
    No source requests, optional imports, profile lookups or input mutation occur.

    Only listed players are returned, excluding 365Scores missing/staff roles and
    Sofascore missingPlayers. No minutes, appearances, cards or shots are inferred.
    Positions/status labels and separate 365Scores member/athlete IDs are retained.
    include_statistics=False validates lineup structure without parsing metrics.
    """
    if not isinstance(match, NormalizedMatch) or match.source not in ("espn", "scores365", "sofascore"):
        raise TypeError("Expected an ESPN, 365Scores or Sofascore NormalizedMatch")
    if type(include_statistics) is not bool:
        raise TypeError("include_statistics must be boolean")
    if (any(not isinstance(value, str) or not value.strip() for value in
            (match.match_id, match.competition_id, match.home_team_id, match.away_team_id))
            or match.home_team_id == match.away_team_id):
        raise ValueError("Match player adapters require native match, competition and two distinct team IDs")
    payload = _object(payload, "match player response")
    lineups, statistics, seen = [], [], set()
    for row, item in {"espn": _espn, "scores365": _scores, "sofascore": _sofa}[match.source](payload, match):
        if row.player_id in seen:
            raise SourceError("A player ID is repeated within the match lineup")
        seen.add(row.player_id)
        lineups.append(row)
        stat = _statistics(row, item) if include_statistics else None
        if stat is not None:
            statistics.append(stat)
    return MatchPlayerRecords(tuple(lineups), tuple(statistics))
