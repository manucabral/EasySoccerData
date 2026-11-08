"""Coverage counts existing values and attributes recorded failures to their tables."""

import builtins
import json
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

import esd

NOW = datetime(2026, 11, 8, tzinfo=timezone.utc)


def dataset(source="espn", tables=("lineups", "player_match_stats"), **metadata):
    return esd.SoccerDataset(esd.DatasetMetadata(source, "example.cup", 2026, tables, NOW, NOW, **metadata))


def field(report, table, name):
    return next(row for row in report.fields if row.table == table and row.field == name)


def test_presence_zeros_flags_and_rows_are_independent_of_task_completeness():
    data = dataset(expected_tasks=("match_details:1", "match_details:2"), successful_tasks=("match_details:1",),
                   coverage_scope="match_ids", requested_match_ids=("1", "2"))
    data = replace(data, lineup_records=(esd.NormalizedLineup("espn", "1", "10", "101", starter=False),
                                        esd.NormalizedLineup("espn", "1", "10", "102", starter=None)),
                   player_match_stat_records=(esd.NormalizedPlayerMatchStats("espn", "1", "10", "101", goals=0),
                                              esd.NormalizedPlayerMatchStats("espn", "1", "10", "102", goals=None)))
    report = esd.inspect_dataset_coverage(data)
    goals = field(report, "player_match_stats", "goals")
    assert (goals.present_count, goals.missing_count, goals.zero_count, goals.present_ratio) == (1, 1, 1, 0.5)
    starter = field(report, "lineups", "starter")
    assert (starter.present_count, starter.missing_count, starter.zero_count, starter.true_count, starter.false_count) == (1, 1, None, 0, 1)
    assert starter.status == goals.status == "partial"
    assert not report.complete and all(row.task_status == "partial" for row in report.tables)
    assert [task.status for task in report.tasks] == ["successful", "pending"]
    with pytest.raises(FrozenInstanceError):
        report.complete = True


def test_successful_empty_failed_and_unknown_tables_are_distinct():
    empty = dataset(tables=("standings",), expected_tasks=("standings:2026",), successful_tasks=("standings:2026",))
    report = esd.inspect_dataset_coverage(empty)
    row = field(report, "standings", "points")
    assert row.status == "empty" and row.present_ratio is None and row.zero_count == 0
    assert report.tables[0].task_status == "complete" and report.complete
    failed = replace(empty, metadata=replace(empty.metadata, successful_tasks=()),
                     errors=(esd.DatasetIssue("standings", "2026", "SourceBlocked", "HTTP 403"),))
    report = esd.inspect_dataset_coverage(failed)
    assert report.tables[0].task_status == "failed" and not report.complete
    assert report.tasks[0].errors == failed.errors
    assert esd.inspect_dataset_coverage(dataset(tables=("standings",))).tables[0].task_status == "unknown"


def test_sofa_context_success_does_not_establish_shot_or_player_success():
    data = dataset("sofascore", tables=("shots", "lineups"), expected_tasks=("match:1", "shots:1", "lineups:1"),
                   successful_tasks=("match:1", "lineups:1"), coverage_scope="match_ids", requested_match_ids=("1",))
    data = replace(data, errors=(esd.DatasetIssue("shots", "1", "SourceBlocked", "HTTP 403"),))
    report = esd.inspect_dataset_coverage(data)
    assert report.tables[0].task_status == "failed" and report.tables[1].task_status == "complete"
    assert report.tables[0].task_keys == ("match:1", "shots:1")
    assert report.tables[1].task_keys == ("match:1", "lineups:1")


def test_missing_sofa_detail_tasks_remain_unknown_even_with_complete_context_metadata():
    data = dataset("sofascore", tables=("shots", "lineups"), expected_tasks=("match:1",),
                   successful_tasks=("match:1",), coverage_scope="match_ids", requested_match_ids=("1",))
    report = esd.inspect_dataset_coverage(data)
    assert report.complete and all(table.task_status == "unknown" for table in report.tables)
    assert all(table.row_count == 0 for table in report.tables)


def test_opaque_legacy_task_keys_are_preserved_without_inventing_table_evidence():
    data = dataset("sofascore", tables=("shots",), expected_tasks=("shots",), successful_tasks=("shots",),
                   coverage_scope="match_ids", requested_match_ids=("1",))
    report = esd.inspect_dataset_coverage(data)
    assert report.tasks[0].key == "shots" and report.tasks[0].status == "successful"
    assert report.tables[0].task_status == "unknown" and not report.tables[0].task_keys


def test_understat_missing_explicit_shot_tasks_do_not_become_an_empty_success():
    data = dataset("understat", tables=("shots",), expected_tasks=("season:2026",),
                   successful_tasks=("season:2026",), requested_match_ids=("1",))
    assert esd.inspect_dataset_coverage(data).tables[0].task_status == "unknown"
    empty_selection = replace(data, metadata=replace(data.metadata, requested_match_ids=()))
    assert esd.inspect_dataset_coverage(empty_selection).tables[0].task_status == "complete"


@pytest.mark.parametrize("source,table,tasks", [
    ("sofascore", "shots", ("match:1", "match:2", "shots:1")),
    ("espn", "player_match_stats", ("match_details:1",)),
    ("scores365", "lineups", ("lineups:1",)),
    ("understat", "shots", ("season:2026", "shots:1")),
])
def test_missing_task_evidence_for_one_requested_match_keeps_table_partial(source, table, tasks):
    data = dataset(source, tables=(table,), expected_tasks=tasks, successful_tasks=tasks,
                   coverage_scope="match_ids", requested_match_ids=("1", "2"))
    report = esd.inspect_dataset_coverage(data)
    assert report.complete and report.tables[0].task_status == "partial"


def test_table_filter_does_not_misattribute_other_table_failures_or_reset_overall_complete():
    data = dataset("scores365", tables=("match_events", "player_match_stats"),
                   expected_tasks=("match_events:1", "lineups:1"), successful_tasks=("match_events:1",),
                   coverage_scope="match_ids", requested_match_ids=("1",))
    # Both player tables are required by the loader, but hand-built snapshots may
    # select player metrics alone; coverage remains explicit about their tasks.
    data = replace(data, errors=(esd.DatasetIssue("lineups", "1", "SourceBlocked", "blocked"),))
    report = esd.inspect_dataset_coverage(data, tables=["player_match_stats"])
    assert len(report.tables) == 1 and report.tables[0].task_status == "failed"
    assert report.tables[0].task_keys == ("lineups:1",) and not report.complete
    assert len(report.tasks) == 2 and report.errors == data.errors


def test_espn_season_flags_reconstruct_only_known_tasks_without_inventing_success():
    data = dataset(tables=("matches", "teams", "standings"), calendar_loaded=True,
                   calendar_dates=("2026-11-03", "2026-11-04"), successful_dates=("2026-11-03",), standings_loaded=True,
                   response_fetched_at=(("matches:2026-11-03", NOW.isoformat()),), cached_tasks=("matches:2026-11-03",))
    report = esd.inspect_dataset_coverage(data)
    assert report.tables[0].task_status == report.tables[1].task_status == "partial"
    assert report.tables[2].task_status == "complete"
    task = next(task for task in report.tasks if task.key == "matches:2026-11-03")
    assert task.cached and task.fetched_at == NOW
    assert next(task for task in report.tasks if task.key == "calendar:2026").fetched_at is None
    failed = dataset(tables=("matches", "teams"))
    failed = replace(failed, errors=(esd.DatasetIssue("calendar", "2026", "SourceError", "calendar unavailable"),))
    assert all(row.task_status == "failed" for row in esd.inspect_dataset_coverage(failed).tables)


@pytest.mark.parametrize("source,table,steps", [
    ("understat", "shots", ("season:2026", "shots:1")),
    ("understat", "player_stats", ("player_stats:2026",)),
    ("goaloo", "standings", ("season:2026-2027",)),
    ("fbref", "match_stats", ("matches:2026-11-03",)),
    ("promiedos", "matches", ("matches:2026-11-03",)),
    ("besoccer", "standings", ("standings:2026",)),
    ("transfermarkt", "transfers", ("transfers:101",)),
    ("espn", "match_stats", ("match_stats:1",)),
])
def test_source_specific_tasks_and_prerequisites(source, table, steps):
    data = dataset(source, tables=(table,), expected_tasks=steps, successful_tasks=steps,
                   coverage_scope="match_ids" if source == "espn" else "season",
                   requested_match_ids=("1",) if source == "espn" else ())
    report = esd.inspect_dataset_coverage(data)
    assert report.tables[0].task_keys == steps and report.tables[0].task_status == "complete"


def test_manual_enrichment_does_not_change_the_current_adapter_contract():
    data = dataset(tables=("shots",))
    data = replace(data, shot_records=(esd.NormalizedShot("espn", "s1", "1", xg=0.0),))
    row = field(esd.inspect_dataset_coverage(data), "shots", "xg")
    assert row.capability.support == "unavailable" and row.status == "populated" and row.zero_count == 1
    assert row.unmapped_values


def test_blank_text_and_false_flags_never_become_numeric_zero_or_missing():
    data = replace(dataset(tables=("lineups",)), lineup_records=(
        esd.NormalizedLineup("espn", "1", "10", "101", " ", starter=False, jersey_number="0"),
    ))
    report = esd.inspect_dataset_coverage(data)
    name = field(report, "lineups", "player_name")
    assert name.blank_count == name.present_count == 1 and name.missing_count == 0 and name.zero_count is None
    jersey = field(report, "lineups", "jersey_number")
    assert jersey.blank_count == 0 and jersey.zero_count is None
    flag = field(report, "lineups", "starter")
    assert flag.false_count == 1 and flag.blank_count is None


def test_json_dates_counts_scope_and_parquet_roundtrip_do_not_reset_metadata(tmp_path):
    pytest.importorskip("pyarrow")
    data = dataset("sofascore", tables=("shots",), expected_tasks=("match:1", "shots:1"),
                   successful_tasks=("match:1", "shots:1"), response_fetched_at=(("shots:1", NOW.isoformat()),),
                   cached_tasks=("shots:1",), coverage_scope="match_ids", requested_match_ids=("1",))
    data = replace(data, shot_records=(esd.NormalizedShot("sofascore", "001", "1", xg=0.0, xg_model="sofascore"),))
    report = esd.inspect_dataset_coverage(data)
    document = json.loads(json.dumps(report.to_dict()))
    assert document["format_version"] == 1 and document["metadata"]["schema_version"] == "6"
    assert document["metadata"]["requested_match_ids"] == ["1"]
    assert document["tasks"][1]["fetched_at"] == NOW.isoformat()
    assert esd.inspect_dataset_coverage(esd.open_dataset(data.save(tmp_path / "snapshot"))) == report


def test_pandas_is_only_needed_for_nullable_report_frames():
    data = dataset(tables=("lineups",))
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in ("pandas", "pyarrow"):
            raise ImportError("Optional dependency blocked")
        return original(name, *args, **kwargs)

    with patch("builtins.__import__", guarded), patch("httpx.Client.request", side_effect=AssertionError("HTTP")):
        report = esd.inspect_dataset_coverage(data)
        assert report.to_dict()
    pytest.importorskip("pandas")
    frame = report.to_dataframe()
    assert str(frame.present_count.dtype) == "Int64" and str(frame.present_ratio.dtype) == "Float64"
    assert str(frame.unmapped_values.dtype) == "boolean" and str(frame.support.dtype) == "string"
    assert frame.present_ratio.isna().all()


@pytest.mark.parametrize("tables", [[], "lineups", ["matches"], [None], 1])
def test_invalid_table_selection_is_rejected(tables):
    with pytest.raises(ValueError):
        esd.inspect_dataset_coverage(dataset(), tables=tables)


def test_invalid_records_and_non_dataset_inputs_are_not_silently_counted():
    with pytest.raises(TypeError):
        esd.inspect_dataset_coverage(None)
    data = replace(dataset(), lineup_records=(esd.NormalizedLineup("espn", starter=0),))
    with pytest.raises(ValueError, match="invalid_record"):
        esd.inspect_dataset_coverage(data)


def test_downloaded_three_source_workflow_matches_declared_fields_and_exact_tasks(monkeypatch, tmp_path):
    import runpy
    from copy import deepcopy
    from pathlib import Path

    script = Path(__file__).resolve().parent.parent / "examples/datasets/champions_workflow.py"
    workflow = runpy.run_path(str(script))
    selections, _, responses = workflow["demo_inputs"]()
    monkeypatch.setattr("esd._provider_datasets.get_api_json", lambda url, **_: deepcopy(responses[url]))
    datasets = workflow["download"](selections, tmp_path / "cache", False, request_delay=0)
    for data in datasets:
        report = esd.inspect_dataset_coverage(data)
        assert report.complete and all(row.task_status == "complete" for row in report.tables)
        assert not [row for row in report.fields if row.unmapped_values]
        assert {task.key for task in report.tasks} == set(data.metadata.expected_tasks)
