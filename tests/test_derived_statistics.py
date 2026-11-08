"""Derived values retain missing observations, source context and formulas."""

import json
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from esd import (
    DatasetIssue,
    DatasetMetadata,
    NormalizedMatchStats,
    NormalizedPlayerMatchStats,
    NormalizedPlayerStats,
    SoccerDataset,
    derive_statistics,
    derived_statistics_to_dataframe,
    open_dataset,
)


def metrics(result):
    return {metric.name: metric for metric in result.metrics}


def test_player_match_rates_use_reported_minutes_and_preserve_identity():
    record = NormalizedPlayerMatchStats(
        "scores365", match_id="001", team_id="02", player_id="003",
        source_athlete_id="004", minutes=45, goals=1, assists=0, passes=20,
        accurate_passes=15, shots=4, shots_on_target=2, xg=0.75, xa=0.2,
    )
    result = derive_statistics(record)
    values = metrics(result)
    assert result.record is record and result.table == "player_match_stats"
    assert values["goals_per90"].value == 2
    assert values["assists_per90"].value == 0
    assert values["xg_per90"].value == 1.5
    assert values["pass_accuracy_pct"].value == 75
    assert values["shot_accuracy_pct"].value == 50
    assert values["xg_per_shot"].value == 0.1875
    formula = values["goals_per90"]
    assert (formula.numerator_field, formula.denominator_field, formula.scale) == ("goals", "minutes", 90)
    assert (formula.numerator, formula.denominator) == (1, 45)
    assert values["xg_per90"].model == "scores365"
    assert values["goals_per90"].model is None
    assert "appearances_per90" not in values and "source_rating_per90" not in values
    assert json.loads(json.dumps(result.to_dict(), allow_nan=False))["record"]["player_id"] == "003"
    with pytest.raises(FrozenInstanceError):
        formula.value = 9


@pytest.mark.parametrize("minutes,expected", [(120, 0.75), (1, 90), (90, 1)])
def test_minutes_are_not_capped_or_inferred(minutes, expected):
    row = NormalizedPlayerMatchStats("sofascore", minutes=minutes, goals=1)
    assert metrics(derive_statistics(row))["goals_per90"].value == expected


@pytest.mark.parametrize("row,name,status", [
    (NormalizedPlayerMatchStats("espn", goals=0, appearances=1), "goals_per90", "missing_denominator"),
    (NormalizedPlayerMatchStats("sofascore", minutes=90), "goals_per90", "missing_numerator"),
    (NormalizedPlayerMatchStats("sofascore", minutes=0, goals=0), "goals_per90", "zero_denominator"),
    (NormalizedPlayerMatchStats("sofascore", passes=0, accurate_passes=0), "pass_accuracy_pct", "zero_denominator"),
    (NormalizedPlayerMatchStats("sofascore", passes=5, accurate_passes=6), "pass_accuracy_pct", "inconsistent_inputs"),
    (NormalizedPlayerMatchStats("scores365", shots=2, shots_on_target=3), "shot_accuracy_pct", "inconsistent_inputs"),
])
def test_null_reasons_are_explicit(row, name, status):
    result = metrics(derive_statistics(row))[name]
    assert result.value is None and result.status == status


def test_understat_season_rates_keep_source_model_and_missing_assists():
    row = NormalizedPlayerStats("understat", competition_id="EPL", season="2024",
                                minutes=180, goals=2, shots=10, xg=1.2, npxg=1.0,
                                xg_chain=2.4, xg_buildup=0.6)
    values = metrics(derive_statistics(row))
    assert values["goals_per90"].value == 1
    assert values["npxg_per90"].value == 0.5
    assert values["xg_chain_per90"].value == 1.2
    assert values["xg_per_shot"].value == 0.12
    assert values["xg_chain_per90"].model == "understat"
    assert values["assists_per90"].value is None
    assert "pass_accuracy_pct" not in values


def test_team_sides_keep_separate_denominators_without_per90():
    row = NormalizedMatchStats("espn", match_id="001", home_passes=4,
                              home_accurate_passes=3, away_passes=2, away_accurate_passes=0,
                              home_shots=5, home_shots_on_target=2, home_xg=1.5)
    values = metrics(derive_statistics(row))
    assert values["home_pass_accuracy_pct"].value == 75
    assert values["away_pass_accuracy_pct"].value == 0
    assert values["home_shot_accuracy_pct"].value == 40
    assert values["home_xg_per_shot"].value == 0.3
    assert values["home_xg_per_shot"].model == "espn"
    assert not any(name.endswith("per90") for name in values)


@pytest.mark.parametrize("value", [True, -1, float("inf"), float("nan"), "90", 10**400])
def test_invalid_operands_raise(value):
    with pytest.raises(ValueError, match="minutes"):
        derive_statistics(NormalizedPlayerMatchStats("sofascore", minutes=value, goals=1))


def test_nonfinite_calculation_is_json_safe():
    row = NormalizedPlayerStats("understat", minutes=5e-324, goals=1)
    result = derive_statistics(row)
    assert metrics(result)["goals_per90"].status == "nonfinite_result"
    json.dumps(result.to_dict(), allow_nan=False)


def test_wrong_record_type_and_missing_source_are_rejected():
    with pytest.raises(TypeError):
        derive_statistics({"goals": 1, "minutes": 45})
    with pytest.raises(ValueError, match="source"):
        derive_statistics(NormalizedPlayerStats(""))


def test_dataframe_keeps_nullable_results_and_native_context():
    pd = pytest.importorskip("pandas")
    result = derive_statistics(NormalizedPlayerMatchStats(
        "scores365", "001", "002", "003", source_athlete_id="004", goals=0, minutes=45,
    ))
    frame = derived_statistics_to_dataframe([result])
    assert str(frame.value.dtype) == "Float64"
    assert str(frame.player_id.dtype) == "string"
    assert set(frame.source_athlete_id) == {"004"}
    assert frame.loc[frame.name == "goals_per90", "value"].iloc[0] == 0
    assert pd.isna(frame.loc[frame.name == "xg_per90", "value"].iloc[0])
    empty = derived_statistics_to_dataframe([])
    assert empty.empty and empty.dtypes.equals(frame.dtypes)
    with pytest.raises(TypeError):
        derived_statistics_to_dataframe([result.record])


def test_snapshot_round_trip_keeps_inputs_failures_and_derived_values(tmp_path):
    pytest.importorskip("pyarrow")
    stamp = datetime(2024, 1, 1, tzinfo=timezone.utc)
    row = NormalizedPlayerMatchStats("sofascore", "001", "02", "03", minutes=45, goals=1)
    dataset = SoccerDataset(
        DatasetMetadata("sofascore", "7", 2024, ("player_match_stats",), stamp, stamp,
                        coverage_scope="match_ids", requested_match_ids=("001", "002"),
                        expected_tasks=("lineups:001", "lineups:002"), successful_tasks=("lineups:001",),
                        response_fetched_at=(("lineups:001", stamp.isoformat()),),
                        cached_tasks=("lineups:001",)),
        player_match_stat_records=(row,),
        errors=(DatasetIssue("lineups", "002", "SourceBlocked", "Blocked"),),
    )
    before = derive_statistics(row)
    restored = open_dataset(dataset.save(tmp_path / "original"), match_ids=("001",))
    assert not restored.complete
    assert restored.errors == dataset.errors
    assert restored.metadata.response_fetched_at == dataset.metadata.response_fetched_at
    assert derive_statistics(restored.player_match_stat_records[0]) == before


def test_example_json_and_snapshot_modes(tmp_path, capsys):
    from examples.datasets.derived_statistics import main

    assert main(["--json"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document[0]["record"]["player_id"] == "001"
    assert next(row for row in document[1]["metrics"] if row["name"] == "goals_per90")["status"] == "missing_denominator"
    pytest.importorskip("pyarrow")
    stamp = datetime(2024, 1, 1, tzinfo=timezone.utc)
    dataset = SoccerDataset(
        DatasetMetadata("understat", "EPL", 2024, ("player_stats",), stamp, stamp),
        player_stat_records=(NormalizedPlayerStats("understat", player_id="001", minutes=180, goals=2),),
    )
    path = dataset.save(tmp_path / "snapshot")
    original = {file.name: file.read_bytes() for file in path.iterdir()}
    assert main(["--open-dir", str(path), "--table", "player_stats", "--json"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert next(row for row in document[0]["metrics"] if row["name"] == "goals_per90")["value"] == 1
    assert {file.name: file.read_bytes() for file in path.iterdir()} == original
    with pytest.raises(SystemExit) as error:
        main(["--open-dir", str(path), "--table", "player_stats", "--match-id", "001"])
    assert error.value.code == 2


def test_example_invalid_snapshot_has_actionable_error(tmp_path, capsys):
    pytest.importorskip("pyarrow")
    from examples.datasets.derived_statistics import main

    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        main(["--open-dir", str(tmp_path)])
    assert error.value.code == 2
    assert "Invalid dataset" in capsys.readouterr().err


def test_frame_retains_source_period_and_does_not_join_native_ids():
    pytest.importorskip("pandas")
    records = (NormalizedMatchStats("espn", "001", source_period="0", home_shots=4,
                                    home_shots_on_target=2),
               NormalizedMatchStats("scores365", "001", source_period="1", home_shots=10,
                                    home_shots_on_target=2))
    frame = derived_statistics_to_dataframe(map(derive_statistics, records))
    subset = frame[frame.name == "home_shot_accuracy_pct"]
    assert list(subset.source) == ["espn", "scores365"]
    assert list(subset.source_period) == ["0", "1"]
    assert list(subset.value) == [50, 20]
