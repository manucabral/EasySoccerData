"""Normalize ESPN summary events and 365Scores game events without HTTP."""

from __future__ import annotations

import json
import re
from dataclasses import replace

from ..exceptions import SourceError
from .match_players import _flag, _id, _list, _number, _object, _text
from .models import NormalizedMatch, NormalizedMatchEvent

ESPN_EVENT_TYPES = {
    "70": "goal", "137": "goal", "173": "goal", "97": "own_goal",
    "98": "penalty_scored", "104": "penalty_scored",
    "113": "penalty_missed", "115": "penalty_missed",
    "94": "yellow_card", "93": "red_card", "76": "substitution",
}
EVENT_TYPES = frozenset((*ESPN_EVENT_TYPES.values(), "other"))


def _event_key(row):
    """Response-local key; a 365Scores order is not a persistent event ID."""
    return row.match_id, ("id", row.event_id) if row.event_id is not None else ("order", row.source_order)


def _optional_id(value):
    return None if value is None else _id(value)


def _context(payload, match):
    sides = {match.home_team_id: "home", match.away_team_id: "away"}
    if None in sides or len(sides) != 2 or not match.match_id or not match.competition_id:
        raise SourceError("Events require a match with native competition and two team IDs")
    if match.source == "espn":
        header = _object(payload.get("header"), "ESPN header")
        competitions = _list(header.get("competitions"), "ESPN competitions")
        if (_id(header.get("id")) != match.match_id
                or _object(header.get("league"), "ESPN league").get("slug") != match.competition_id
                or match.season is not None and _text(_object(header.get("season"), "ESPN season").get("year")) != match.season
                or len(competitions) != 1 or _id(competitions[0].get("id")) != match.match_id):
            raise SourceError("ESPN events differ from the supplied match context")
        competitors = _list(competitions[0].get("competitors"), "ESPN competitors")
        if len(competitors) != 2 or {
            (_id(_object(item.get("team"), "ESPN team").get("id")), item.get("homeAway")) for item in competitors
        } != set(sides.items()):
            raise SourceError("ESPN event response has conflicting match teams")
        return payload
    game = _object(payload.get("game"), "365Scores game")
    if (_id(game.get("id")) != match.match_id or _id(game.get("competitionId")) != match.competition_id
            or type(game.get("sportId")) is not int or game["sportId"] != 1
            or match.source_season_id is not None and _text(game.get("seasonNum")) != match.source_season_id
            or any(_id(_object(game.get(f"{side}Competitor"), "365Scores competitor").get("id")) != team
                   for team, side in sides.items())):
        raise SourceError("365Scores events differ from the supplied match context")
    return game


def _clock(text):
    if not text:
        return None, None
    parsed = re.fullmatch(r"\s*(\d+)\s*['\u2032]?(?:\s*\+\s*(\d+)\s*['\u2032]?)?\s*", text)
    if parsed is None:
        return None, None
    minute, added = parsed.groups()
    return _number(minute, "minute"), _number(added, "added_minute")


def _espn_row(item, match, collection, order=None):
    kind = _object(item.get("type"), "ESPN event type")
    native_type = _id(kind.get("id"))
    period = _text(_object(item.get("period") or {}, "ESPN period").get("number"))
    clock = _object(item.get("clock") or {}, "ESPN clock")
    display = _text(clock.get("displayValue"))
    shootout = _flag(item.get("shootout"))
    # ESPN period 5 explicitly identifies the shootout even when the flag is absent.
    if period == "5" and native_type in ("104", "113", "115"):
        if shootout is False:
            raise SourceError("ESPN penalty period conflicts with its shootout flag")
        shootout = True
    minute, added = (None, None) if shootout else _clock(display)
    team = _object(item.get("team") or {}, "ESPN event team")
    participants = _list(item.get("participants", []), "ESPN event participants")
    athletes = [_object(person.get("athlete"), "ESPN event athlete") for person in participants]
    values = {}
    for prefix, athlete in zip(("", "related_"), athletes):
        values[prefix + "player_id"] = _optional_id(athlete.get("id"))
        values[prefix + "player_name"] = _text(athlete.get("displayName") or athlete.get("fullName"))
    return NormalizedMatchEvent(
        "espn", match.match_id, _id(item.get("id")), source_order=order, source_collection=collection,
        event_type=ESPN_EVENT_TYPES.get(native_type, "other"), source_type_id=native_type,
        source_type_name=_text(kind.get("text")), source_period=period,
        minute=minute, added_minute=added, clock_seconds=_number(clock.get("value"), "xg"),
        source_clock=display, is_shootout=shootout, scoring_play=_flag(item.get("scoringPlay")),
        team_id=_optional_id(team.get("id")), team_name=_text(team.get("displayName")),
        source_participants_json=json.dumps(participants, ensure_ascii=False, sort_keys=True),
        source_text=_text(item.get("text")), **values,
    )


def _espn(data, match):
    rows = {}
    for item in _list(data.get("keyEvents"), "ESPN keyEvents"):
        row = _espn_row(item, match, "keyEvents")
        if row.event_id in rows:
            raise SourceError("Repeated ESPN key event ID")
        rows[row.event_id] = row
    for entry in _list(data.get("commentary", []), "ESPN commentary"):
        play = entry.get("play")
        if play is None:
            continue
        play = _object(play, "ESPN commentary play")
        kind = _object(play.get("type"), "ESPN commentary event type")
        if _text(kind.get("id")) not in ESPN_EVENT_TYPES:
            continue
        row = _espn_row(play, match, "commentary.play", _number(entry.get("sequence"), "source_order"))
        previous = rows.get(row.event_id)
        if previous is not None:
            for field in ("source_type_id", "source_period", "team_id", "player_id", "related_player_id"):
                first, second = getattr(previous, field), getattr(row, field)
                if first is not None and second is not None and first != second:
                    raise SourceError("Conflicting ESPN representations of one event")
            continue
        rows[row.event_id] = row
    return tuple(rows.values())


def _scores(data, match):
    members = {}
    for member in _list(data.get("members", []), "365Scores event members"):
        # The source can include an anonymous member containing only competitorId.
        if member.get("id") is None:
            continue
        identifier = _id(member.get("id"))
        if identifier in members:
            raise SourceError("Repeated 365Scores event member ID")
        members[identifier] = member
    rows = []
    for item in _list(data.get("events"), "365Scores events"):
        kind = _object(item.get("eventType"), "365Scores event type")
        native_type, subtype = _id(kind.get("id")), _text(kind.get("subTypeId"))
        event_type = {"1": "goal", "2": "yellow_card", "3": "red_card", "6": "penalty_missed", "1000": "substitution"}.get(native_type, "other")
        if native_type == "1":
            event_type = {"2": "own_goal", "3": "penalty_scored"}.get(subtype, "goal")
        period = _text(item.get("stageId"))
        shootout = None if period is None else period == "11"
        game_time = _number(item.get("gameTime"), "xg")
        minute = None if shootout is not False or game_time is None else _number(game_time, "minute")
        added = None if shootout else _number(item.get("addedTime"), "added_minute")
        order = _number(item.get("order"), "source_order")
        if order is None:
            raise SourceError("365Scores events require a native order within the match")
        extras = item.get("extraPlayers", [])
        if not isinstance(extras, list):
            raise SourceError("Invalid 365Scores extraPlayers")
        ids = [_optional_id(item.get("playerId")), *[_id(value) for value in extras]]
        values = {}
        for prefix, identifier in zip(("", "related_"), ids):
            member = members.get(identifier, {})
            values[prefix + "player_id"] = identifier
            values[prefix + "player_name"] = _text(member.get("name"))
            values[("related_" if prefix else "") + "source_athlete_id"] = _optional_id(member.get("athleteId"))
        rows.append(NormalizedMatchEvent(
            "scores365", match.match_id, source_order=order, source_collection="game.events",
            event_type=event_type, source_type_id=native_type, source_type_name=_text(kind.get("name")),
            source_subtype_id=subtype, source_subtype_name=_text(kind.get("subTypeName")),
            source_period=period, source_status_id=_text(item.get("statusId")),
            minute=minute, added_minute=added, source_game_time=game_time,
            source_clock=_text(item.get("gameTimeDisplay")), is_shootout=shootout,
            team_id=_optional_id(item.get("competitorId")),
            source_participants_json=json.dumps({"playerId": item.get("playerId"), "extraPlayers": extras}, sort_keys=True),
            **values,
        ))
    return tuple(rows)


def normalize_match_events(payload: dict, *, match: NormalizedMatch) -> tuple[NormalizedMatchEvent, ...]:
    """Read native event lists for ESPN/365Scores, without names-to-ID matching.

    Missing lists fail explicitly; an explicit empty list is valid. ESPN keeps
    keyEvents and adds recognized goals/cards/substitutions from commentary.play,
    deduplicating by native event ID. Existing keyEvents records take precedence.
    Their collection order is retained, then commentary-only records are appended.
    Native periods and source clock text are preserved; unknown types stay other.
    365Scores stage 11 denotes the shootout. Its 121+ counters stay exclusively in
    source_game_time. No event is used to recalculate the match score.
    """
    if not isinstance(match, NormalizedMatch) or match.source not in ("espn", "scores365"):
        raise ValueError("Match events support an ESPN or 365Scores NormalizedMatch")
    data = _context(_object(payload, "event response"), match)
    rows = _espn(data, match) if match.source == "espn" else _scores(data, match)
    seen = set()
    result = []
    for row in rows:
        if row.team_id is not None and row.team_id not in (match.home_team_id, match.away_team_id):
            raise SourceError("Event team is outside the supplied match")
        key = _event_key(row)
        if key in seen:
            raise SourceError("Repeated source event key within one match")
        seen.add(key)
        if row.event_type == "substitution":
            row = replace(row, player_role="incoming", related_player_role="outgoing")
        result.append(row)
    return tuple(result)
