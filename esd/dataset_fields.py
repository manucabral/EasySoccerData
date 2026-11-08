"""Column contracts for implemented dataset adapters, without source requests."""

from __future__ import annotations

from dataclasses import dataclass, fields

from .dataset_capabilities import get_dataset_capabilities
from .normalized.schema import TABLE_MODELS, _column_dtype


@dataclass(frozen=True)
class DatasetFieldCapability:
    """One adapter column, independent of coverage in a league or response.

    support is mapped, context, derived or unavailable. mapped means the adapter
    has a source mapping, not that every response supplies a value. context uses
    query/verified match context or a source label. derived uses an explicit
    normalization rule, such as a side flag or response position. unavailable
    means the current dataset adapter leaves the column null. Contracts describe
    load_dataset(), whose columns can differ from individual client models.
    """

    source: str
    table: str
    field: str
    dtype: str
    support: str
    unit: str | None = None
    model: str | None = None
    coordinate_system: str | None = None
    notes: tuple[str, ...] = ()


def _names(text):
    return set(text.split())


_MATCH = _names("match_id competition_id season kickoff home_team_id home_team_name away_team_id away_team_name home_score away_score source_status source_status_text")
_STANDING = _names("competition_id season team_id team_name rank played won drawn lost goals_for goals_against goal_difference points")
_PLAYER = _names("match_id team_id player_id player_name")
_LINEUP = _PLAYER | _names("home_away starter captain jersey_number position formation")
_EVENT = _names("match_id source_order source_collection event_type source_type_id source_period minute added_minute is_shootout team_id player_id player_name related_player_id related_player_name source_participants_json player_role related_player_role")
_SHOT = _names("shot_id match_id player_id player_name minute home_away result source_shot_type coordinate_system x y")


def _mapped(source, table):
    if table == "matches":
        result = set(_MATCH)
        if source in ("scores365", "sofascore", "goaloo", "besoccer"):
            result.add("competition_name")
        if source in ("scores365", "sofascore", "goaloo"):
            result.add("source_season_id")
        if source == "scores365":
            result.add("stage_id")
        if source == "fbref":
            result -= {"source_status", "source_status_text"}
        if source == "understat":
            result.discard("source_status_text")
        return result
    if table == "teams":
        # Most loaders build teams from normalized matches, omitting short_name.
        return _names("team_id name short_name" if source in ("espn", "goaloo", "transfermarkt") else "team_id name")
    if table == "standings":
        result = set(_STANDING)
        if source in ("espn", "sofascore"):
            result.add("table_id")
        if source in ("espn", "scores365", "sofascore", "goaloo"):
            result.add("table_name")
        if source in ("scores365", "sofascore", "goaloo"):
            result.add("source_season_id")
        if source == "scores365":
            result |= {"stage_id", "group_id"}
        if source == "espn":
            result.add("deductions")
        return result
    if table == "match_stats":
        from ._match_statistics import ESPN_METRICS, SCORES_METRICS, SOFA_METRICS

        if source in ("understat", "fbref"):
            return _names("match_id home_xg away_xg") | (_names("forecast_win forecast_draw forecast_loss") if source == "understat" else set())
        mapping = {"espn": ESPN_METRICS, "scores365": SCORES_METRICS, "sofascore": SOFA_METRICS}[source]
        return {"match_id", "source_period", *(f"{side}_{metric}" for side in ("home", "away") for metric in mapping.values())}
    if table == "lineups":
        result = set(_LINEUP)
        if source == "scores365":
            result |= _names("source_athlete_id source_position_id source_lineup_status source_role")
        elif source == "espn":
            result.add("source_position_id")
        else:
            result.add("confirmed")
        return result
    if table == "player_match_stats":
        from .normalized.match_players import (
            ESPN_PLAYER_METRICS,
            SCORES_PLAYER_METRICS,
            SOFA_PLAYER_METRICS,
        )

        mapping = {"espn": ESPN_PLAYER_METRICS, "scores365": SCORES_PLAYER_METRICS, "sofascore": SOFA_PLAYER_METRICS}[source]
        result = _PLAYER | set(mapping.values())
        if source == "scores365":
            result |= _names("source_athlete_id passes accurate_passes source_rating")
        return result
    if table == "match_events":
        result = set(_EVENT)
        if source == "espn":
            result |= _names("event_id source_type_name clock_seconds source_clock scoring_play team_name source_text")
        elif source == "scores365":
            result |= _names("source_type_name source_subtype_id source_subtype_name source_status_id source_game_time source_clock source_athlete_id related_source_athlete_id")
        else:
            result |= _names("event_id source_subtype_id clock_seconds source_game_time source_clock source_text rescinded source_details_json")
        return result
    if table == "shots":
        result = set(_SHOT)
        if source == "understat":
            return result | _names("situation source_date xg xg_model")
        result |= _names("team_id source_order source_collection source_type_id source_period added_minute clock_seconds is_shootout source_details_json")
        if source == "sofascore":
            result |= _names("situation body_part xg xgot xg_model")
        return result
    if table == "player_stats":
        return _names("competition_id season player_id player_name source_team_names position games minutes goals shots key_passes yellow_cards red_cards xg xa npxg xg_chain xg_buildup")
    return {
        "players": _names("player_id name team_id position source_birth_date market_value currency"),
        "market_values": _names("player_id team_id source_season_id source_date value currency"),
        "transfers": _names("transfer_id player_id source_season source_date from_team_id to_team_id fee source_fee_display source_pending source_transfer_type"),
    }[table]


def _support(source, table, field, mapped):
    if field == "source":
        return "context"
    if field not in mapped:
        return "unavailable"
    if field == "season" or field in ("coordinate_system", "xg_model", "source_collection"):
        return "context"
    if field == "competition_id" and source != "scores365" or field == "match_id" and table in ("match_stats", "lineups", "player_match_stats", "match_events", "shots") and source != "understat":
        return "context"
    if field == "source_order" and (source == "sofascore" or table == "shots"):
        return "derived"
    if table == "lineups" and field in ("home_away", "starter") and (field == "home_away" or source != "espn"):
        return "derived"
    if table == "match_events" and field in ("event_type", "player_role", "related_player_role"):
        return "derived"
    if table == "shots" and field == "home_away" and source != "understat":
        return "derived"
    return "mapped"


def get_dataset_field_capabilities(source: str, table: str) -> dict[str, DatasetFieldCapability]:
    """Return a fresh field mapping for one supported source/table, without HTTP.

    All normalized columns appear, including unavailable ones. dtype describes
    optional DataFrame export without importing pandas. Model/coordinate labels
    preserve source conventions, not shared definitions. No league or historical
    coverage is promised. Unknown sources, tables or unsupported pairs raise
    ValueError. Individual client methods can expose additional native fields.
    """
    if not isinstance(source, str) or not isinstance(table, str):
        raise ValueError("source and table must be strings")
    contract = get_dataset_capabilities(source)
    if table not in contract.tables:
        raise ValueError(f"Unsupported dataset table {table!r} for {source}")
    mapped = _mapped(source, table)
    result = {}
    for item in fields(TABLE_MODELS[table]):
        name = item.name
        support = _support(source, table, name, mapped)
        unit = model = coordinate = None
        notes = []
        if support == "unavailable":
            notes.append("The current dataset adapter does not populate this column.")
        else:
            if name in ("minute", "added_minute", "minutes"):
                unit = "minutes"
            elif name == "clock_seconds":
                unit = "seconds"
            elif name.endswith("possession_pct"):
                unit = "percentage_points"
            elif name in ("x", "y", "coordinate_system"):
                coordinate = {"espn": "espn-native-field", "sofascore": "sofascore-native-player", "understat": "understat-native"}[source]
                unit = "native_coordinates" if name in ("x", "y") else None
                notes.append("Native axes; scale and playing direction are not inferred.")
            if name in ("xg", "xgot", "xa", "npxg", "xg_chain", "xg_buildup", "home_xg", "away_xg", "forecast_win", "forecast_draw", "forecast_loss", "source_rating", "xg_model"):
                model = source
                notes.append("Provider-specific metric/model; no common definition or model version is asserted.")
            if name == "source_athlete_id" or name == "related_source_athlete_id":
                notes.append("365Scores athlete ID is distinct from the normalized member player_id.")
            if name == "team_id" and table == "match_events":
                notes.append("An own-goal event team can be the beneficiary, not the player's lineup team.")
            if name == "source_order":
                notes.append("Order is local to this response, not a persistent event/shot ID.")
            if source == "espn" and table == "teams" and name == "short_name":
                notes.append("The season loader retains short names; explicit detail downloads derive teams from matches and leave this field null.")
        result[name] = DatasetFieldCapability(source, table, name, _column_dtype(name), support,
                                              unit, model, coordinate, tuple(notes))
    return result
