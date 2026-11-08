"""Field contracts describe implemented mappings rather than column existence."""

import builtins
from dataclasses import FrozenInstanceError, fields
from unittest.mock import patch

import pytest

import esd
from esd.normalized.schema import TABLE_MODELS


@pytest.mark.parametrize("source", list(esd.get_dataset_capabilities()))
def test_all_supported_source_tables_have_frozen_field_contracts(source):
    for table in esd.get_dataset_capabilities(source).tables:
        capabilities = esd.get_dataset_field_capabilities(source, table)
        assert list(capabilities) == [field.name for field in fields(TABLE_MODELS[table])]
        assert all(value.source == source and value.table == table and value.field == name
                   and value.support in ("mapped", "context", "derived", "unavailable")
                   for name, value in capabilities.items())
        assert capabilities["source"].support == "context"
        with pytest.raises(FrozenInstanceError):
            capabilities["source"].support = "changed"
        capabilities.clear()
        assert esd.get_dataset_field_capabilities(source, table)


@pytest.mark.parametrize("source,table,field,support", [
    ("espn", "player_match_stats", "minutes", "unavailable"),
    ("scores365", "player_match_stats", "minutes", "mapped"),
    ("sofascore", "player_match_stats", "shots", "unavailable"),
    ("sofascore", "player_match_stats", "shots_on_target", "mapped"),
    ("scores365", "player_match_stats", "accurate_passes", "mapped"),
    ("espn", "shots", "xg", "unavailable"), ("espn", "shots", "x", "mapped"),
    ("sofascore", "shots", "xgot", "mapped"),
    ("understat", "shots", "body_part", "unavailable"),
    ("understat", "player_stats", "assists", "unavailable"),
    ("scores365", "standings", "deductions", "unavailable"),
    ("goaloo", "standings", "table_name", "mapped"),
    ("goaloo", "matches", "source_season_id", "mapped"),
    ("fbref", "match_stats", "home_shots", "unavailable"),
    ("fbref", "match_stats", "home_xg", "mapped"),
    ("espn", "teams", "short_name", "mapped"),
    ("sofascore", "teams", "short_name", "unavailable"),
    ("goaloo", "teams", "short_name", "mapped"),
    ("transfermarkt", "teams", "short_name", "mapped"),
    ("promiedos", "matches", "competition_name", "unavailable"),
    ("besoccer", "matches", "competition_name", "mapped"),
    ("scores365", "match_events", "event_id", "unavailable"),
    ("sofascore", "match_events", "source_order", "derived"),
    ("espn", "match_events", "rescinded", "unavailable"),
])
def test_source_specific_gaps_and_context_are_explicit(source, table, field, support):
    assert esd.get_dataset_field_capabilities(source, table)[field].support == support


def test_models_units_native_coordinates_and_separate_member_ids():
    for source, convention in (("espn", "espn-native-field"), ("understat", "understat-native"),
                               ("sofascore", "sofascore-native-player")):
        assert esd.get_dataset_field_capabilities(source, "shots")["x"].coordinate_system == convention
    assert esd.get_dataset_field_capabilities("scores365", "match_stats")["home_possession_pct"].unit == "percentage_points"
    assert esd.get_dataset_field_capabilities("espn", "match_stats")["home_xg"].model is None
    assert esd.get_dataset_field_capabilities("sofascore", "shots")["xgot"].model == "sofascore"
    assert esd.get_dataset_field_capabilities("scores365", "player_match_stats")["source_athlete_id"].notes


@pytest.mark.parametrize("source,table", [("unknown", "matches"), ("espn", "unknown"), ("scores365", "shots"),
                                        ("transfermarkt", "matches"), (None, "matches"), ([], "shots")])
def test_bad_or_unsupported_selections_raise_before_io(source, table):
    with patch("httpx.Client.request", side_effect=AssertionError("Unexpected HTTP")):
        with pytest.raises(ValueError):
            esd.get_dataset_field_capabilities(source, table)


def test_field_contracts_need_neither_pandas_arrow_nor_source_requests():
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in ("pandas", "pyarrow"):
            raise AssertionError("Optional import")
        return original(name, *args, **kwargs)

    with patch("builtins.__import__", guarded), patch("httpx.Client.request", side_effect=AssertionError("HTTP")):
        for source, contract in esd.get_dataset_capabilities().items():
            for table in contract.tables:
                assert esd.get_dataset_field_capabilities(source, table)
