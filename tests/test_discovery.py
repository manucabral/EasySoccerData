"""Discovery preserves native selectors and makes query limitations explicit."""

import subprocess
import sys
from copy import deepcopy
from dataclasses import FrozenInstanceError
from unittest.mock import Mock

import pytest

import esd
from esd import discovery


@pytest.fixture
def fetch(monkeypatch):
    fetch = Mock()
    monkeypatch.setattr(discovery, "get_api_json", fetch)
    return fetch


def test_capabilities_cover_all_nine_sources_without_fetching(fetch):
    capabilities = esd.get_discovery_capabilities()
    assert set(capabilities) == set(esd.get_dataset_capabilities())
    assert capabilities["scores365"].seasons == "competition_response"
    assert capabilities["fbref"].competitions is None
    capabilities.pop("espn")
    assert "espn" in esd.get_discovery_capabilities()
    with pytest.raises(FrozenInstanceError):
        esd.get_discovery_capabilities("espn").source = "other"
    fetch.assert_not_called()


@pytest.mark.parametrize("source", ["fbref", "understat", "besoccer", "goaloo"])
def test_manual_competition_selection_is_explicit_before_io(fetch, source):
    with pytest.raises(esd.DiscoveryNotSupported, match="manually"):
        esd.list_competitions(source)
    fetch.assert_not_called()


@pytest.mark.parametrize("source", ["fbref", "understat", "promiedos"])
def test_manual_season_selection_is_explicit_before_io(fetch, source):
    with pytest.raises(esd.DiscoveryNotSupported, match="manually"):
        esd.list_seasons(source, "native")
    fetch.assert_not_called()


def test_espn_keeps_numeric_id_separate_from_dataset_slug_and_filters_names(fetch):
    payload = {"leagues": [
        {"id": "775", "slug": "uefa.champions", "name": "UEFA Champions League"},
        {"id": "23", "slug": "eng.1", "name": "Premier League"},
    ]}
    fetch.return_value = deepcopy(payload)
    result = esd.list_competitions("espn", query="CHAMPIONS")
    assert result.competitions == (
        esd.CompetitionInfo("espn", "uefa.champions", "UEFA Champions League", "775"),
    )
    assert result.scope == "listing" and result.query == "CHAMPIONS"
    assert result.fetched_at.utcoffset().total_seconds() == 0 and not result.cached
    assert fetch.return_value == payload


def test_scores_search_excludes_other_sports_and_keeps_provider_names(fetch):
    fetch.return_value = {"competitions": [
        {"id": 572, "name": "UEFA Champions League", "sportId": 1},
        {"id": 900, "name": "Champions", "sportId": 2},
    ]}
    result = esd.list_competitions("scores365", query="Champions & qualifiers")
    assert [row.competition_id for row in result.competitions] == ["572"]
    assert result.scope == "search"
    assert "Champions%20%26%20qualifiers" in fetch.call_args.args[0]


def test_sofascore_reads_all_groups_and_deduplicates_same_entry(fetch):
    first, second = {"id": 17, "name": "Premier League"}, {"id": 19, "name": "FA Cup"}
    fetch.return_value = {"groups": [{"uniqueTournaments": [first]}, {"uniqueTournaments": [first, second]}]}
    result = esd.list_competitions("sofascore", category_id=1)
    assert [row.competition_id for row in result.competitions] == ["17", "19"]
    assert result.category_id == "1" and result.scope == "category"
    assert fetch.call_args.args[0].endswith("/category/1/unique-tournaments")


def test_promiedos_only_lists_the_selected_day_and_sends_required_header(fetch):
    fetch.return_value = {"leagues": [{"id": "hc", "name": "Liga Profesional"}]}
    result = esd.list_competitions("promiedos", date="2026-11-07")
    assert result.date == "2026-11-07" and result.scope == "date"
    assert result.competitions[0].competition_id == "hc"
    assert fetch.call_args.args[0].endswith("/games/07-11-2026")
    assert fetch.call_args.kwargs["headers"]["X-VER"] == "1.11.7.5"


@pytest.mark.parametrize("source, competition, payload, expected", [
    ("espn", "uefa.champions", {"count": 1, "pageCount": 1, "items": [{"$ref": "http://sports.core.api.espn.com/v2/sports/soccer/leagues/uefa.champions/seasons/2026?lang=en"}]},
     esd.SeasonInfo("espn", "uefa.champions", "2026", year=2026)),
    ("scores365", 572, {"competitions": [{"id": 572, "sportId": 1, "seasons": [{"num": 74, "name": "2026/2027"}]}]},
     esd.SeasonInfo("scores365", "572", "74", "2026/2027")),
    ("sofascore", 7, {"seasons": [{"id": 96518, "name": "UEFA Champions League 26/27", "year": "26/27"}]},
     esd.SeasonInfo("sofascore", "7", "96518", "UEFA Champions League 26/27", source_season="26/27")),
    ("goaloo", 36, {"SeasonList": ["2026-2027"]},
     esd.SeasonInfo("goaloo", "36", "2026-2027", "2026-2027", source_season="2026-2027")),
])
def test_native_seasons_are_not_guessed_from_year_labels(fetch, source, competition, payload, expected):
    fetch.return_value = payload
    result = esd.list_seasons(source, competition)
    assert result.seasons == (expected,)
    assert result.competition_id == str(competition)
    assert not result.competitions


@pytest.mark.parametrize("operation, arguments, payload", [
    (esd.list_competitions, ("espn",), {}),
    (esd.list_competitions, ("espn",), {"leagues": [{}]}),
    (esd.list_competitions, ("espn",), {"leagues": [None]}),
    (esd.list_competitions, ("espn",), {"leagues": [{"id": "1", "slug": "same", "name": "A"}, {"id": "2", "slug": "same", "name": "B"}]}),
    (esd.list_seasons, ("goaloo", 36), {"SeasonList": [1]}),
    (esd.list_seasons, ("scores365", 572), {"competitions": [{"id": 332, "sportId": 1, "seasons": []}]}),
    (esd.list_seasons, ("scores365", 572), {"competitions": [{"id": 572, "sportId": 2, "seasons": []}]}),
    (esd.list_seasons, ("sofascore", 7), {"seasons": [{"id": None, "name": "Name"}]}),
    (esd.list_seasons, ("espn", "eng.1"), {"pageCount": 2, "count": 2, "items": []}),
    (esd.list_seasons, ("espn", "eng.1"), {"pageCount": 1, "count": 1, "items": [{"$ref": "https://sports.core.api.espn.com/v2/sports/soccer/leagues/esp.1/seasons/2026"}]}),
])
def test_malformed_or_conflicting_source_data_is_not_cached(fetch, tmp_path, operation, arguments, payload):
    fetch.return_value = payload
    with pytest.raises(esd.SourceError):
        operation(*arguments, cache_dir=tmp_path)
    assert not list(tmp_path.rglob("*.json"))


@pytest.mark.parametrize("operation, arguments, options", [
    (esd.list_competitions, (None,), {}),
    (esd.list_seasons, (None, 572), {}),
    (esd.list_competitions, ("unknown",), {}),
    (esd.list_competitions, ("scores365",), {}),
    (esd.list_competitions, ("espn",), {"query": " "}),
    (esd.list_competitions, ("espn",), {"category_id": 1}),
    (esd.list_competitions, ("espn",), {"date": "2026-11-07"}),
    (esd.list_competitions, ("sofascore",), {}),
    (esd.list_competitions, ("promiedos",), {"date": "2026-1-07"}),
    (esd.list_seasons, ("espn", 775), {}),
    (esd.list_seasons, ("scores365", True), {}),
    (esd.list_seasons, ("goaloo", -1), {}),
    (esd.list_seasons, ("goaloo", 36), {"refresh": "yes"}),
    (esd.list_seasons, ("goaloo", 36), {"cache_policy": "invalid"}),
    (esd.list_seasons, ("goaloo", 36), {"cache_policy": esd.CachePolicy()}),
])
def test_invalid_selection_is_rejected_before_network(fetch, operation, arguments, options):
    with pytest.raises(ValueError):
        operation(*arguments, **options)
    fetch.assert_not_called()


def test_cache_preserves_fetch_time_and_validates_before_forced_replacement(fetch, tmp_path):
    fetch.return_value = {"SeasonList": ["2026-2027"]}
    first = esd.list_seasons("goaloo", 36, cache_dir=tmp_path)
    cached = esd.list_seasons("goaloo", 36, cache_dir=tmp_path)
    assert fetch.call_count == 1 and cached.cached
    assert cached.fetched_at == first.fetched_at
    fetch.return_value = {}
    with pytest.raises(esd.SourceError):
        esd.list_seasons("goaloo", 36, cache_dir=tmp_path, refresh=True)
    recovered = esd.list_seasons("goaloo", 36, cache_dir=tmp_path)
    assert recovered.cached and recovered.seasons == first.seasons
    fetch.return_value = {"SeasonList": ["2025-2026"]}
    changed = esd.list_seasons("goaloo", 36, cache_dir=tmp_path, refresh=True)
    assert not changed.cached and changed.seasons[0].source_season == "2025-2026"


def test_http_blocks_are_propagated_without_becoming_empty_results(fetch):
    fetch.side_effect = esd.SourceBlocked("Sample block")
    with pytest.raises(esd.SourceBlocked, match="Sample block"):
        esd.list_seasons("sofascore", 7)


def test_proxy_options_are_forwarded(fetch):
    fetch.return_value = {"SeasonList": []}
    proxies = {"https": "http://proxy.test"}
    assert esd.list_seasons("goaloo", 36, proxies=proxies).seasons == ()
    assert fetch.call_args.kwargs["proxies"] is proxies


def test_discovery_requires_neither_optional_packages_nor_browser():
    code = '''
import importlib.abc
import sys
class NoExtras(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('pandas', 'pyarrow'):
            raise ModuleNotFoundError('Optional import blocked', name=fullname)
sys.meta_path.insert(0, NoExtras())
import esd
from unittest.mock import patch
with patch('esd.discovery.get_api_json', return_value={'SeasonList': ['2026-2027']}), patch('esd.utils.BrowserSession._launch', side_effect=AssertionError('Browser launched')):
    result = esd.list_seasons('goaloo', 36)
    assert result.seasons[0].season_id == '2026-2027'
assert 'pandas' not in sys.modules and 'pyarrow' not in sys.modules
'''
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
