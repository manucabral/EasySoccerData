"""Catalog names resolve reviewed IDs; source season labels never become years."""

import json
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

import esd
from esd import catalog as catalog_module
from esd import discovery

NOW = datetime(2026, 11, 7, tzinfo=timezone.utc)


def reference(source="espn", identifier="test.cup"):
    return esd.CatalogReference(source, identifier, "https://example.com/review", NOW)


@pytest.fixture
def fetch(monkeypatch):
    fetch = Mock()
    monkeypatch.setattr(discovery, "get_api_json", fetch)
    return fetch


def test_bundled_lookup_is_explicit_and_does_not_request_sources(fetch):
    catalog = esd.get_catalog()
    assert len(catalog.competitions) == 3 and len(catalog.teams) == 62
    champions = catalog.competition("  UEFA   CHAMPIONS League ")
    assert champions == catalog.competition("champions-league") == catalog.competition("Champions League")
    assert champions.for_source("espn").source_id == "uefa.champions"
    assert champions.for_source("espn").native_id == "775"
    assert champions.for_source("scores365").source_id == "572"
    assert catalog.competition("Premier League").for_source("scores365").source_id == "7"
    assert catalog.competition("La Liga").for_source("espn").source_id == "esp.1"
    assert catalog.team("FC Barcelona").for_source("espn").source_id == "83"
    assert catalog.team("barcelona").for_source("scores365").source_id == "132"
    assert all(ref.verified_at.utcoffset() == timedelta(0) and ref.source_url.startswith("https://")
               for entity in (*catalog.competitions, *catalog.teams) for ref in entity.references)
    fetch.assert_not_called()


@pytest.mark.parametrize("name", ["Champions", "Liverpool FC invented alias", "Real Madrd", "", None])
def test_names_are_not_fuzzy_matched_or_interpreted_as_native_ids(name):
    with pytest.raises(ValueError):
        esd.get_catalog().team(name)
    with pytest.raises(ValueError):
        esd.get_catalog().competition(name)


def test_source_namespaces_are_distinct_and_identity_maps_are_independent():
    catalog = esd.get_catalog()
    identities = catalog.identities()
    assert identities is not catalog.identities()
    assert identities.resolve("team", "espn", "132") == "bayern"
    assert identities.resolve("team", "scores365", "132") == "barcelona"
    assert identities.resolve("competition", "espn", "uefa.champions") == "champions-league"
    assert identities.resolve("competition", "scores365", "572") == "champions-league"
    assert identities.resolve("team", "espn", "not-reviewed") is None
    with pytest.raises(FrozenInstanceError):
        catalog.version = "changed"


def test_catalog_extensions_add_sources_and_aliases_without_mutating_defaults():
    original = esd.get_catalog()
    champions = original.competition("Champions League")
    added = replace(champions, references=(reference("sofascore", "7"),), aliases=("My cup",))
    club = esd.CatalogTeam("my-club", "My club", (reference("espn", "new-team"),))
    extended = original.with_entries(competitions=[added], teams=[club], version="my-project-1")
    assert extended.competition("My cup").for_source("sofascore").source_id == "7"
    assert extended.team("My club").for_source("espn").source_id == "new-team"
    assert extended.competition("Champions League").for_source("espn") == champions.for_source("espn")
    assert extended.version == "my-project-1" and len(original.teams) == 62
    with pytest.raises(ValueError):
        original.competition("My cup")
    with pytest.raises(ValueError):
        champions.for_source("sofascore")


@pytest.mark.parametrize("change", ["alias", "native", "name", "replacement", "duplicate", "kind"])
def test_conflicting_extensions_are_rejected(change):
    catalog = esd.get_catalog()
    team = catalog.team("barcelona")
    if change == "alias":
        entry = esd.CatalogTeam("other-club", "Other club", (reference("espn", "new"),), aliases=("barcelona",))
    elif change == "native":
        entry = esd.CatalogTeam("other-club", "Other club", (reference("espn", "83"),))
    elif change == "name":
        entry = replace(team, name="Changed name")
    elif change == "replacement":
        entry = replace(team, references=(reference("espn", "new"),))
    elif change == "duplicate":
        with pytest.raises(ValueError):
            esd.FootballCatalog(teams=(team, team))
        return
    else:
        entry = esd.get_catalog().competition("Champions League")
    with pytest.raises(ValueError):
        catalog.with_entries(teams=[entry])


@pytest.mark.parametrize("change", ["naive", "source", "blank", "url", "credentials", "native"])
def test_review_references_require_valid_ids_and_provenance(change):
    values = {"source": "espn", "source_id": "test.cup", "source_url": "https://example.com/review", "verified_at": NOW}
    if change == "naive":
        values["verified_at"] = NOW.replace(tzinfo=None)
    elif change == "source":
        values["source"] = "unknown"
    elif change == "blank":
        values["source_id"] = " "
    elif change == "url":
        values["source_url"] = "file:///local-file"
    elif change == "credentials":
        values["source_url"] = "https://username:secret@example.com/review"
    else:
        values["native_id"] = 1
    with pytest.raises(ValueError):
        esd.CatalogReference(**values)


def test_season_discovery_uses_the_catalog_selector_and_existing_cache(fetch, tmp_path):
    fetch.return_value = {"competitions": [{"id": 572, "sportId": 1,
                                           "seasons": [{"num": 74, "name": "2026/2027"}]}]}
    catalog = esd.get_catalog()
    first = catalog.list_seasons("Champions League", "scores365", cache_dir=tmp_path)
    second = catalog.list_seasons("champions-league", "scores365", cache_dir=tmp_path)
    assert first.seasons == second.seasons and second.cached and first.fetched_at == second.fetched_at
    assert fetch.call_count == 1 and "competitions=572" in fetch.call_args.args[0]
    with pytest.raises(ValueError):
        catalog.dataset_options("Champions League", first.seasons[0])
    assert catalog.dataset_options("Champions League", first.seasons[0], year=2026) == {
        "source": "scores365", "league": "572", "season": 2026, "season_id": "74",
    }


def test_native_espn_year_is_used_and_not_replaced_by_the_label(fetch):
    fetch.return_value = {"pageCount": 1, "count": 1, "items": [
        {"$ref": "https://sports.core.api.espn.com/v2/sports/soccer/leagues/eng.1/seasons/2025"},
    ]}
    catalog = esd.get_catalog()
    season = catalog.list_seasons("Premier League", "espn").seasons[0]
    assert catalog.dataset_options("Premier League", season) == {"source": "espn", "league": "eng.1", "season": 2025}
    with pytest.raises(ValueError):
        catalog.dataset_options("Premier League", season, year=2024)
    with pytest.raises(ValueError):
        catalog.dataset_options("La Liga", season)


@pytest.mark.parametrize("year", [None, True, 2026.0, 999, "2026"])
def test_opaque_native_seasons_require_a_caller_year_without_parsing_labels(year):
    season = esd.SeasonInfo("scores365", "7", "132", "2026/2027")
    with pytest.raises(ValueError):
        esd.get_catalog().dataset_options("Premier League", season, year=year)


@pytest.mark.parametrize("source,native,year,source_season,options", [
    ("sofascore", "96518", None, "26/27", {"season_id": "96518"}),
    ("goaloo", "2026-2027", None, "2026-2027", {"source_season": "2026-2027"}),
    ("besoccer", "2027", 2027, None, {}),
])
def test_custom_source_selectors_preserve_native_semantics(source, native, year, source_season, options):
    entry = esd.CatalogCompetition("custom-cup", "Custom cup", (reference(source, "72"),))
    catalog = esd.FootballCatalog(competitions=[entry])
    season = esd.SeasonInfo(source, "72", native, "2026/2027", year=year, source_season=source_season)
    result = catalog.dataset_options("custom-cup", season, year=2026 if year is None else None)
    assert result == {"source": source, "league": "72", "season": 2026 if year is None else 2027, **options}


def test_unsupported_or_unreviewed_sources_fail_before_io(fetch):
    with pytest.raises(ValueError):
        esd.get_catalog().list_seasons("Champions League", "sofascore")
    entry = esd.CatalogCompetition("history", "History", (reference("transfermarkt", "CL"),))
    with pytest.raises(ValueError, match="no historical season selection"):
        esd.FootballCatalog(competitions=(entry,)).dataset_options(
            "history", esd.SeasonInfo("transfermarkt", "CL", "2026"), year=2026,
        )
    fetch.assert_not_called()


def test_catalog_document_roundtrip_preserves_review_dates_and_native_ids(tmp_path):
    catalog = esd.get_catalog()
    document = catalog.to_dict()
    assert esd.FootballCatalog.from_dict(json.loads(json.dumps(document))) == catalog
    path = catalog.save_json(tmp_path / "caller-data" / "identities.json")
    assert esd.open_catalog(path) == catalog and not list(path.parent.glob(".esd-catalog-*"))
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        catalog.save_json(path)
    assert path.read_bytes() == before


@pytest.mark.parametrize("change", ["version", "extra", "date", "entity", "references", "aliases"])
def test_catalog_documents_reject_bad_shapes_and_unknown_versions(change):
    doc = esd.get_catalog().to_dict()
    if change == "version":
        doc["format_version"] = True
    elif change == "extra":
        doc["unexpected"] = 1
    elif change == "date":
        doc["competitions"][0]["references"][0]["verified_at"] = "2026-11-07"
    elif change == "entity":
        doc["teams"].append(doc["teams"][0])
    elif change == "references":
        doc["competitions"][0]["references"] = {}
    else:
        doc["teams"][0]["aliases"] = "alias"
    with pytest.raises(ValueError):
        esd.FootballCatalog.from_dict(doc)


def test_catalog_publication_failure_cleans_staging_without_a_partial_file(tmp_path, monkeypatch):
    def fail(*args):
        raise OSError("Publication unavailable")
    monkeypatch.setattr(catalog_module.os, "link", fail)
    with pytest.raises(OSError):
        esd.get_catalog().save_json(tmp_path / "catalog.json")
    assert not list(tmp_path.iterdir())
