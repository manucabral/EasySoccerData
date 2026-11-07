"""Champions League comparison uses explicit identities and preserves source evidence."""

import builtins
import json
import runpy
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

import esd
from esd.cache import ResponseInfo
from esd.espn.types import ESPNMatch, ESPNTeam

EXAMPLE = Path(__file__).resolve().parent.parent / "examples/datasets/champions_compare.py"


@pytest.fixture
def example():
    return runpy.run_path(str(EXAMPLE))


@pytest.fixture
def pair():
    now = datetime(2026, 11, 7, tzinfo=timezone.utc)
    kickoff = now.replace(day=3, hour=20)
    result = []
    for source, league, match_id, home, away in (
        ("scores365", "572", "s1", "1955", "890"),
        ("espn", "uefa.champions", "e1", "493", "2250"),
    ):
        result.append(esd.SoccerDataset(
            esd.DatasetMetadata(
                source, league, 2026, ("matches", "teams"), now, now,
                coverage_scope="date_range", start_date="2026-11-03", end_date="2026-11-04",
                expected_tasks=("matches:2026-11-03",), successful_tasks=("matches:2026-11-03",),
                response_fetched_at=(("matches:2026-11-03", now.isoformat()),),
            ),
            match_records=(esd.NormalizedMatch(
                source, match_id=match_id, competition_id=league, kickoff=kickoff,
                home_team_id=home, away_team_id=away, home_team_name="Same", away_team_name="Same",
                home_score=0, away_score=1, source_status="4" if source == "scores365" else "STATUS_FINAL",
            ),),
        ))
    return tuple(result)


def identities(example):
    return example["read_identities"](example["DEFAULT_IDENTITIES"])[1]


def test_import_and_help_work_without_optional_packages_or_network(monkeypatch):
    original = builtins.__import__

    def without_extras(name, *args, **kwargs):
        if name.split(".")[0] in ("pandas", "pyarrow"):
            raise AssertionError("Unexpected optional import")
        return original(name, *args, **kwargs)

    fetch = Mock(side_effect=AssertionError("Unexpected download"))
    monkeypatch.setattr(builtins, "__import__", without_extras)
    monkeypatch.setattr(esd, "load_dataset", fetch)
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(EXAMPLE))["main"](["--help"])
    assert exc.value.code == 0
    fetch.assert_not_called()


@pytest.mark.parametrize("away_score, expected", [(1, "equal"), (2, "different"), (None, "unknown")])
def test_report_links_ids_and_preserves_scores_times_and_statuses(example, pair, away_score, expected):
    left, right = pair
    row = replace(right.match_records[0], away_score=away_score,
                  kickoff=right.match_records[0].kickoff + timedelta(seconds=120))
    right = replace(right, match_records=(row,))
    report = example["compare"](left, right, identities(example))
    link = report["links"][0]
    assert link["score_comparison"] == expected
    assert link["kickoff_difference_seconds"] == 120
    assert link["scores365"]["home_score"] == 0
    assert link["espn"]["away_score"] == away_score
    assert link["scores365"]["source_status"] == "4"
    assert link["espn"]["source_status"] == "STATUS_FINAL"
    assert report["sources"]["espn"]["response_fetched_at"] == dict(right.metadata.response_fetched_at)
    assert pair[1].match_records[0].away_score == 1


@pytest.mark.parametrize("kind", ["unmapped", "ambiguous", "rescheduled", "missing_kickoff"])
def test_unresolved_matches_are_not_forced_into_links(example, pair, kind):
    left, right = pair
    mapping = identities(example)
    row = right.match_records[0]
    if kind == "unmapped":
        mapping = esd.IdentityMap()
    elif kind == "ambiguous":
        right = replace(right, match_records=(row, replace(row, match_id="e2")))
    elif kind == "rescheduled":
        right = replace(right, match_records=(replace(row, kickoff=row.kickoff + timedelta(hours=1)),))
    else:
        right = replace(right, match_records=(replace(row, kickoff=None),))
    report = example["compare"](left, right, mapping)
    assert not report["links"]
    if kind == "ambiguous":
        assert report["ambiguous"] == {"scores365": ("s1",), "espn": ("e1", "e2")}
    else:
        assert report["unmatched"] == {"scores365": ("s1",), "espn": ("e1",)}


@pytest.mark.parametrize("kind", ["source", "range", "outside", "scope"])
def test_incompatible_snapshot_selection_is_rejected(example, pair, kind):
    left, right = pair
    if kind == "source":
        right = replace(right, metadata=replace(right.metadata, league="eng.1"))
    elif kind == "range":
        right = replace(right, metadata=replace(right.metadata, end_date="2026-11-05"))
    elif kind == "scope":
        right = replace(right, metadata=replace(right.metadata, coverage_scope="season"))
    else:
        right = replace(right, match_records=(replace(right.match_records[0], kickoff=datetime(2026, 11, 5, tzinfo=timezone.utc)),))
    with pytest.raises(ValueError):
        example["compare"](left, right, identities(example))


@pytest.mark.parametrize("both_empty", [False, True])
def test_empty_source_is_complete_but_does_not_invent_links(example, pair, both_empty):
    left, right = pair
    right = replace(right, match_records=())
    if both_empty:
        left = replace(left, match_records=())
    report = example["compare"](left, right, identities(example))
    assert all(source["complete"] for source in report["sources"].values())
    assert not report["links"]
    assert report["unmatched"]["scores365"] == (() if both_empty else ("s1",))
    assert report["unmatched"]["espn"] == ()


def test_espn_download_filters_boundary_days_and_keeps_newer_observation(example, monkeypatch):
    client = Mock()
    event = ESPNMatch(id="e1", date="2026-11-03T23:30-01:00",
                      home_team=ESPNTeam(id="493", name="Home", score=2),
                      away_team=ESPNTeam(id="2250", name="Away", score=0))
    outside = replace(event, id="outside", date="2026-11-05T00:00Z")
    calls = []

    def scoreboard(league, day, expected_season):
        calls.append((league, day, expected_season))
        client.last_response = ResponseInfo(len(calls) == 3, 2000 if len(calls) == 2 else 1000)
        if len(calls) == 4:
            raise esd.SourceBlocked("Sample failed boundary day")
        return [event, outside] if len(calls) == 2 else [replace(event, home_team=ESPNTeam(id="493", score=0))]

    client.get_scoreboard.side_effect = scoreboard
    monkeypatch.setattr(esd, "ESPNClient", Mock(return_value=client))
    result = example["download_espn"](date(2026, 11, 3), date(2026, 11, 4), 2026)
    assert [call[1] for call in calls] == ["2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05"]
    assert all(call[0] == "uefa.champions" and call[2] == 2026 for call in calls)
    assert len(result.match_records) == 1
    assert result.match_records[0].kickoff.isoformat() == "2026-11-04T00:30:00+00:00"
    assert result.match_records[0].home_score == 2
    assert result.team_records[0].name == "Home"
    assert not result.complete
    assert result.errors[0].target == "2026-11-05"
    assert result.metadata.cached_tasks == ("matches:2026-11-04",)


@pytest.mark.parametrize("partial", [False, True])
def test_saved_pair_repeats_offline_without_pandas_and_preserves_tolerance(
    example, pair, monkeypatch, tmp_path, capsys, partial,
):
    pytest.importorskip("pyarrow")
    left, right = pair
    if partial:
        right = replace(right, errors=(esd.DatasetIssue("matches", "2026-11-04", "SourceError", "Sample failure"),))
    aliases, mapping = example["read_identities"](example["DEFAULT_IDENTITIES"])
    report = example["compare"](left, right, mapping, 120)
    root = example["save_pair"](tmp_path / "chosen pair", left, right, aliases, report)
    assert esd.open_dataset(root / "scores365") == left
    assert esd.open_dataset(root / "espn") == right
    original = builtins.__import__

    def without_pandas(name, *args, **kwargs):
        if name.split(".")[0] == "pandas":
            raise ModuleNotFoundError("pandas blocked", name="pandas")
        return original(name, *args, **kwargs)

    no_network = Mock(side_effect=AssertionError("Unexpected network access"))
    monkeypatch.setattr(builtins, "__import__", without_pandas)
    monkeypatch.setattr(esd, "load_dataset", no_network)
    monkeypatch.setattr("httpx.Client.request", no_network)
    monkeypatch.setattr("curl_cffi.requests.Session.request", no_network)
    monkeypatch.setattr("esd.utils.BrowserSession._launch", no_network)
    original_compare = example["main"].__globals__["compare"]
    checked_compare = Mock(wraps=original_compare)
    monkeypatch.setitem(example["main"].__globals__, "compare", checked_compare)
    assert example["main"](["--open-dir", str(root)]) == int(partial)
    assert checked_compare.call_args.args[3] == 120
    output = capsys.readouterr()
    assert "Linked matches: 1" in output.out
    assert "Original fetch:" in output.out
    assert ("Sample failure" in output.err) == partial
    no_network.assert_not_called()


def test_failed_second_snapshot_leaves_no_pair_or_staging(example, pair, monkeypatch, tmp_path):
    pytest.importorskip("pyarrow")
    original_save = esd.SoccerDataset.save

    def save(dataset, path):
        if dataset.metadata.source == "espn":
            raise OSError("disk full")
        return original_save(dataset, path)

    monkeypatch.setattr(esd.SoccerDataset, "save", save)
    with pytest.raises(OSError, match="disk full"):
        example["save_pair"](tmp_path / "pair", *pair, [], {})
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("arguments", [
    ["--start-date", "bad"], ["--end-date", "2026-11-02"], ["--end-date", "2026-11-10"],
    ["--season", "0"], ["--tolerance-seconds", "nan"], ["--tolerance-seconds", "-1"],
    ["--open-dir", "pair", "--refresh"], ["--open-dir", "pair", "--start-date", "2026-11-03"],
])
def test_invalid_arguments_never_download(example, monkeypatch, arguments):
    fetch = Mock(side_effect=AssertionError("Unexpected download"))
    monkeypatch.setattr(esd, "load_dataset", fetch)
    monkeypatch.setattr(esd, "ESPNClient", fetch)
    with pytest.raises(SystemExit) as exc:
        example["main"](arguments)
    assert exc.value.code == 2
    fetch.assert_not_called()


def test_existing_output_is_untouched_before_download(example, monkeypatch, tmp_path):
    root = tmp_path / "pair"
    root.mkdir()
    marker = root / "keep"
    marker.write_text("original", encoding="utf-8")
    fetch = Mock(side_effect=AssertionError("Unexpected download"))
    monkeypatch.setattr(esd, "load_dataset", fetch)
    with pytest.raises(SystemExit) as exc:
        example["main"](["--output-dir", str(root)])
    assert exc.value.code == 2
    assert marker.read_text(encoding="utf-8") == "original"
    fetch.assert_not_called()


@pytest.mark.parametrize("failed_day", [False, True])
def test_live_mode_reuses_cache_recovers_failures_and_refreshes(
    example, monkeypatch, tmp_path, capsys, failed_day,
):
    calls, reports = [], []
    blocked = [failed_day]

    def scores(url, **kwargs):
        calls.append(url)
        games = [] if "04/11/2026" in url else [{
            "id": 1, "competitionId": 572, "startTime": "2026-11-03T20:00:00Z", "statusGroup": 4,
            "homeCompetitor": {"id": 1955, "name": "Home", "score": 0},
            "awayCompetitor": {"id": 890, "name": "Away", "score": 1},
        }]
        return {"games": games}

    def espn(url, **kwargs):
        calls.append(url)
        if blocked[0] and "20261104" in url:
            raise esd.SourceError("Sample failed day")
        return {
            "leagues": [{"slug": "uefa.champions", "season": {"year": 2026}}],
            "events": [{
                "id": "e1", "date": "2026-11-03T20:00Z",
                "status": {"type": {"completed": True, "name": "STATUS_FINAL"}},
                "competitions": [{"competitors": [
                    {"homeAway": "home", "score": "0", "team": {"id": "493", "name": "Home"}},
                    {"homeAway": "away", "score": "1", "team": {"id": "2250", "name": "Away"}},
                ]}],
            }],
        }

    original_compare = example["compare"]

    def compare(*args):
        result = original_compare(*args)
        reports.append(result)
        return result

    monkeypatch.setattr("esd._provider_datasets.get_api_json", scores)
    monkeypatch.setattr("esd.espn.service.get_api_json", espn)
    monkeypatch.setattr("esd._response_reader.time.sleep", lambda delay: None)
    monkeypatch.setitem(example["main"].__globals__, "compare", compare)
    arguments = ["--cache-dir", str(tmp_path / "responses")]
    assert example["main"](arguments) == int(failed_day)
    assert len(calls) == 6
    first_times = reports[0]["sources"]["scores365"]["response_fetched_at"]
    blocked[0] = False
    assert example["main"](arguments) == 0
    assert len(calls) == 6 + int(failed_day)
    assert reports[-1]["sources"]["scores365"]["response_fetched_at"] == first_times
    assert len(reports[-1]["links"]) == 1
    assert len(reports[-1]["sources"]["scores365"]["cached_tasks"]) == 2
    assert example["main"]([*arguments, "--refresh"]) == 0
    assert len(calls) == 12 + int(failed_day)
    assert not reports[-1]["sources"]["scores365"]["cached_tasks"]
    assert not reports[-1]["sources"]["espn"]["cached_tasks"]
    capsys.readouterr()


@pytest.mark.parametrize("entries", [{}, [1], [{"kind": "team"}]])
def test_invalid_identity_files_fail_before_download(example, monkeypatch, tmp_path, entries):
    path = tmp_path / "aliases.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    fetch = Mock(side_effect=AssertionError("Unexpected download"))
    monkeypatch.setattr(esd, "load_dataset", fetch)
    with pytest.raises(SystemExit) as exc:
        example["main"](["--identities", str(path)])
    assert exc.value.code == 2
    fetch.assert_not_called()


@pytest.mark.parametrize("flag", ["--open-dir", "--output-dir"])
def test_storage_without_pyarrow_never_downloads(example, monkeypatch, tmp_path, capsys, flag):
    monkeypatch.setitem(example["main"].__globals__, "find_spec", lambda name: None)
    fetch = Mock(side_effect=AssertionError("Unexpected download"))
    monkeypatch.setattr(esd, "load_dataset", fetch)
    with pytest.raises(SystemExit) as exc:
        example["main"]([flag, str(tmp_path / "pair")])
    assert exc.value.code == 2
    assert 'python -m pip install -e ".[parquet]"' in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []
    fetch.assert_not_called()
