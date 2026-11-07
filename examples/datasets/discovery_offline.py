"""Discover native selectors from artificial responses and reuse a temporary cache."""

from tempfile import TemporaryDirectory
from unittest.mock import patch

import esd


def main():
    with patch("esd.discovery.get_api_json", return_value={
        "leagues": [{"id": "775", "slug": "uefa.champions", "name": "UEFA Champions League"}],
    }):
        competition = esd.list_competitions("espn").competitions[0]
    print("ESPN dataset league:", competition.competition_id, "| Numeric ID:", competition.native_id)
    with patch("esd.discovery.get_api_json", return_value={
        "competitions": [{"id": 572, "sportId": 1, "seasons": [{"num": 74, "name": "2026/2027"}]}],
    }):
        season = esd.list_seasons("scores365", 572).seasons[0]
    assert season.season_id == "74" and season.year is None
    print("365Scores native season ID:", season.season_id, "| Name:", season.name)
    with TemporaryDirectory(prefix="esd-discovery-") as directory, patch(
        "esd.discovery.get_api_json", return_value={"SeasonList": ["2026-2027"]},
    ) as fetch:
        first = esd.list_seasons("goaloo", 36, cache_dir=directory)
        cached = esd.list_seasons("goaloo", 36, cache_dir=directory)
        assert fetch.call_count == 1 and cached.cached and cached.fetched_at == first.fetched_at
        assert cached.seasons[0].source_season == "2026-2027"
        esd.list_seasons("goaloo", 36, cache_dir=directory, refresh=True)
        assert fetch.call_count == 2
        print("Goaloo source_season:", cached.seasons[0].source_season, "| Original fetch preserved:", cached.cached)


if __name__ == "__main__":
    main()
