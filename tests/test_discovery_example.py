"""Discovery CLI help and support checks are offline; source failures remain explicit."""

import runpy
from pathlib import Path
from unittest.mock import Mock

import pytest

import esd
from esd import discovery

EXAMPLE = Path(__file__).resolve().parent.parent / "examples/datasets/discover.py"


def test_import_help_and_support_listing_do_not_fetch(monkeypatch, capsys):
    fetch = Mock(side_effect=AssertionError("Unexpected source request"))
    monkeypatch.setattr(discovery, "get_api_json", fetch)
    main = runpy.run_path(str(EXAMPLE))["main"]
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    capsys.readouterr()
    assert main(["--list"]) == 0
    output = capsys.readouterr().out
    assert len(output.splitlines()) == 9 and "manual" in output
    fetch.assert_not_called()


@pytest.mark.parametrize("arguments", [
    ["--seasons"], ["--competition-id", "572"],
    ["--seasons", "--competition-id", "572", "--query", "Champions"],
    ["--source", "scores365"],
])
def test_invalid_cli_selections_do_not_fetch(monkeypatch, arguments):
    fetch = Mock(side_effect=AssertionError("Unexpected source request"))
    monkeypatch.setattr(discovery, "get_api_json", fetch)
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(EXAMPLE))["main"](arguments)
    assert exc.value.code == 2
    fetch.assert_not_called()


def test_cli_prints_native_season_without_inventing_year(monkeypatch, capsys):
    monkeypatch.setattr(discovery, "get_api_json", Mock(return_value={
        "competitions": [{"id": 572, "sportId": 1, "seasons": [{"num": 74, "name": "2026/2027"}]}],
    }))
    main = runpy.run_path(str(EXAMPLE))["main"]
    assert main(["--source", "scores365", "--seasons", "--competition-id", "572"]) == 0
    output = capsys.readouterr().out
    assert "74 | name: 2026/2027 | native year: None" in output
    assert "competition_response" in output


def test_cli_reports_unimplemented_operation_as_manual(monkeypatch, capsys):
    fetch = Mock(side_effect=AssertionError("Unexpected source request"))
    monkeypatch.setattr(discovery, "get_api_json", fetch)
    assert runpy.run_path(str(EXAMPLE))["main"](["--source", "fbref"]) == 1
    assert "DiscoveryNotSupported" in capsys.readouterr().err
    fetch.assert_not_called()


def test_cli_reports_source_block_without_empty_success(monkeypatch, capsys):
    monkeypatch.setattr(discovery, "get_api_json", Mock(side_effect=esd.SourceBlocked("Sample block")))
    assert runpy.run_path(str(EXAMPLE))["main"](["--source", "sofascore", "--category-id", "1"]) == 1
    assert "SourceBlocked: Sample block" in capsys.readouterr().err
