"""Catalog CLI separates local lookups from explicit season requests."""

import runpy
from pathlib import Path
from unittest.mock import Mock

import pytest

import esd
from esd import discovery

ROOT = Path(__file__).resolve().parent.parent / "examples/datasets"


@pytest.fixture
def example(monkeypatch):
    fetch = Mock(return_value={"competitions": [{"id": 7, "sportId": 1,
                                               "seasons": [{"num": 132, "name": "2026/2027"}]}]})
    monkeypatch.setattr(discovery, "get_api_json", fetch)
    return runpy.run_path(str(ROOT / "catalog.py")), fetch


def test_listing_and_local_lookup_do_not_request_sources(example, capsys):
    module, fetch = example
    assert module["main"]([]) == 0
    assert module["main"](["--competition", "Premier League", "--source", "espn"]) == 0
    assert "Dataset ID: eng.1" in capsys.readouterr().out
    fetch.assert_not_called()


def test_explicit_season_selection_preserves_native_id_and_caller_year(example, capsys):
    module, fetch = example
    assert module["main"](["--competition", "Premier League", "--source", "scores365",
                           "--season-id", "132", "--year", "2026"]) == 0
    assert fetch.call_count == 1
    output = capsys.readouterr().out
    assert "'league': '7'" in output and "'season_id': '132'" in output


@pytest.mark.parametrize("options", [["--seasons"], ["--list", "--seasons"],
                                      ["--competition", "Premier League", "--source", "espn", "--refresh"],
                                      ["--competition", "Premier League", "--source", "espn", "--year", "2026"],
                                      ["--competition", "Premier League", "--source", "goaloo", "--seasons"]])
def test_invalid_or_unreviewed_selection_fails_before_requests(example, options):
    module, fetch = example
    with pytest.raises(SystemExit) as exc:
        module["main"](options)
    assert exc.value.code == 2
    fetch.assert_not_called()


def test_absent_season_is_not_inferred_from_a_year_label(example):
    module, fetch = example
    with pytest.raises(SystemExit) as exc:
        module["main"](["--competition", "Premier League", "--source", "scores365", "--season-id", "2026", "--year", "2026"])
    assert exc.value.code == 2 and fetch.call_count == 1


def test_source_block_stays_a_source_failure(example, capsys):
    module, fetch = example
    fetch.side_effect = esd.SourceBlocked("Source unavailable")
    assert module["main"](["--competition", "Premier League", "--source", "scores365", "--seasons"]) == 1
    assert "SourceBlocked" in capsys.readouterr().err


@pytest.mark.parametrize("code,failures,raises,calls", [(145, 1, False, 2), (145, 3, True, 3), (5, 1, True, 1)])
def test_workflow_cleanup_retries_only_bounded_directory_not_empty_errors(tmp_path, code, failures, raises, calls):
    module = runpy.run_path(str(ROOT / "catalog_workflow_offline.py"))
    namespace = module["workflow_directory"].__wrapped__.__globals__
    error = OSError("Simulated directory cleanup failure")
    error.winerror = code
    temporary = Mock(name=str(tmp_path))
    temporary.name = str(tmp_path)
    temporary.cleanup.side_effect = [*([error] * failures), None]
    namespace["TemporaryDirectory"] = Mock(return_value=temporary)
    pause = Mock()
    namespace["sleep"] = pause

    def run():
        with module["workflow_directory"]() as directory:
            assert directory == tmp_path

    if raises:
        with pytest.raises(OSError) as exc:
            run()
        assert exc.value is error
    else:
        run()
    assert temporary.cleanup.call_count == calls
    assert pause.call_count == calls - 1
