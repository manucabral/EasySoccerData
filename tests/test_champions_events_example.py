"""Three-provider Champions queries use explicit selectors and bounded reads."""

import runpy
from pathlib import Path
from unittest.mock import Mock

import pytest

import esd
from esd import _provider_datasets

ROOT = Path(__file__).resolve().parent.parent / "examples/datasets"
OPTIONS = ["--espn-match-id", "1", "--scores365-match-id", "1", "--sofascore-match-id", "1",
           "--espn-season", "2026", "--year", "2026", "--scores365-season-id", "228", "--sofascore-season-id", "228"]


@pytest.fixture
def example(monkeypatch):
    payload = runpy.run_path(str(ROOT / "match_events_offline.py"))["payload"]

    def fake_fetch(url, **options):
        if "espn.com/" in url:
            data = payload("espn")
            data["header"]["league"]["slug"] = "uefa.champions"
            data["boxscore"] = {"teams": []}
            return data
        if "365scores.com/" in url:
            data = payload("scores365")
            data["game"]["competitionId"] = 572
            if "/stats/" in url:
                return {"games": [data["game"]], "statistics": []}
            return data
        if url.endswith("/incidents"):
            return payload("sofascore")
        if url.endswith("/lineups"):
            return {"home": {"players": []}, "away": {"players": []}}
        if url.endswith("/statistics"):
            return {"statistics": []}
        return {"event": {"id": 1, "season": {"id": 228}, "tournament": {"uniqueTournament": {"id": 7}},
                          "startTimestamp": 1793736000, "homeTeam": {"id": 10}, "awayTeam": {"id": 20}}}

    fetch = Mock(side_effect=fake_fetch)
    monkeypatch.setattr(_provider_datasets, "get_api_json", fetch)
    return runpy.run_path(str(ROOT / "champions_events.py")), fetch


@pytest.mark.parametrize("flags,reads", [([], 4), (["--with-players"], 5), (["--with-match-stats"], 6),
                                      (["--with-players", "--with-match-stats"], 7)])
def test_champions_native_selectors_and_shared_context_have_exact_total_cost(example, flags, reads, capsys):
    module, fetch = example
    assert module["main"](OPTIONS + flags + ["--max-match-requests", str(reads)]) == 0
    assert fetch.call_count == reads
    text = capsys.readouterr().out
    assert all(f"{source} | Complete: True" in text for source in ("espn", "scores365", "sofascore"))


@pytest.mark.parametrize("flags", [["--with-players"], ["--max-match-requests", "3"], ["--year", "99"],
                                  ["--sofascore-match-id", "0"], ["--limit", "0"]])
def test_bad_budgets_or_native_selectors_fail_before_any_source(example, flags):
    module, fetch = example
    with pytest.raises(SystemExit) as exc:
        module["main"](OPTIONS + flags)
    assert exc.value.code == 2
    fetch.assert_not_called()


def test_champions_cache_reuse_retains_both_sofascore_reads(example, tmp_path, capsys):
    module, fetch = example
    assert module["main"](OPTIONS + ["--cache-dir", str(tmp_path)]) == 0
    assert module["main"](OPTIONS + ["--cache-dir", str(tmp_path)]) == 0
    assert fetch.call_count == 4
    assert "Cached tasks: ('match:1', 'match_events:1')" in capsys.readouterr().out


def test_blocked_sofascore_stays_partial_and_is_saved_with_its_errors(example, tmp_path):
    pytest.importorskip("pyarrow")
    module, fetch = example
    fake = fetch.side_effect
    fetch.side_effect = lambda url, **options: (_ for _ in ()).throw(esd.SourceBlocked("Blocked")) if "sofascore.com/" in url else fake(url, **options)
    target = tmp_path / "champions"
    assert module["main"](OPTIONS + ["--output-dir", str(target)]) == 1
    sofa = esd.open_dataset(target / "sofascore")
    assert not sofa.complete and len(sofa.errors) == 2 and not sofa.match_event_records
    assert esd.open_dataset(target / "espn").complete and esd.open_dataset(target / "scores365").complete


@pytest.mark.parametrize("extra,flags", [("pyarrow", ["--output-dir", "champions-events"]), ("pandas", ["--pandas"])])
def test_missing_extra_is_checked_before_requests(example, extra, flags):
    module, fetch = example
    module["main"].__globals__["find_spec"] = lambda name: None if name == extra else object()
    with pytest.raises(SystemExit) as exc:
        module["main"](OPTIONS + flags)
    assert exc.value.code == 2
    fetch.assert_not_called()


def test_existing_destination_fails_before_requests(example, tmp_path):
    module, fetch = example
    with pytest.raises(SystemExit) as exc:
        module["main"](OPTIONS + ["--output-dir", str(tmp_path)])
    assert exc.value.code == 2
    fetch.assert_not_called()
