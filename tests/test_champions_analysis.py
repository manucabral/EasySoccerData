"""Offline Champions League analysis preserves unknown scores and source identity."""

import builtins
import runpy
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

import esd

EXAMPLE = Path(__file__).resolve().parent.parent / "examples/pandas/champions_analysis.py"


@pytest.fixture
def example():
    return runpy.run_path(str(EXAMPLE))


@pytest.fixture
def dataset():
    now = datetime(2026, 11, 7, tzinfo=timezone.utc)
    kickoff = datetime(2026, 11, 3, 20, tzinfo=timezone.utc)

    def match(identifier, home="a", away="b", goals=(2, 0), status="4", time=kickoff):
        return esd.NormalizedMatch(
            "scores365", match_id=identifier, competition_id="572", kickoff=time,
            home_team_id=home, away_team_id=away,
            home_team_name="Same", away_team_name="Same",
            home_score=goals[0], away_score=goals[1], source_status=status,
            source_status_text="Sample status text",
        )

    return esd.SoccerDataset(
        esd.DatasetMetadata(
            "scores365", "572", 2026, ("matches", "teams"), now, now,
            start_date="2026-11-03", end_date="2026-11-04", coverage_scope="date_range",
            expected_tasks=("matches:2026-11-03", "matches:2026-11-04"),
            successful_tasks=("matches:2026-11-03", "matches:2026-11-04"),
        ),
        match_records=(
            match("late", away="c", goals=(0, 0), time=kickoff.replace(day=4)),
            match("first"),
            match("second", home="b", away="a", goals=(1, 3)),
            match("live", goals=(8, 0), status="2"),
            match("unknown-status", status=None),
            match("scheduled", goals=(None, None), status="1"),
            match("unknown-score", goals=(0, None)),
            match("missing-id", home=None),
            match("same-id", away="a"),
            match("negative-score", goals=(-1, 0)),
            match("missing-kickoff", home="b", away="c", goals=(1, 1), time=None),
        ),
    )


def test_import_and_help_do_not_load_optional_packages_or_snapshot(monkeypatch):
    original_import = builtins.__import__

    def without_extras(name, *args, **kwargs):
        if name.split(".")[0] in ("pandas", "pyarrow"):
            raise AssertionError("Import and help must work without optional packages")
        return original_import(name, *args, **kwargs)

    read = Mock(side_effect=AssertionError("Unexpected snapshot read"))
    monkeypatch.setattr(builtins, "__import__", without_extras)
    monkeypatch.setattr(esd, "open_dataset", read)
    module = runpy.run_path(str(EXAMPLE))
    with pytest.raises(SystemExit) as exc:
        module["main"](["--help"])
    assert exc.value.code == 0
    read.assert_not_called()


def test_summary_counts_results_by_id_and_excludes_ineligible_matches(example, dataset):
    pd = pytest.importorskip("pandas")
    fixtures, summary, excluded = example["analyze"](dataset)
    assert len(fixtures) == 11
    assert fixtures.iloc[-1].match_id == "missing-kickoff"
    assert fixtures.iloc[-2].match_id == "late"
    assert str(fixtures.kickoff.dtype) == "datetime64[ns, UTC]"
    unknown = fixtures.set_index("match_id").loc["unknown-score"]
    assert unknown.home_score == 0
    assert pd.isna(unknown.away_score)
    assert excluded == {
        "not_finished": 3, "missing_or_invalid_scores": 2, "missing_or_invalid_team_ids": 2,
    }
    rows = summary.set_index("team_id")
    columns = ["played", "wins", "draws", "losses", "goals_for", "goals_against", "goal_difference"]
    assert rows.loc["a", columns].tolist() == [3, 2, 1, 0, 5, 1, 4]
    assert rows.loc["b", columns].tolist() == [3, 0, 1, 2, 2, 6, -4]
    assert rows.loc["c", columns].tolist() == [2, 0, 2, 0, 1, 1, 0]
    assert (summary.source == "scores365").all()
    assert (summary.team_name == "Same").all()
    assert int(summary.played.sum()) == 8
    assert len(dataset.match_records) == 11
    assert dataset.match_records[6].away_score is None


@pytest.mark.parametrize("records", ["empty", "unfinished", "unknown-score"])
def test_no_eligible_games_has_empty_summary(example, dataset, records):
    pytest.importorskip("pandas")
    selected = {
        "empty": (), "unfinished": (dataset.match_records[3],),
        "unknown-score": (dataset.match_records[6],),
    }[records]
    fixtures, summary, excluded = example["analyze"](replace(dataset, match_records=selected))
    assert len(fixtures) == len(selected)
    assert summary.empty
    assert summary.columns.tolist() == example["SUMMARY_COLUMNS"]
    assert sum(excluded.values()) == len(selected)


@pytest.mark.parametrize("change", [
    {"source": "espn"}, {"league": "332"}, {"tables": ("teams",)},
])
def test_other_provider_competition_or_table_is_rejected(example, dataset, change):
    pytest.importorskip("pandas")
    invalid = replace(dataset, metadata=replace(dataset.metadata, **change))
    with pytest.raises(ValueError, match="Champions League matches snapshot"):
        example["analyze"](invalid)


@pytest.mark.parametrize("partial", [False, True])
def test_cli_reads_snapshot_without_network_and_reports_coverage(
    example, dataset, monkeypatch, tmp_path, capsys, partial,
):
    pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    if partial:
        dataset = replace(
            dataset,
            metadata=replace(dataset.metadata, successful_tasks=("matches:2026-11-03",)),
            errors=(esd.DatasetIssue("matches", "2026-11-04", "SourceError", "Sample failed day"),),
        )
    destination = dataset.save(tmp_path / "saved matches")
    no_network = Mock(side_effect=AssertionError("Snapshot analysis attempted network access"))
    monkeypatch.setattr("httpx.Client.request", no_network)
    monkeypatch.setattr("curl_cffi.requests.Session.request", no_network)
    monkeypatch.setattr("esd.utils.BrowserSession._launch", no_network)
    monkeypatch.setattr(esd, "load_dataset", no_network)
    assert example["main"]([str(destination)]) == int(partial)
    captured = capsys.readouterr()
    assert "2026-11-03 to 2026-11-04 (UTC)" in captured.out
    assert "Saved matches: 11" in captured.out
    assert "Matches included in summary: 4" in captured.out
    assert "not the official standings" in captured.out
    assert "<NA>" in captured.out
    if partial:
        assert "Complete: False" in captured.out
        assert "matches 2026-11-04: SourceError: Sample failed day" in captured.err
    else:
        assert "Complete: True" in captured.out
        assert not captured.err
    no_network.assert_not_called()


def test_cli_missing_snapshot_reports_error(example, monkeypatch, tmp_path, capsys):
    no_network = Mock(side_effect=AssertionError("Unexpected network access"))
    monkeypatch.setattr(esd, "load_dataset", no_network)
    with pytest.raises(SystemExit) as exc:
        example["main"]([str(tmp_path / "missing")])
    assert exc.value.code == 2
    assert "Dataset directory not found" in capsys.readouterr().err
    no_network.assert_not_called()


@pytest.mark.parametrize("records", [(), (3,), (6,)])
def test_cli_without_eligible_matches_reports_empty_summary(
    example, dataset, monkeypatch, capsys, records,
):
    pytest.importorskip("pandas")
    selected = tuple(dataset.match_records[index] for index in records)
    monkeypatch.setattr(esd, "open_dataset", Mock(return_value=replace(dataset, match_records=selected)))
    assert example["main"](["snapshot"]) == 0
    captured = capsys.readouterr()
    assert "No finished matches with known scores and team IDs" in captured.out
    assert "Matches included in summary: 0" in captured.out
    assert not captured.err


@pytest.mark.parametrize("package", ["pandas", "pyarrow"])
def test_cli_missing_extra_reports_install_command(example, dataset, monkeypatch, capsys, package):
    if package == "pandas":
        monkeypatch.setattr(esd, "open_dataset", Mock(return_value=dataset))
    original_import = builtins.__import__

    def without_extra(name, *args, **kwargs):
        if name.split(".")[0] == package:
            raise ModuleNotFoundError("Optional package missing", name=package)
        return original_import(name, *args, **kwargs)

    if package == "pyarrow":
        monkeypatch.setattr(esd, "open_dataset", Mock(side_effect=ImportError("PyArrow missing")))
    monkeypatch.setattr(builtins, "__import__", without_extra)
    with pytest.raises(SystemExit) as exc:
        example["main"](["snapshot"])
    assert exc.value.code == 2
    assert 'python -m pip install -e ".[pandas,parquet]"' in capsys.readouterr().err
