"""Dataset quality checks preserve records and provider-specific selection semantics."""

import subprocess
import sys
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

import pytest

import esd


@pytest.fixture
def dataset():
    now = datetime(2026, 11, 7, tzinfo=timezone.utc)
    return esd.SoccerDataset(
        esd.DatasetMetadata(
            "scores365", "572", 2026, ("matches", "teams"), now, now,
            coverage_scope="date_range", start_date="2026-11-03", end_date="2026-11-04",
            expected_tasks=("matches:2026-11-03",), successful_tasks=("matches:2026-11-03",),
        ),
        match_records=(esd.NormalizedMatch(
            "scores365", match_id="m1", competition_id="572", season="2026",
            kickoff=now.replace(day=3, hour=20), home_team_id="h", away_team_id="a",
            home_score=0, away_score=None, source_status="uninterpreted",
        ),),
        team_records=(esd.NormalizedTeam("scores365", "h"), esd.NormalizedTeam("scores365", "a")),
    )


def codes(report):
    return {issue.code for issue in report.issues}


@pytest.mark.parametrize("source", list(esd.get_dataset_capabilities()))
def test_valid_records_for_all_nine_providers(source, dataset):
    if source == "transfermarkt":
        sample = replace(
            dataset,
            metadata=replace(dataset.metadata, source=source, league="GB1", coverage_scope="entities",
                             start_date=None, end_date=None, tables=("teams", "players", "market_values", "transfers")),
            match_records=(), team_records=(esd.NormalizedTeam(source, "h"),),
            player_records=(esd.NormalizedPlayer(source, "p1", team_id="foreign-current-club"),),
            market_value_records=(esd.NormalizedMarketValue(source, "p1", "historical-club", source_date="native date", value=0),),
            transfer_records=(esd.NormalizedTransfer(source, "t1", "p1", source_season="2010/11",
                                                   source_date="native date", from_team_id="foreign-a", to_team_id="foreign-b"),),
        )
    else:
        dated = source in ("scores365", "fbref", "promiedos", "besoccer")
        sample = replace(
            dataset, metadata=replace(dataset.metadata, source=source, source_timezone="UTC",
                                      coverage_scope="date_range" if dated else "season",
                                      start_date=dataset.metadata.start_date if dated else None,
                                      end_date=dataset.metadata.end_date if dated else None),
            match_records=tuple(replace(row, source=source, source_season_id="native-99") for row in dataset.match_records),
            team_records=tuple(replace(row, source=source) for row in dataset.team_records),
        )
    report = esd.validate_dataset(sample)
    assert report.valid and not report.issues


def test_unknown_score_and_status_are_not_inferred_and_input_is_unchanged(dataset):
    before = repr(dataset)
    report = esd.validate_dataset(dataset)
    assert report.valid and not report.issues
    assert repr(dataset) == before
    assert dataset.match_records[0].away_score is None
    with pytest.raises(FrozenInstanceError):
        report.issues = ()


@pytest.mark.parametrize("change, code", [
    ({"home_score": -1}, "negative_score"),
    ({"away_score": True}, "invalid_record"),
    ({"home_score": "0"}, "invalid_record"),
    ({"kickoff": datetime(2026, 11, 3)}, "invalid_record"),
    ({"kickoff": "2026-11-03"}, "invalid_record"),
    ({"source": "espn"}, "source_mismatch"),
    ({"competition_id": "332"}, "competition_mismatch"),
    ({"season": "2025"}, "season_label_mismatch"),
    ({"home_team_id": "a"}, "same_match_teams"),
    ({"match_id": " "}, "empty_identifier"),
    ({"kickoff": datetime(2026, 11, 5, tzinfo=timezone.utc)}, "kickoff_outside_range"),
])
def test_record_errors_include_location(dataset, change, code):
    invalid = replace(dataset, match_records=(replace(dataset.match_records[0], **change),))
    report = esd.validate_dataset(invalid)
    assert not report.valid and code in codes(report)
    issue = next(issue for issue in report.errors if issue.code == code)
    assert issue.table == "matches" and issue.row_index == 0


def test_duplicate_match_and_team_ids_are_reported(dataset):
    invalid = replace(dataset, match_records=dataset.match_records * 2, team_records=dataset.team_records * 2)
    report = esd.validate_dataset(invalid)
    assert not report.valid
    assert {issue.table for issue in report.errors if issue.code == "duplicate_key"} == {"matches", "teams"}


def test_standings_groups_and_valuation_history_have_scoped_keys(dataset):
    row = esd.NormalizedStanding("scores365", competition_id="572", team_id="h", group_id="A", points=-3)
    sample = replace(dataset, metadata=replace(dataset.metadata, tables=("standings",)),
                     match_records=(), team_records=(), standing_records=(row, replace(row, group_id="B")))
    assert esd.validate_dataset(sample).valid
    duplicated = replace(sample, standing_records=(row, row))
    assert "duplicate_key" in codes(esd.validate_dataset(duplicated))
    value = esd.NormalizedMarketValue("transfermarkt", "p1", source_date="native-first", value=10)
    history = replace(sample, metadata=replace(sample.metadata, source="transfermarkt", tables=("market_values",),
                                              coverage_scope="entities", start_date=None, end_date=None),
                      standing_records=(), market_value_records=(value, replace(value, source_date="native-second")))
    assert esd.validate_dataset(history).valid
    assert "duplicate_key" in codes(esd.validate_dataset(replace(history, market_value_records=(value, value))))


def test_only_selected_tables_are_used_for_references(dataset):
    sample = replace(dataset, team_records=())
    report = esd.validate_dataset(sample)
    assert report.valid
    assert len([issue for issue in report.warnings if issue.code == "unresolved_reference"]) == 2
    no_team_selection = replace(sample, metadata=replace(sample.metadata, tables=("matches",)))
    assert not esd.validate_dataset(no_team_selection).warnings
    with_stats = replace(dataset, metadata=replace(dataset.metadata, tables=("matches", "teams", "match_stats", "shots")),
                         match_stat_records=(esd.NormalizedMatchStats("scores365", "other"),),
                         shot_records=(esd.NormalizedShot("scores365", "shot1", match_id="other"),))
    report = esd.validate_dataset(with_stats)
    assert report.valid
    assert {issue.table for issue in report.warnings} == {"match_stats", "shots"}


def test_missing_ids_and_kickoff_are_warnings(dataset):
    sample = replace(dataset, match_records=(replace(dataset.match_records[0], match_id=None, kickoff=None),))
    report = esd.validate_dataset(sample)
    assert report.valid and codes(report) == {"missing_identifier", "missing_kickoff"}


def test_partial_data_warns_but_contradictory_success_is_an_error(dataset):
    issue = esd.DatasetIssue("matches", "2026-11-03", "SourceError", "Sample source failure")
    partial = replace(dataset, metadata=replace(dataset.metadata, successful_tasks=()), errors=(issue,))
    report = esd.validate_dataset(partial)
    assert report.valid and codes(report) == {"source_failure", "incomplete_coverage"}
    contradictory = replace(dataset, errors=(issue,))
    assert "task_success_with_error" in codes(esd.validate_dataset(contradictory))


@pytest.mark.parametrize("step", ["calendar", "matches", "standings"])
def test_legacy_calendar_coverage_cannot_report_success_and_failure(dataset, step):
    target = "2026-11-03" if step == "matches" else "2026"
    sample = replace(
        dataset,
        metadata=replace(dataset.metadata, expected_tasks=(), successful_tasks=(),
                         calendar_loaded=True, calendar_dates=("2026-11-03",),
                         successful_dates=("2026-11-03",), standings_loaded=True),
        errors=(esd.DatasetIssue(step, target, "SourceError", "Sample failure"),),
    )
    assert "task_success_with_error" in codes(esd.validate_dataset(sample))


@pytest.mark.parametrize("change", [
    {"successful_tasks": ("outside",)}, {"expected_tasks": ("same", "same")},
    {"schema_version": "unsupported"}, {"finished_at": datetime(2026, 11, 6, tzinfo=timezone.utc)},
    {"calendar_dates": ("2026-11-03",)}, {"tables": ("unknown",)},
    {"cached_tasks": ("matches:2026-11-03",)},
])
def test_invalid_metadata_is_reported_without_raising(dataset, change):
    report = esd.validate_dataset(replace(dataset, metadata=replace(dataset.metadata, **change)))
    assert not report.valid and "invalid_metadata" in codes(report)


@pytest.mark.parametrize("change, expected", [
    ({"start_date": None}, "invalid_date_bounds"),
    ({"end_date": "2026-11-02"}, "invalid_date_bounds"),
    ({"start_date": "2026-1-03"}, "invalid_date_bounds"),
    ({"start_date": None, "end_date": None}, "missing_date_bounds"),
])
def test_invalid_date_bounds_are_reported(dataset, change, expected):
    report = esd.validate_dataset(replace(dataset, metadata=replace(dataset.metadata, **change)))
    assert not report.valid and expected in codes(report)


def test_source_local_range_uses_configured_timezone(dataset, monkeypatch):
    from esd import dataset_validation

    monkeypatch.setattr(dataset_validation, "ZoneInfo", lambda name: timezone(timedelta(hours=-3)))
    sample = replace(dataset, metadata=replace(dataset.metadata, source="promiedos", source_timezone="America/Argentina/Buenos_Aires",
                                              start_date="2026-11-03", end_date="2026-11-03"),
                     match_records=(replace(dataset.match_records[0], source="promiedos", kickoff=datetime(2026, 11, 4, 1, tzinfo=timezone.utc)),),
                     team_records=tuple(replace(row, source="promiedos") for row in dataset.team_records))
    assert not esd.validate_dataset(sample).issues
    late = replace(sample, match_records=(replace(sample.match_records[0], kickoff=datetime(2026, 11, 4, 4, tzinfo=timezone.utc)),))
    assert "kickoff_outside_range" in codes(esd.validate_dataset(late))
    unknown = replace(sample, metadata=replace(sample.metadata, source_timezone=None))
    report = esd.validate_dataset(unknown)
    assert report.valid and codes(report) == {"unknown_date_timezone"}


def test_unavailable_timezone_warns_instead_of_importing_optional_data(dataset, monkeypatch):
    from esd import dataset_validation

    def unavailable(name):
        raise dataset_validation.ZoneInfoNotFoundError(name)

    monkeypatch.setattr(dataset_validation, "ZoneInfo", unavailable)
    sample = replace(dataset, metadata=replace(dataset.metadata, source="promiedos", source_timezone="Unavailable/Zone"),
                     match_records=tuple(replace(row, source="promiedos") for row in dataset.match_records),
                     team_records=tuple(replace(row, source="promiedos") for row in dataset.team_records))
    report = esd.validate_dataset(sample)
    assert report.valid and codes(report) == {"unavailable_date_timezone"}


def test_aware_non_utc_offset_warns_without_changing_the_instant(dataset):
    kickoff = dataset.match_records[0].kickoff.astimezone(timezone(timedelta(hours=-3)))
    sample = replace(dataset, match_records=(replace(dataset.match_records[0], kickoff=kickoff),))
    report = esd.validate_dataset(sample)
    assert report.valid and codes(report) == {"non_utc_kickoff"}
    assert sample.match_records[0].kickoff.utcoffset() == timedelta(hours=-3)


def test_old_cached_timestamps_are_valid_but_failed_cached_tasks_are_not(dataset):
    key = "matches:2026-11-03"
    meta = replace(dataset.metadata, cached_tasks=(key,), response_fetched_at=((key, "2020-01-01T00:00:00+00:00"),))
    assert not esd.validate_dataset(replace(dataset, metadata=meta)).issues
    failed = replace(dataset, metadata=replace(meta, successful_tasks=()))
    assert "cached_task_not_successful" in codes(esd.validate_dataset(failed))


@pytest.mark.parametrize("change, expected", [
    ({"metadata": None}, "invalid_metadata"), ({"match_records": None}, "invalid_table"),
    ({"match_records": ({"match_id": "m1"},)}, "invalid_record"),
    ({"errors": None}, "invalid_download_issues"), ({"errors": ("bad",)}, "invalid_download_issue"),
    ({"player_records": (esd.NormalizedPlayer("scores365", "p1"),)}, "unselected_table"),
])
def test_malformed_containers_return_diagnostics(dataset, change, expected):
    report = esd.validate_dataset(replace(dataset, **change))
    assert not report.valid and expected in codes(report)
    narrowed = replace(dataset, metadata=replace(dataset.metadata, snapshot_match_ids=("other",)))
    assert "unrequested_match" in codes(esd.validate_dataset(narrowed))


def test_wrong_input_type_raises_type_error():
    with pytest.raises(TypeError, match="SoccerDataset"):
        esd.validate_dataset([])


def test_validation_has_no_optional_imports_network_or_writes():
    code = '''
import importlib.abc
import sys
class NoExtras(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('pandas', 'pyarrow'):
            raise ModuleNotFoundError('Optional dependency blocked', name=fullname)
sys.meta_path.insert(0, NoExtras())
import esd
from datetime import datetime, timezone
from unittest.mock import patch
now = datetime(2026, 11, 7, tzinfo=timezone.utc)
dataset = esd.SoccerDataset(esd.DatasetMetadata('espn', 'eng.1', 2026, ('teams',), now, now))
def forbidden(*args, **kwargs):
    raise AssertionError('Unexpected I/O')
with patch('httpx.Client.request', forbidden), patch('curl_cffi.requests.Session.request', forbidden), patch('pathlib.Path.write_text', forbidden):
    assert esd.validate_dataset(dataset).valid
assert 'pandas' not in sys.modules and 'pyarrow' not in sys.modules
'''
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
