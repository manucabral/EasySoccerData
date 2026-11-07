"""DataFrame exports preserve source values and support explicit schemas."""

from copy import deepcopy
from dataclasses import asdict

import pytest

from esd import to_dataframe
from esd.espn.types import ESPNMatch, ESPNStandingRow, ESPNTeam
from esd.scores365.types.standing import StandingRow
from esd.sofascore.types.event import Event
from esd.understat.types import UnderstatShot

pd = pytest.importorskip("pandas")


def test_default_export_preserves_existing_structure_and_types():
    matches = [ESPNMatch(id="001", home_team=ESPNTeam(name="Home", score=0))]
    pd.testing.assert_frame_equal(
        to_dataframe(matches), pd.DataFrame([asdict(match) for match in matches])
    )


def test_flat_matches_preserve_ids_nulls_zero_and_utc_dates():
    matches = [
        ESPNMatch(id="001", date="2026-11-06T18:00:00-03:00",
                  home_team=ESPNTeam(name="Home", score=0)),
        ESPNMatch(id="002", date=None, home_team=ESPNTeam(name="Next", score=None)),
        ESPNMatch(id="003", date="2026-11-07T21:00Z"),
    ]
    original = deepcopy(matches)
    frame = to_dataframe(matches, flatten=True, convert_dtypes=True,
                         dtypes={"id": "string", "home_team.score": "Int64"},
                         datetime_columns={"date": None})
    assert frame["id"].tolist() == ["001", "002", "003"]
    assert frame.loc[0, "home_team.score"] == 0
    assert pd.isna(frame.loc[1, "home_team.score"])
    assert str(frame["home_team.score"].dtype) == "Int64"
    assert str(frame["completed"].dtype) == "boolean"
    assert frame.loc[0, "date"] == pd.Timestamp("2026-11-06T21:00Z")
    assert pd.isna(frame.loc[1, "date"])
    assert str(frame["date"].dt.tz) == "UTC"
    assert matches == original


def test_standings_can_be_sorted_filtered_and_joined():
    rows = [
        ESPNStandingRow(team=ESPNTeam(id="001", name="Home"), points=0, rank=2),
        ESPNStandingRow(team=ESPNTeam(id="002", name="Away"), points=3, rank=1),
    ]
    frame = to_dataframe(rows, flatten=True, convert_dtypes=True)
    assert str(frame["points"].dtype) == "Int64"
    assert frame.sort_values("points", ascending=False).iloc[0]["team.name"] == "Away"
    assert frame.loc[frame["points"] == 0, "team.id"].tolist() == ["001"]
    teams = to_dataframe([row.team for row in rows], convert_dtypes=True)
    joined = frame.merge(teams, left_on="team.id", right_on="id", validate="one_to_one")
    assert joined["name"].tolist() == ["Home", "Away"]


def test_nested_lists_are_not_exploded_or_shared_with_source():
    row = StandingRow(recent_form=[1, 2, 3])
    frame = to_dataframe([row], flatten=True, convert_dtypes=True)
    assert len(frame) == 1
    assert frame.loc[0, "recent_form"] == [1, 2, 3]
    frame.loc[0, "recent_form"].append(4)
    assert row.recent_form == [1, 2, 3]


@pytest.mark.parametrize("unit, timestamp, expected", [
    ("s", 0, "1970-01-01T00:00Z"),
    ("s", 86400, "1970-01-02T00:00Z"),
    ("ms", 86400000, "1970-01-02T00:00Z"),
])
def test_unix_dates_use_explicit_units_and_preserve_epoch_zero(unit, timestamp, expected):
    frame = to_dataframe([Event(start_timestamp=timestamp)],
                         datetime_columns={"start_timestamp": unit})
    assert frame.loc[0, "start_timestamp"] == pd.Timestamp(expected)


def test_naive_dates_follow_the_documented_utc_convention():
    frame = to_dataframe([ESPNMatch(date="2026-11-06 18:00:00")],
                         datetime_columns={"date": None})
    assert frame.loc[0, "date"] == pd.Timestamp("2026-11-06T18:00Z")


def test_nullable_floats_keep_fractional_values_and_missing_values():
    frame = to_dataframe([UnderstatShot(xg=0.25), UnderstatShot(xg=None)],
                         convert_dtypes=True)
    assert str(frame["xg"].dtype) == "Float64"
    assert frame.loc[0, "xg"] == 0.25
    assert pd.isna(frame.loc[1, "xg"])


@pytest.mark.parametrize("flatten", [False, True])
def test_empty_exports_can_have_a_declared_schema(flatten):
    assert to_dataframe([], flatten=flatten).shape == (0, 0)
    frame = to_dataframe([], flatten=flatten, dtypes={"id": "string", "score": "Int64"},
                         datetime_columns={"date": None})
    assert frame.columns.tolist() == ["id", "score", "date"]
    assert str(frame["score"].dtype) == "Int64"
    assert str(frame["id"].dtype) == "string"
    assert str(frame["date"].dt.tz) == "UTC"


@pytest.mark.parametrize("options", [
    {"dtypes": {"typo": "Int64"}}, {"datetime_columns": {"typo": None}},
])
def test_unknown_columns_raise(options):
    with pytest.raises(KeyError, match="typo"):
        to_dataframe([ESPNMatch()], **options)


def test_invalid_dates_and_conflicting_types_raise():
    with pytest.raises(ValueError):
        to_dataframe([ESPNMatch(date="invalid")], datetime_columns={"date": None})
    with pytest.raises(ValueError, match="datetime_columns"):
        to_dataframe([], dtypes={"date": "string"}, datetime_columns={"date": None})


def test_explicit_types_apply_to_columns_with_only_missing_values():
    frame = to_dataframe([ESPNMatch(), ESPNMatch()], flatten=True,
                         dtypes={"home_team.score": "Int64"})
    assert str(frame["home_team.score"].dtype) == "Int64"
    assert frame["home_team.score"].isna().all()
