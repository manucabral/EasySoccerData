"""Native Sofascore shotmaps and recognized ESPN attempts, without HTTP."""

from __future__ import annotations

import json
import math

from ..exceptions import SourceError
from .match_events import _context, _espn_row, _optional_id, _sofa_time
from .match_players import _flag, _list, _number, _object, _text
from .models import NormalizedMatch, NormalizedShot

_ESPN_SHOTS = {
    "106": "on_target", "117": "off_target", "135": "blocked", "136": "woodwork",
    "70": "goal", "137": "goal", "173": "goal", "98": "penalty_scored",
    "104": "penalty_scored", "113": "penalty_missed", "115": "penalty_missed",
}


def _shot_key(row):
    return row.match_id, ("id", row.shot_id) if row.shot_id is not None else ("order", row.source_order)


def _details(item):
    return json.dumps(item, ensure_ascii=False, sort_keys=True, allow_nan=False)


def _coordinate(value):
    if value is None:
        return None
    if type(value) not in (str, int, float):
        raise SourceError("Shot coordinates must be finite numbers")
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise SourceError("Shot coordinates must be finite numbers") from exc
    if not math.isfinite(result):
        raise SourceError("Shot coordinates must be finite numbers")
    return result


def _espn(data, match):
    rows = {}
    seen = set()
    collections = [("keyEvents", _list(data.get("keyEvents", []), "ESPN keyEvents"))]
    commentary = _list(data.get("commentary", []), "ESPN commentary")
    if "keyEvents" not in data and "commentary" not in data:
        raise SourceError("ESPN shots require keyEvents or commentary")
    collections.append(("commentary.play", [entry.get("play") for entry in commentary]))
    for collection, items in collections:
        for index, item in enumerate(items):
            if item is None:
                continue
            item = _object(item, "ESPN shot play")
            native_type = _text(_object(item.get("type"), "ESPN shot type").get("id"))
            if native_type not in _ESPN_SHOTS:
                continue
            # The event adapter keeps clock, period and shootout semantics shared.
            event = _espn_row(item, match, collection, index)
            if (collection, event.event_id) in seen:
                raise SourceError("Repeated ESPN shot ID in one collection")
            seen.add((collection, event.event_id))
            row = NormalizedShot(
                source="espn", match_id=match.match_id, shot_id=event.event_id,
                source_order=index, source_collection=collection, source_type_id=native_type,
                player_id=event.player_id, player_name=event.player_name, team_id=event.team_id,
                home_away="home" if event.team_id == match.home_team_id else "away" if event.team_id == match.away_team_id else None,
                minute=event.minute, added_minute=event.added_minute, clock_seconds=event.clock_seconds,
                source_period=event.source_period, is_shootout=event.is_shootout,
                result=_ESPN_SHOTS[native_type], source_shot_type=event.source_type_name,
                coordinate_system="espn-native-field" if item.get("fieldPositionX") is not None or item.get("fieldPositionY") is not None else None,
                x=_coordinate(item.get("fieldPositionX")), y=_coordinate(item.get("fieldPositionY")),
                source_details_json=_details(item),
            )
            previous = rows.get(row.shot_id)
            if previous is not None:
                for field in ("source_type_id", "source_period", "team_id", "player_id", "is_shootout", "minute", "added_minute", "coordinate_system", "x", "y"):
                    first, second = getattr(previous, field), getattr(row, field)
                    if first is not None and second is not None and first != second:
                        raise SourceError("Conflicting ESPN representations of one shot")
                continue
            rows[row.shot_id] = row
    return tuple(rows.values())


def _sofa(data, match):
    if data.get("eventId") is not None and _optional_id(data["eventId"]) != match.match_id:
        raise SourceError("Sofascore shotmap belongs to another event")
    for index, item in enumerate(_list(data.get("shotmap"), "Sofascore shotmap")):
        if not _text(item.get("shotType")):
            raise SourceError("Sofascore shot is missing its native shotType")
        player = _object(item.get("player") or {}, "Sofascore shot player")
        coordinates = _object(item.get("playerCoordinates") or {}, "Sofascore player coordinates")
        is_home = _flag(item.get("isHome"))
        team = None if is_home is None else match.home_team_id if is_home else match.away_team_id
        explicit_team = _optional_id(item.get("teamId"))
        if explicit_team is not None:
            if team is not None and explicit_team != team:
                raise SourceError("Sofascore shot teamId conflicts with isHome")
            team = explicit_team
        shootout = _flag(item.get("isShootout"))
        xg, xgot = _number(item.get("xg"), "xg"), _number(item.get("xgot"), "xg")
        yield NormalizedShot(
            source="sofascore", match_id=match.match_id, shot_id=_optional_id(item.get("id")),
            source_order=index, source_collection="shotmap", source_type_id=_text(item.get("shotType")),
            player_id=_optional_id(player.get("id")), player_name=_text(player.get("name") or player.get("shortName")),
            team_id=team, home_away="home" if team == match.home_team_id else "away" if team == match.away_team_id else None,
            minute=None if shootout else _sofa_time(item.get("time"), "minute"),
            added_minute=None if shootout else _sofa_time(item.get("addedTime"), "added_minute"),
            clock_seconds=_sofa_time(item.get("timeSeconds"), "xg"), source_period=_text(item.get("period")),
            is_shootout=shootout, result=_text(item.get("shotType")), situation=_text(item.get("situation")),
            body_part=_text(item.get("bodyPart")), source_shot_type=_text(item.get("shotType")),
            coordinate_system="sofascore-native-player" if coordinates else None,
            x=_coordinate(coordinates.get("x")), y=_coordinate(coordinates.get("y")),
            xg=xg, xgot=xgot, xg_model="sofascore" if xg is not None or xgot is not None else None,
            source_details_json=_details(item),
        )


def normalize_match_shots(payload: dict, *, match: NormalizedMatch) -> tuple[NormalizedShot, ...]:
    """Read a Sofascore shotmap or recognized ESPN attempts for verified context.

    ESPN goals and attempts from keyEvents/commentary.play use native play IDs,
    deduplicating across collections. This is a partial feed, with native
    fieldPositionX/Y when reported and no inferred xG. Own goals are excluded.
    Sofascore retains player coordinates, body part, xG/xGOT and the entire native
    shot object, including goal-mouth coordinates. Missing flags remain unknown.
    No scale, orientation, period or model version is inferred. An explicit
    empty collection is valid; a missing required collection fails.
    """
    if not isinstance(match, NormalizedMatch) or match.source not in ("espn", "sofascore"):
        raise ValueError("Match shots require an ESPN or Sofascore NormalizedMatch")
    data = _context(_object(payload, "shot response"), match)
    result = tuple(_espn(data, match) if match.source == "espn" else _sofa(data, match))
    seen = set()
    for row in result:
        if row.team_id is not None and row.team_id not in (match.home_team_id, match.away_team_id):
            raise SourceError("Shot team is outside the supplied match")
        key = _shot_key(row)
        if key in seen:
            raise SourceError("Repeated source shot key within one match")
        seen.add(key)
    return result
