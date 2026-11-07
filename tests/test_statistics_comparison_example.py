"""Champions CLI uses explicit bounded requests and reopens source pairs offline."""

import json
import runpy
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import Mock

import pytest

import esd

ROOT = Path(__file__).resolve().parent.parent / "examples/datasets"
OPTIONS = ["--espn-match-id", "1", "--scores365-match-id", "2", "--season", "2026", "--season-id", "74"]


@pytest.fixture
def example(monkeypatch, tmp_path):
    pair, identities = runpy.run_path(str(ROOT / "compare_statistics_offline.py"))["example_pair"]()
    pair = [replace(item, metadata=replace(item.metadata, league=league),
                    match_records=(replace(item.match_records[0], competition_id=league),))
            for item, league in zip(pair, ("uefa.champions", "572"))]
    aliases = [esd.EntityAlias(kind, canonical, source, native)
               for kind, canonical, natives in (("competition", "cup", ("uefa.champions", "572")),
                                                ("team", "home", ("10", "30")), ("team", "away", ("20", "40")))
               for source, native in zip(("espn", "scores365"), natives)]
    path = tmp_path / "aliases.json"
    path.write_text(json.dumps([asdict(item) for item in aliases]), encoding="utf-8")
    fetch = Mock(side_effect=pair)
    monkeypatch.setattr(esd, "load_dataset", fetch)
    return runpy.run_path(str(ROOT / "champions_statistics.py")), fetch, path


def test_live_cli_limits_requests_and_reports_diagnostic_differences(example, capsys):
    module, fetch, aliases = example
    assert module["main"](OPTIONS + ["--identities", str(aliases)]) == 0
    assert fetch.call_count == 2
    for call in fetch.call_args_list:
        assert call.kwargs["max_match_requests"] == 1 and call.kwargs["tables"] == ["match_stats"]
        assert len(call.kwargs["match_ids"]) == 1
    assert "Linked matches: 1 | Differences: 1" in capsys.readouterr().out


@pytest.mark.parametrize("options", [[], ["--espn-match-id", "0"], ["--possession-tolerance", "nan"],
                                      ["--kickoff-tolerance", "-1"], ["--open-dir", "missing", "--season", "2026"]])
def test_bad_cli_selection_is_rejected_before_download(example, options):
    module, fetch, aliases = example
    with pytest.raises(SystemExit) as exc:
        module["main"](options)
    assert exc.value.code == 2
    fetch.assert_not_called()


@pytest.mark.parametrize("extra,options", [("pyarrow", ["--output-dir", "new-pair"]), ("pandas", ["--pandas"])])
def test_optional_extras_are_checked_before_download(example, extra, options):
    module, fetch, aliases = example
    module["main"].__globals__["find_spec"] = lambda name: None if name == extra else object()
    with pytest.raises(SystemExit) as exc:
        module["main"](OPTIONS + ["--identities", str(aliases)] + options)
    assert exc.value.code == 2
    fetch.assert_not_called()


def test_existing_destination_and_invalid_aliases_fail_before_download(example, tmp_path):
    module, fetch, aliases = example
    with pytest.raises(SystemExit) as exc:
        module["main"](OPTIONS + ["--output-dir", str(tmp_path)])
    assert exc.value.code == 2
    aliases.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        module["main"](OPTIONS + ["--identities", str(aliases)])
    assert exc.value.code == 2
    fetch.assert_not_called()


def test_saved_report_recomputes_from_snapshots_without_http(example, tmp_path, capsys):
    pytest.importorskip("pyarrow")
    module, fetch, aliases = example
    destination = tmp_path / "pair"
    assert module["main"](OPTIONS + ["--identities", str(aliases), "--output-dir", str(destination)]) == 0
    original = json.loads((destination / "comparison.json").read_text(encoding="utf-8"))
    assert original["rows"][0]["status"] == "different" and original["left_complete"]
    fetch.side_effect = AssertionError("Unexpected source request")
    assert module["main"](["--open-dir", str(destination)]) == 0
    assert fetch.call_count == 2
    assert "Saved and verified:" in capsys.readouterr().out


def test_unmatched_ids_return_failure_without_selecting_by_name(example, capsys):
    module, fetch, aliases = example
    aliases.write_text("[]", encoding="utf-8")
    assert module["main"](OPTIONS + ["--identities", str(aliases)]) == 1
    assert "Unmatched ESPN" in capsys.readouterr().out
