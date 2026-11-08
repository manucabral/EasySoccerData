"""Player comparison examples bound source reads and reproduce saved settings."""

import json
import runpy
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import Mock

import pytest

import esd

ROOT = Path(__file__).resolve().parent.parent / "examples/datasets"
OPTIONS = ["--espn-match-id", "1", "--scores365-match-id", "2", "--espn-season", "2026", "--year", "2026", "--season-id", "74"]


@pytest.fixture
def example(monkeypatch, tmp_path):
    pair, identities = runpy.run_path(str(ROOT / "compare_players_offline.py"))["fixture"]()
    pair = [replace(item, metadata=replace(item.metadata, league=league),
                    match_records=(replace(item.match_records[0], competition_id=league),))
            for item, league in zip(pair, ("uefa.champions", "572"))]
    aliases = [replace(alias, source_id="uefa.champions" if alias.source == "espn" else "572")
               if alias.kind == "competition" else alias for alias in identities.aliases]
    file = tmp_path / "aliases.json"
    file.write_text(json.dumps([asdict(alias) for alias in aliases]), encoding="utf-8")
    loader = Mock(side_effect=pair)
    monkeypatch.setattr(esd, "load_dataset", loader)
    module = runpy.run_path(str(ROOT / "champions_player_comparison.py"))
    return module, loader, [*OPTIONS, "--identities", str(file)], pair


def test_explicit_native_options_shared_read_budget_and_partial_aliases(example, capsys):
    module, loader, options, _ = example
    assert module["main"](options) == 1
    assert loader.call_count == 2
    first, second = [call.kwargs for call in loader.call_args_list]
    assert first["league"] == "uefa.champions" and first["match_ids"] == ["1"] and first["season_id"] is None
    assert second["season_id"] == "74" and second["season"] == 2026
    assert first["tables"] == second["tables"] == ["lineups", "player_match_stats"]
    assert first["max_match_requests"] == second["max_match_requests"] == 1
    assert "Paired players: 2" in capsys.readouterr().out


@pytest.mark.parametrize("arguments", [["--limit", "0"], ["--minutes-tolerance", "nan"], ["--metric", "unknown"],
    ["--metric", "goals", "--minutes-tolerance", "1"], ["--espn-match-id", "0"], ["--espn-season", "26"],
    ["--open-dir", "saved", "--refresh"]])
def test_invalid_settings_fail_before_source_access(example, arguments):
    module, loader, options, _ = example
    with pytest.raises(SystemExit) as exc:
        module["main"](options + arguments)
    assert exc.value.code == 2
    loader.assert_not_called()


def test_missing_extras_fail_before_http(example, monkeypatch, tmp_path):
    module, loader, options, _ = example
    monkeypatch.setitem(module["main"].__globals__, "find_spec", lambda name: None)
    for arguments in (["--pandas"], ["--output-dir", str(tmp_path / "pair")]):
        with pytest.raises(SystemExit) as exc:
            module["main"](options + arguments)
        assert exc.value.code == 2
    loader.assert_not_called()


def test_saved_pair_recomputes_from_sources_and_retains_aliases_and_settings(example, tmp_path):
    pytest.importorskip("pyarrow")
    module, loader, options, pair = example
    target = tmp_path / "pair"
    assert module["main"](options + ["--output-dir", str(target), "--metric", "minutes", "--minutes-tolerance", "2"]) == 1
    report = json.loads((target / "comparison.json").read_text(encoding="utf-8"))
    assert report["tolerances"] == [["minutes", 2.0]]
    assert esd.open_dataset(target / "espn") == pair[0]
    (target / "comparison.json").write_text('{"invented_report": true}', encoding="utf-8")
    loader.side_effect = AssertionError("Offline comparison accessed HTTP")
    assert module["main"](["--open-dir", str(target)]) == 1
    assert loader.call_count == 2
    assert module["read_options"](target / "options.json")["tolerances"] == {"minutes": 2}


def test_existing_destination_is_not_overwritten(example, tmp_path):
    module, loader, options, _ = example
    with pytest.raises(SystemExit) as exc:
        module["main"](options + ["--output-dir", str(tmp_path)])
    assert exc.value.code == 2
    loader.assert_not_called()


def test_partial_downloads_and_failed_tasks_survive_save_and_open(example, tmp_path):
    pytest.importorskip("pyarrow")
    module, loader, options, pair = example
    failed = replace(pair[1], lineup_records=(), player_match_stat_records=(),
                     metadata=replace(pair[1].metadata, successful_tasks=(), response_fetched_at=()),
                     errors=(esd.DatasetIssue("lineups", "2", "SourceBlocked", "Blocked source"),))
    loader.side_effect = [pair[0], failed]
    target = tmp_path / "partial"
    assert module["main"](options + ["--output-dir", str(target)]) == 1
    assert esd.open_dataset(target / "scores365").errors == failed.errors
    assert module["main"](["--open-dir", str(target)]) == 1


@pytest.mark.parametrize("raw", [{"format": "other"}, {"format": "easysoccerdata-player-comparison", "format_version": 99}])
def test_unknown_saved_format_rejected(example, tmp_path, raw):
    module, _, _, _ = example
    path = tmp_path / "options.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError):
        module["read_options"](path)


def test_reviewed_alias_sample_extends_event_map_without_replacing_it():
    sample = json.loads((ROOT / "champions_player_identities.json").read_text(encoding="utf-8"))
    original = json.loads((ROOT / "champions_event_identities.json").read_text(encoding="utf-8"))
    assert all(alias in sample for alias in original)
    assert len({row["canonical_id"] for row in sample if row["kind"] == "player"}) == 12
    assert len(esd.IdentityMap(esd.EntityAlias(**row) for row in sample).aliases) == len(sample)
