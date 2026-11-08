"""Integrated workflow contracts, cache reuse, snapshots and partial source errors."""

import builtins
import json
import runpy
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

import esd

SCRIPT = Path(__file__).resolve().parent.parent / "examples/datasets/champions_workflow.py"


@pytest.fixture
def workflow(monkeypatch, tmp_path):
    module = runpy.run_path(str(SCRIPT))
    selections, identities, responses = module["demo_inputs"]()

    def response(url, **kwargs):
        return deepcopy(responses[url])

    fetch = Mock(side_effect=response)
    monkeypatch.setattr("esd._provider_datasets.get_api_json", fetch)
    datasets = module["download"](selections, tmp_path / "responses", False, request_delay=0)
    settings = module["default_settings"](module["SOURCES"], allow_unknown_period=True)
    return module, selections, identities, datasets, settings, fetch


def test_three_source_workflow_downloads_each_detail_once_and_compares_all_tables(workflow, tmp_path):
    module, selections, identities, datasets, settings, fetch = workflow
    assert fetch.call_count == 7 and all(item.complete for item in datasets)
    assert all(set(item.metadata.tables) == set(module["TABLES"]) for item in datasets)
    reports = module["compare_sources"](datasets, identities, settings)
    assert len(reports) == 3 and all(len(group["matches"]) == 1 for group in reports.values())
    first = reports["espn--scores365"]
    assert first["events"].differences[0].differences == ("minute",)
    assert first["team_statistics"].differences[0].delta == 1
    assert first["players"].statistic_differences[0].metric == "shots"
    sofa = reports["espn--sofascore"]
    assert "source_period" in sofa["events"].rows[0].unknown_fields
    assert sofa["players"].rows[0].right_lineup.confirmed is True
    assert "confirmed" in sofa["players"].rows[0].unknown_fields
    cached = module["download"](selections, tmp_path / "responses", False, request_delay=0)
    assert fetch.call_count == 7 and all(item.metadata.cached_tasks for item in cached)
    for first, second in zip(datasets, cached):
        assert first.metadata.response_fetched_at == second.metadata.response_fetched_at
        assert first.match_event_records == second.match_event_records
    changed = module["compare_sources"](cached, identities, settings)
    for name in reports:
        assert reports[name]["events"].rows == changed[name]["events"].rows
        assert reports[name]["players"].rows == changed[name]["players"].rows


def test_absent_sofa_period_remains_unresolved_under_default_policy(workflow):
    module, _, identities, datasets, _, _ = workflow
    reports = module["compare_sources"](datasets, identities, module["default_settings"](module["SOURCES"]))
    assert len(reports["espn--sofascore"]["events"].unresolved) == 2
    assert not reports["espn--scores365"]["events"].unresolved


def test_unknown_aliases_do_not_hide_native_players_or_events(workflow):
    module, _, _, datasets, settings, _ = workflow
    reports = module["compare_sources"](datasets, esd.IdentityMap(), settings)
    for group in reports.values():
        assert not group["matches"] and len(group["players"].unresolved) == 2
        assert len(group["events"].unresolved) == 2


def test_demo_and_pandas_paths(workflow, capsys):
    module, _, _, _, _, _ = workflow
    assert module["main"](["--demo", "--allow-unknown-period", "--limit", "1"]) == 0
    assert "cache reused 7 tasks without HTTP" in capsys.readouterr().out
    pytest.importorskip("pandas")
    assert module["main"](["--demo", "--pandas", "--limit", "1"]) == 0


def test_live_mode_uses_only_supplied_native_ids_and_shares_detail_responses(workflow, monkeypatch, tmp_path):
    module, _, identities, datasets, _, _ = workflow
    path = tmp_path / "aliases.json"
    path.write_text(json.dumps([asdict(row) for row in identities.aliases]), encoding="utf-8")
    loader = Mock(side_effect=datasets)
    monkeypatch.setattr(esd, "load_dataset", loader)
    args = ["--espn-match-id", "1", "--scores365-match-id", "2", "--espn-season", "2026", "--year", "2026",
            "--scores365-season-id", "228", "--sofascore-match-id", "3", "--sofascore-season-id", "228", "--identities", str(path)]
    assert module["main"](args) == 0
    assert [call.kwargs["max_match_requests"] for call in loader.call_args_list] == [1, 2, 4]
    assert [call.kwargs["match_ids"] for call in loader.call_args_list] == [["1"], ["2"], ["3"]]
    assert all(set(call.kwargs["tables"]) == set(module["TABLES"]) for call in loader.call_args_list)


@pytest.mark.parametrize("args", [[], ["--demo", "--year", "2026"], ["--demo", "--minute-tolerance", "-1"],
    ["--demo", "--kickoff-tolerance", "nan"], ["--demo", "--max-match-requests", "6"], ["--demo", "--limit", "0"],
    ["--open-dir", "saved", "--allow-unknown-period"], ["--open-dir", "saved", "--demo"]])
def test_invalid_cli_fails_before_native_download(workflow, monkeypatch, args):
    module, _, _, _, _, _ = workflow
    loader = Mock()
    monkeypatch.setattr(esd, "load_dataset", loader)
    with pytest.raises(SystemExit) as exc:
        module["main"](args)
    assert exc.value.code == 2
    loader.assert_not_called()


def test_missing_extras_and_existing_output_fail_before_http(workflow, monkeypatch, tmp_path):
    module, _, _, _, _, _ = workflow
    loader = Mock()
    monkeypatch.setattr(esd, "load_dataset", loader)
    monkeypatch.setitem(module["main"].__globals__, "find_spec", lambda _: None)
    for options in (["--demo", "--pandas"], ["--demo", "--output-dir", str(tmp_path / "new")]):
        with pytest.raises(SystemExit) as exc:
            module["main"](options)
        assert exc.value.code == 2
    monkeypatch.setitem(module["main"].__globals__, "find_spec", lambda _: object())
    with pytest.raises(SystemExit) as exc:
        module["main"](["--demo", "--output-dir", str(tmp_path)])
    assert exc.value.code == 2
    loader.assert_not_called()


def test_saved_bundle_recomputes_original_observations_and_settings_without_http(workflow, tmp_path):
    pytest.importorskip("pyarrow")
    module, _, identities, datasets, settings, _ = workflow
    reports = module["compare_sources"](datasets, identities, settings)
    target = tmp_path / "bundle"
    module["save_bundle"](target, datasets, identities, settings, reports)
    options = json.loads((target / "options.json").read_text(encoding="utf-8"))
    assert options["events"]["allow_unknown_period"] is True and options["events"]["period_aliases"]
    with patch("esd._provider_datasets.get_api_json", side_effect=AssertionError("Offline HTTP access")):
        (target / "comparison.json").write_text('{"invented": true}', encoding="utf-8")
        assert module["main"](["--open-dir", str(target)]) == 0
        restored = [esd.open_dataset(target / source) for source in module["SOURCES"]]
        assert restored == datasets
        assert module["compare_sources"](restored, identities, options) == reports


def test_scoped_identity_dates_and_evidence_survive_saved_workflow(workflow, tmp_path):
    pytest.importorskip("pyarrow")
    from datetime import datetime, timedelta, timezone

    module, _, identities, datasets, settings, _ = workflow
    start = datetime(2026, 11, 3, tzinfo=timezone.utc)
    scoped = esd.IdentityMap(replace(alias, team_id=next(dataset.lineup_records[0].team_id for dataset in datasets
                                                       if dataset.metadata.source == alias.source),
                                     valid_from=start, valid_until=start + timedelta(days=1),
                                     source_url="https://example.com/reviewed-roster", verified_at=start)
                             if alias.kind == "player" else alias for alias in identities.aliases)
    reports = module["compare_sources"](datasets, scoped, settings)
    target = tmp_path / "scoped"
    module["save_bundle"](target, datasets, scoped, settings, reports)
    restored = module["read_identities"](target / "identities.json")
    assert restored.aliases == scoped.aliases
    assert module["compare_sources"](datasets, restored, settings) == reports
    assert module["main"](["--open-dir", str(target)]) == 0


def test_partial_sofa_error_stays_visible_after_offline_reopening(workflow, tmp_path):
    pytest.importorskip("pyarrow")
    module, _, identities, datasets, settings, _ = workflow
    failed = replace(datasets[2], match_event_records=(),
                     metadata=replace(datasets[2].metadata, successful_tasks=("match:3", "lineups:3", "match_stats:3"),
                                      response_fetched_at=tuple(row for row in datasets[2].metadata.response_fetched_at if row[0] != "match_events:3")),
                     errors=(esd.DatasetIssue("match_events", "3", "SourceBlocked", "Blocked incidents"),))
    datasets = [*datasets[:2], failed]
    reports = module["compare_sources"](datasets, identities, settings)
    target = tmp_path / "partial"
    module["save_bundle"](target, datasets, identities, settings, reports)
    assert esd.open_dataset(target / "sofascore").errors == failed.errors
    assert module["main"](["--open-dir", str(target)]) == 1
    assert reports["espn--sofascore"]["players"].right_coverage[0].successful
    assert not reports["espn--sofascore"]["events"].right_coverage[0].successful


def test_save_failure_cleans_owned_staging_without_publishing_partial_bundle(workflow, monkeypatch, tmp_path):
    pytest.importorskip("pyarrow")
    module, _, identities, datasets, settings, _ = workflow
    reports = module["compare_sources"](datasets, identities, settings)
    save = esd.SoccerDataset.save

    def failing(dataset, *args, **kwargs):
        if dataset.metadata.source == "scores365":
            raise OSError("disk full")
        return save(dataset, *args, **kwargs)

    monkeypatch.setattr(esd.SoccerDataset, "save", failing)
    before = set(tmp_path.iterdir())
    with pytest.raises(OSError, match="disk full"):
        module["save_bundle"](tmp_path / "partial", datasets, identities, settings, reports)
    assert set(tmp_path.iterdir()) == before


@pytest.mark.parametrize("damage", ["source_path", "version", "missing_key", "bad_period", "duplicate_position", "metric"])
def test_invalid_saved_rules_or_source_paths_fail_without_http(workflow, tmp_path, damage):
    module, _, identities, datasets, settings, _ = workflow
    settings = deepcopy(settings)
    if damage == "source_path":
        settings["sources"][2] = "../outside"
    elif damage == "version":
        settings["format_version"] = True
    elif damage == "missing_key":
        del settings["events"]["allow_unknown_period"]
    elif damage == "bad_period":
        settings["events"]["period_aliases"] = ["period"]
    elif damage == "duplicate_position":
        settings["players"]["position_aliases"] = [["sofascore", "F", "forward"]] * 2
    else:
        settings["players"]["metrics"] = ["unknown"]
    with pytest.raises(ValueError):
        module["compare_sources"](datasets, identities, settings)


def test_base_workflow_does_not_import_pandas_or_arrow(workflow):
    module, _, identities, datasets, settings, _ = workflow
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in ("pandas", "pyarrow"):
            raise AssertionError(f"Optional import: {name}")
        return original(name, *args, **kwargs)

    with patch("builtins.__import__", guarded):
        assert len(module["compare_sources"](datasets, identities, settings)) == 3


def test_workflow_alias_sample_extends_reviewed_players_with_explicit_sofa_ids(workflow):
    module, _, _, _, _, _ = workflow
    identities = module["read_identities"](module["DEFAULT_IDENTITIES"])
    original = module["read_identities"](SCRIPT.with_name("champions_player_identities.json"))
    assert all(alias in identities.aliases for alias in original.aliases)
    assert identities.resolve("team", "sofascore", "3313") == "shakhtar"
    assert identities.resolve("team", "sofascore", "3001") == "sporting"
    assert identities.resolve("player", "sofascore", "1141754") == "issa-doumbia"


@pytest.mark.parametrize("code,failures,raises,calls", [(145, 1, False, 2), (145, 2, False, 3),
                                                       (145, 3, True, 3), (5, 1, True, 1)])
def test_owned_directory_cleanup_retries_only_bounded_transient_errors(tmp_path, monkeypatch, code, failures, raises, calls):
    module = runpy.run_path(str(SCRIPT))
    namespace = module["workflow_directory"].__wrapped__.__globals__
    error = OSError("Temporary cleanup failed")
    error.winerror = code
    temporary = Mock(name=str(tmp_path))
    temporary.name = str(tmp_path)
    temporary.cleanup.side_effect = [*([error] * failures), None]
    pause = Mock()
    monkeypatch.setitem(namespace, "TemporaryDirectory", Mock(return_value=temporary))
    monkeypatch.setitem(namespace, "sleep", pause)
    if raises:
        with pytest.raises(OSError) as caught, module["workflow_directory"]("demo"):
            pass
        assert caught.value is error
    else:
        with module["workflow_directory"]("demo") as directory:
            assert directory == tmp_path
    assert temporary.cleanup.call_count == calls and pause.call_count == calls - 1
