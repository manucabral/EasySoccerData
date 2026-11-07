"""HTML selectors, search scope, source identity and cache failure behavior."""

from unittest.mock import Mock

import pytest

import esd
from esd import discovery
from esd.transfermarkt.types import parse_search_html

SEARCH = '''<html><a href="/unrelated/startseite/wettbewerb/ZZ">Navigation</a>
<div id="competition-grid"><table><tbody>
<tr><td><a href="/uefa-champions-league/startseite/pokalwettbewerb/CL">UEFA Champions League</a></td></tr>
<tr><td><a href="/premier-league/startseite/wettbewerb/GB1">Premier League</a></td></tr>
</tbody></table></div></html>'''
URL = "https://www.transfermarkt.com/uefa-champions-league/startseite/pokalwettbewerb/CL"
TM_SEASONS = '''<form action="/uefa-champions-league/gesamtspielplan/pokalwettbewerb/CL">
<select name="saison_id"><option value="2026">26/27</option><option value="1999">99/00</option></select></form>'''
BE_SEASONS = '''<select id="season" name="season"
data-url="https://es.besoccer.com/competicion/clasificacion/champions/NNN">
<option value="2027">2026-27</option><option value="2026">2025-26</option></select>'''


@pytest.fixture
def fetch(monkeypatch):
    fetch = Mock(return_value=SEARCH)
    monkeypatch.setattr(discovery, "get_text", fetch)
    monkeypatch.setattr(discovery, "get_api_json", Mock(side_effect=AssertionError("Unexpected JSON request")))
    return fetch


def test_search_uses_only_competition_grid_and_keeps_native_cup_route(fetch):
    fetch.return_value = SEARCH.replace("</table>", '</table><ul class="tm-pagination"><li class="tm-pagination__list-item--active"><a>2</a></li></ul>')
    result = esd.list_competitions("transfermarkt", query="Champions & leagues", page=2)
    assert [(x.competition_id, x.name) for x in result.competitions] == [
        ("CL", "UEFA Champions League"), ("GB1", "Premier League"),
    ]
    assert result.competitions[0].source_url == URL
    assert result.scope == "search_page" and result.page == 2
    assert "Wettbewerb_page=2" in fetch.call_args.args[0]
    assert "Champions%20%26%20leagues" in result.source_url
    assert "ZZ" not in [x.native_id for x in result.competitions]


def test_existing_search_parser_handles_cups_and_current_competition_cells():
    assert [row.id for row in parse_search_html(SEARCH)] == ["CL", "GB1"]


@pytest.mark.parametrize("source, competition, raw, options, expected", [
    ("besoccer", "champions", BE_SEASONS, {}, esd.SeasonInfo("besoccer", "champions", "2027", "2026-27", year=2027)),
    ("transfermarkt", "CL", TM_SEASONS, {"competition_url": URL}, esd.SeasonInfo("transfermarkt", "CL", "2026", "26/27")),
])
def test_season_selectors_keep_source_year_conventions(fetch, source, competition, raw, options, expected):
    fetch.return_value = raw
    result = esd.list_seasons(source, competition, **options)
    assert result.seasons[0] == expected
    assert result.source_url == fetch.call_args.args[0]
    assert result.scope == "selector"
    if source == "besoccer":
        assert fetch.call_args.kwargs["impersonate"] == "safari17_0"
    else:
        assert "/gesamtspielplan/pokalwettbewerb/CL" in result.source_url


def test_transfermarkt_league_form_accepts_native_plus_suffix(fetch):
    fetch.return_value = TM_SEASONS.replace("uefa-champions-league/gesamtspielplan/pokalwettbewerb/CL", "premier-league/startseite/wettbewerb/GB1/plus/")
    result = esd.list_seasons("transfermarkt", "GB1", competition_url="https://www.transfermarkt.com/premier-league/startseite/wettbewerb/GB1")
    assert result.seasons[0].season_id == "2026"


@pytest.mark.parametrize("raw", [
    '<div id="competition-grid"><table><tbody><tr><td class="empty">No results</td></tr></tbody></table></div>',
    '<section class="no-result"><h2>Nothing found?</h2></section>',
    '<form action="/schnellsuche/ergebnis/schnellsuche"></form><div id="player-grid"><table><tbody><tr><td>Example player</td></tr></tbody></table></div>',
])
def test_explicit_empty_search_is_valid(fetch, raw):
    fetch.return_value = raw
    assert esd.list_competitions("transfermarkt", query="No match").competitions == ()


@pytest.mark.parametrize("raw", [
    "<html><body>Maintenance</body></html>",
    SEARCH.replace("pokalwettbewerb/CL", "verein/CL"),
    SEARCH.replace("/uefa-champions-league/", "https://unrelated.test/uefa-champions-league/"),
    SEARCH.replace("UEFA Champions League</a>", "</a>"),
])
def test_invalid_search_does_not_publish_cache(fetch, tmp_path, raw):
    fetch.return_value = raw
    with pytest.raises(esd.SourceError):
        esd.list_competitions("transfermarkt", query="Champions", cache_dir=tmp_path)
    assert not list(tmp_path.rglob("*.json"))


def test_clamped_page_is_reported_instead_of_mislabeled_results(fetch, tmp_path):
    fetch.return_value = SEARCH.replace("</table>", '</table><ul class="tm-pagination"><li class="tm-pagination__list-item--active"><a>15</a></li></ul>')
    with pytest.raises(esd.SourceError, match="different.*page"):
        esd.list_competitions("transfermarkt", query="Champions", page=999, cache_dir=tmp_path)
    assert not list(tmp_path.rglob("*.json"))


@pytest.mark.parametrize("raw", [
    BE_SEASONS.replace("/champions/NNN", "/premier/NNN"),
    BE_SEASONS.replace('value="2027"', 'value="26/27"'),
    BE_SEASONS.replace('name="season"', 'name="round"'),
    "<html>Other content</html>",
])
def test_malformed_or_wrong_competition_selector_is_not_empty(fetch, raw):
    fetch.return_value = raw
    with pytest.raises(esd.SourceError):
        esd.list_seasons("besoccer", "champions")


def test_wrong_transfermarkt_form_does_not_establish_season_identity(fetch):
    fetch.return_value = TM_SEASONS.replace("/CL", "/EL")
    with pytest.raises(esd.SourceError):
        esd.list_seasons("transfermarkt", "CL", competition_url=URL)


@pytest.mark.parametrize("url", [
    None, "https://unrelated.test/a/startseite/pokalwettbewerb/CL",
    URL.replace("/CL", "/EL"), URL + "?x=1", URL + "#fragment",
    URL.replace("https://", "http://"), URL.replace("www.transfermarkt.com", "www.transfermarkt.com@unrelated.test"),
])
def test_season_url_must_match_provider_and_competition_before_io(fetch, url):
    with pytest.raises(ValueError):
        esd.list_seasons("transfermarkt", "CL", competition_url=url)
    fetch.assert_not_called()


@pytest.mark.parametrize("source, options", [
    ("transfermarkt", {}), ("transfermarkt", {"query": "Champions", "page": 0}),
    ("transfermarkt", {"query": "Champions", "page": True}),
    ("espn", {"page": 2}),
])
def test_invalid_search_arguments_do_not_fetch(fetch, source, options):
    with pytest.raises(ValueError):
        esd.list_competitions(source, **options)
    fetch.assert_not_called()


def test_html_cache_preserves_timestamp_and_valid_entry_on_block(fetch, tmp_path):
    first = esd.list_competitions("transfermarkt", query="Champions", cache_dir=tmp_path)
    cached = esd.list_competitions("transfermarkt", query="Champions", cache_dir=tmp_path)
    assert cached.cached and cached.fetched_at == first.fetched_at and fetch.call_count == 1
    fetch.return_value = "<title>Client Challenge</title>"
    with pytest.raises(esd.SourceBlocked):
        esd.list_competitions("transfermarkt", query="Champions", cache_dir=tmp_path, refresh=True)
    recovered = esd.list_competitions("transfermarkt", query="Champions", cache_dir=tmp_path)
    assert recovered.competitions == first.competitions and recovered.cached
    assert fetch.call_count == 2
