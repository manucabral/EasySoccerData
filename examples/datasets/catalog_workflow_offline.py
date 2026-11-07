"""Artificial fixtures for three competitions, two sources and two seasons.

Source seasons 901/902 and match observations are artificial. The catalog IDs
are reviewed identities. No provider requests occur. --pandas and --parquet use
their independent extras; response caching and catalog JSON use the base install.
"""

import argparse
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from time import sleep
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import esd


@contextmanager
def workflow_directory():
    """Own the temporary files and retry Windows error 145 during cleanup.

    Retry only directory-not-empty errors, at most twice. Other errors and a
    repeated failure propagate rather than leaving an unnoticed cleanup failure.
    """
    temporary = TemporaryDirectory(prefix="esd-catalog-workflow-")
    try:
        yield Path(temporary.name)
    finally:
        for attempt in range(3):
            try:
                temporary.cleanup()
            except OSError as exc:
                if getattr(exc, "winerror", None) != 145 or attempt == 2:
                    raise
                sleep(0.05 * (attempt + 1))
            else:
                break


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pandas", action="store_true")
    parser.add_argument("--parquet", action="store_true")
    args = parser.parse_args(argv)
    catalog = esd.get_catalog()
    competitions = (("Champions League", "shakhtar", "sporting"),
                    ("Premier League", "arsenal", "manchester-city"),
                    ("La Liga", "barcelona", "real-madrid"))
    fixtures, selections = {}, {}
    for index, (name, home, away) in enumerate(competitions):
        for year in (2024, 2026):
            for offset, source in enumerate(("espn", "scores365")):
                identifier = str(index * 100000 + year * 10 + offset)
                league = catalog.competition(name).for_source(source).source_id
                first, second = (catalog.team(team).for_source(source).source_id for team in (home, away))
                fixtures[identifier] = (source, league, year, first, second)
                selections[name, year, source] = identifier

    def fake_fetch(url, **options):
        parsed = urlsplit(url)
        query = parse_qs(parsed.query)
        if parsed.path.endswith("/seasons"):
            return {"pageCount": 1, "count": 2, "items": [
                {"$ref": f"{parsed.scheme}://{parsed.netloc}{parsed.path}/{year}"} for year in (2024, 2026)
            ]}
        if parsed.path.endswith("/competitions/"):
            return {"competitions": [{"id": int(query["competitions"][0]), "sportId": 1,
                                       "seasons": [{"num": 901, "name": "2024/2025"}, {"num": 902, "name": "2026/2027"}]}]}
        identifier = query.get("event", query.get("games", [None]))[0]
        source, league, year, home, away = fixtures[identifier]
        if source == "espn":
            return {"header": {"id": identifier, "league": {"slug": league}, "season": {"year": year},
                               "competitions": [{"id": identifier, "date": f"{year}-11-03T20:00:00Z", "competitors": [
                                   {"homeAway": "home", "team": {"id": home}}, {"homeAway": "away", "team": {"id": away}},
                               ]}]}, "boxscore": {"teams": [{"team": {"id": home},
                                                           "statistics": [{"name": "totalShots", "displayValue": "12"}]}]}}
        return {"games": [{"id": int(identifier), "competitionId": int(league), "sportId": 1,
                           "seasonNum": 901 if year == 2024 else 902, "startTime": f"{year}-11-03T20:00:00+00:00",
                           "homeCompetitor": {"id": int(home)}, "awayCompetitor": {"id": int(away)}}],
                "actualGameStatistics": {"filterId": -1},
                "statistics": [{"id": 3, "competitorId": int(home), "value": "13"}]}

    print("Artificial fixtures and native seasons 901/902; reviewed catalog", catalog.version)
    with workflow_directory() as root, \
            patch("esd.discovery.get_api_json", side_effect=fake_fetch) as discover, \
            patch("esd._provider_datasets.get_api_json", side_effect=fake_fetch) as detail:
        restored_catalog = esd.open_catalog(catalog.save_json(root / "catalog.json"))
        assert restored_catalog == catalog
        for name, _, _ in competitions:
            for year in (2024, 2026):
                pair = []
                for source in ("espn", "scores365"):
                    seasons = catalog.list_seasons(name, source, cache_dir=root / "responses")
                    native_id = str(year) if source == "espn" else "901" if year == 2024 else "902"
                    selected = next(row for row in seasons.seasons if row.season_id == native_id)
                    options = catalog.dataset_options(name, selected, year=None if source == "espn" else year)
                    query = {**options, "match_ids": [selections[name, year, source]], "tables": ["match_stats"],
                             "max_match_requests": 1, "cache_dir": root / "responses", "request_delay": 0}
                    dataset = esd.load_dataset(**query)
                    reused = esd.load_dataset(**query)
                    assert dataset.complete and esd.validate_dataset(dataset).valid
                    assert reused.metadata.cached_tasks and reused.metadata.response_fetched_at == dataset.metadata.response_fetched_at
                    if args.parquet:
                        restored = esd.open_dataset(dataset.save(root / name / str(year) / source))
                        assert restored == dataset
                        dataset = restored
                    pair.append(dataset)
                report = esd.compare_match_statistics(*pair, identities=restored_catalog.identities(), metrics=["home_shots"])
                assert len(report.linkage.links) == len(report.differences) == 1
                assert report.rows[0].delta == 1
                print(name, year, "| Linked:", len(report.linkage.links), "| Shot difference:", report.rows[0].delta)
                if args.pandas:
                    assert str(report.to_dataframe().delta.dtype) == "Float64"
        assert discover.call_count == 6 and detail.call_count == 12
        print("Six season indexes and twelve detail responses; repeated requests reused the original cache")
        if args.parquet:
            print("Twelve snapshots restored with the saved catalog identities")


if __name__ == "__main__":
    main()
