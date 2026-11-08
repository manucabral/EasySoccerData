"""Diagnostic comparisons retain identity, missingness, scope and original fetches."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

import pytest

import esd

NOW = datetime(2026, 11, 3, 20, tzinfo=timezone.utc)


def dataset(source, identifier, competition, home, away, period):
    task = f"match_stats:{identifier}"
    return esd.SoccerDataset(
        esd.DatasetMetadata(source, competition, 2026, ("matches", "match_stats"), NOW, NOW,
                            expected_tasks=(task,), successful_tasks=(task,),
                            response_fetched_at=((task, NOW.isoformat()),)),
        match_records=(esd.NormalizedMatch(source, match_id=identifier, competition_id=competition,
                                           kickoff=NOW, home_team_id=home, away_team_id=away),),
        match_stat_records=(esd.NormalizedMatchStats(
            source, match_id=identifier, source_period=period, home_shots=12, away_shots=4,
            home_red_cards=0, home_possession_pct=51.5, home_xg=1.2, forecast_win=0.5),),
    )


@pytest.fixture
def pair():
    return (dataset("espn", "1", "example.cup", "10", "20", "boxscore"),
            dataset("scores365", "2", "72", "30", "40", "-1"))


@pytest.fixture
def identities():
    return esd.IdentityMap([
        esd.EntityAlias(kind, canonical, source, native)
        for kind, canonical, natives in (("competition", "cup", ("example.cup", "72")),
                                         ("team", "home", ("10", "30")), ("team", "away", ("20", "40")))
        for source, native in zip(("espn", "scores365"), natives)
    ])


def stats(dataset, **changes):
    return replace(dataset, match_stat_records=(replace(dataset.match_stat_records[0], **changes),))


def test_deltas_missing_values_and_model_boundaries(pair, identities):
    left, right = pair
    right = stats(right, home_shots=13, away_shots=4, home_red_cards=None, away_red_cards=0)
    report = esd.compare_match_statistics(left, right, identities=identities)
    rows = {row.metric: row for row in report.rows}
    assert (rows["home_shots"].status, rows["home_shots"].delta) == ("different", 1)
    assert rows["away_shots"].status == "equal" and rows["away_shots"].delta == 0
    assert rows["home_red_cards"].status == "missing_right" and rows["home_red_cards"].left_value == 0
    assert rows["away_red_cards"].status == "missing_left" and rows["away_red_cards"].right_value == 0
    assert rows["home_corners"].status == "missing_both"
    assert rows["home_xg"].status == rows["forecast_win"].status == "source_specific"
    assert rows["home_xg"].delta is None and rows["home_xg"].left_value == rows["home_xg"].right_value
    assert report.differences == (rows["home_shots"],)
    assert rows["home_xg"] in report.unresolved and rows["away_shots"] not in report.unresolved
    assert left.match_stat_records[0].home_shots == 12
    with pytest.raises(FrozenInstanceError):
        report.rows = ()


def test_decimal_tolerance_has_percentage_point_units(pair, identities):
    report = esd.compare_match_statistics(pair[0], stats(pair[1], home_possession_pct=51.6),
                                          identities=identities, metrics=["home_possession_pct"],
                                          tolerances={"home_possession_pct": 0.1})
    row, = report.rows
    assert (row.status, row.delta, row.unit) == ("equal", 0.1, "percentage_points")
    report = esd.compare_match_statistics(pair[0], stats(pair[1], home_shots=11),
                                          identities=identities, metrics=["home_shots", "home_shots"])
    assert len(report.rows) == 1 and report.rows[0].delta == -1


@pytest.mark.parametrize("period,status", [(None, "period_unknown"), ("unrecognized", "period_unknown")])
def test_unknown_period_prevents_a_delta(pair, identities, period, status):
    row, = esd.compare_match_statistics(pair[0], stats(pair[1], source_period=period),
                                        identities=identities, metrics=["home_shots"]).rows
    assert row.status == status and row.delta is None and row.right_period == period


def test_same_source_periods_and_models_remain_explicit(pair):
    left = stats(pair[0], source_period="custom-total")
    right = stats(left, home_xg=1.4)
    row, = esd.compare_match_statistics(left, right, metrics=["home_xg"]).rows
    assert row.status == "different" and row.delta == 0.2
    unknown = stats(left, source_period=None)
    assert esd.compare_match_statistics(unknown, unknown, metrics=["home_shots"]).rows[0].status == "period_unknown"
    sofa = dataset("sofascore", "1", "72", "10", "20", "ALL")
    row, = esd.compare_match_statistics(sofa, stats(sofa, source_period="1ST"), metrics=["home_shots"]).rows
    assert row.status == "period_mismatch" and row.delta is None


@pytest.mark.parametrize("missing,status", [("left", "record_missing_left"), ("right", "record_missing_right"),
                                           ("both", "record_missing_both")])
def test_missing_record_is_not_a_record_with_all_null_values(pair, identities, missing, status):
    left, right = pair
    if missing in ("left", "both"):
        left = replace(left, match_stat_records=())
    if missing in ("right", "both"):
        right = replace(right, match_stat_records=())
    row, = esd.compare_match_statistics(left, right, identities=identities, metrics=["home_shots"]).rows
    assert row.status == status and row.delta is None
    assert row.left_statistics_available == (missing == "right")
    assert row.right_statistics_available == (missing == "left")


def test_exact_original_fetches_survive_cache_and_snapshot_round_trip(pair, identities, tmp_path):
    pytest.importorskip("pyarrow")
    left, right = pair
    fetched = NOW - timedelta(days=3)
    left = replace(left, metadata=replace(left.metadata, cached_tasks=("match_stats:1",),
                                         response_fetched_at=(("match_stats:1", fetched.isoformat()),)))
    right = replace(right, metadata=replace(right.metadata, response_fetched_at=(("matches:day", NOW.isoformat()),)))
    report = esd.compare_match_statistics(left, right, identities=identities, metrics=["home_shots"])
    row, = report.rows
    assert row.left_fetched_at == fetched and row.right_fetched_at is None
    assert report.left_metadata.cached_tasks == ("match_stats:1",)
    reopened = [esd.open_dataset(item.save(tmp_path / str(i))) for i, item in enumerate((left, right))]
    assert esd.compare_match_statistics(*reopened, identities=identities, metrics=["home_shots"]) == report


def test_partial_download_errors_and_warnings_are_retained(pair, identities):
    left = replace(pair[0], metadata=replace(pair[0].metadata, expected_tasks=("match_stats:1", "match_stats:3")),
                   errors=(esd.DatasetIssue("match_stats", "3", "SourceBlocked", "Source unavailable"),))
    report = esd.compare_match_statistics(left, pair[1], identities=identities, metrics=["home_shots"])
    assert report.rows[0].status == "equal" and not report.left_complete and report.right_complete
    assert report.left_errors == left.errors and report.left_validation.warnings


def test_unmatched_and_ambiguous_matches_are_not_guessed(pair, identities):
    report = esd.compare_match_statistics(*pair)
    assert not report.rows and report.linkage.unmatched_left == ("1",)
    left, right = pair
    right = replace(right, match_records=(*right.match_records, replace(right.match_records[0], match_id="3")))
    report = esd.compare_match_statistics(left, right, identities=identities)
    assert not report.rows and report.linkage.ambiguous_left == ("1",)
    assert set(report.linkage.ambiguous_right) == {"2", "3"}


@pytest.mark.parametrize("options", [
    {"metrics": []}, {"metrics": "home_shots"}, {"metrics": ["source_period"]},
    {"metrics": [None]}, {"tolerances": []}, {"tolerances": {"home_shots": -1}},
    {"tolerances": {"home_shots": True}}, {"tolerances": {"home_shots": float("nan")}},
    {"tolerances": {"home_shots": float("inf")}}, {"tolerances": {"unknown": 1}},
    {"metrics": ["home_shots"], "tolerances": {"away_shots": 1}}, {"tolerance_seconds": -1},
    {"tolerance_seconds": True}, {"tolerance_seconds": "300"}, {"identities": []},
])
def test_invalid_options_fail_explicitly(pair, options):
    with pytest.raises(ValueError):
        esd.compare_match_statistics(*pair, **options)


@pytest.mark.parametrize("change", ["negative", "duplicate", "orphan", "missing_selection", "metadata"])
def test_invalid_datasets_are_rejected(pair, change):
    left, right = pair
    if change == "negative":
        left = stats(left, home_shots=-1)
    elif change == "duplicate":
        left = replace(left, match_stat_records=left.match_stat_records * 2)
    elif change == "orphan":
        left = stats(left, match_id="999")
    elif change == "missing_selection":
        left = replace(left, metadata=replace(left.metadata, tables=("matches",)), match_stat_records=())
    else:
        left = replace(left, metadata=None)
    with pytest.raises(ValueError):
        esd.compare_match_statistics(left, right)


def test_dataframe_nullable_values_fixed_empty_schema_and_utc(pair, identities):
    pd = pytest.importorskip("pandas")
    report = esd.compare_match_statistics(*pair, identities=identities,
                                          metrics=["home_shots", "away_red_cards", "home_xg"])
    frame = report.to_dataframe()
    empty = esd.compare_match_statistics(*pair).to_dataframe()
    assert list(empty.columns) == list(frame.columns) and empty.empty
    assert str(frame.left_value.dtype) == str(empty.delta.dtype) == "Float64"
    assert str(frame.left_statistics_available.dtype) == "boolean"
    assert str(empty.left_fetched_at.dtype) == "datetime64[ns, UTC]"
    assert pd.isna(frame.iloc[1].left_value) and pd.isna(frame.iloc[2].delta)
    assert frame.attrs == {"report": "match_statistics", "report_version": "1"}
