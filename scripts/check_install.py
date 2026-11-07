"""Offline smoke checks for an installed wheel and its optional dependencies."""

import argparse
import importlib.util
import sys
from datetime import datetime, timezone
from importlib.metadata import metadata
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extra", choices=("base", "pandas", "parquet", "full"), required=True)
    args = parser.parse_args()
    wants_pandas = args.extra in ("pandas", "full")
    wants_arrow = args.extra in ("parquet", "full")
    assert (importlib.util.find_spec("pandas") is not None) == wants_pandas
    assert (importlib.util.find_spec("pyarrow") is not None) == wants_arrow

    import esd

    assert "site-packages" in Path(esd.__file__).parts, esd.__file__
    assert metadata("EasySoccerData")["License-Expression"] == "MIT"
    assert "pandas" not in sys.modules and "pyarrow" not in sys.modules
    assert len(esd.get_dataset_capabilities()) == 9
    assert len(esd.get_discovery_capabilities()) == 9
    assert esd.get_discovery_capabilities("goaloo").seasons == "index"
    with patch("esd.discovery.get_api_json", return_value={"SeasonList": ["2024-2025"]}):
        seasons = esd.list_seasons("goaloo", 36)
        assert seasons.seasons[0].source_season == "2024-2025"
        assert seasons.seasons[0].year is None
    with patch("esd.discovery.get_text", return_value='''<select id="season" name="season"
        data-url="https://es.besoccer.com/competicion/clasificacion/champions/NNN">
        <option value="2027">2026-27</option></select>'''):
        assert esd.list_seasons("besoccer", "champions").seasons[0].year == 2027
    assert esd.get_discovery_capabilities("transfermarkt").competitions == "search_page"
    detail_payload = {"header": {"id": "1", "league": {"slug": "example.cup"}, "season": {"year": 2026},
                                 "competitions": [{"id": "1", "date": "2026-11-03T20:00:00Z", "competitors": [
                                     {"homeAway": "home", "team": {"id": "10"}},
                                     {"homeAway": "away", "team": {"id": "20"}},
                                 ]}]}, "boxscore": {"teams": [
                                     {"team": {"id": "10"}, "statistics": [{"name": "totalShots", "displayValue": "0"}]},
                                 ]}}
    with patch("esd._provider_datasets.get_api_json", return_value=detail_payload):
        details = esd.load_dataset(source="espn", league="example.cup", season=2026,
                                   tables=["match_stats"], match_ids=[1], max_match_requests=1)
    assert details.complete and details.metadata.schema_version == "3"
    assert details.match_stat_records[0].home_shots == 0 and details.match_stat_records[0].away_shots is None
    assert esd.validate_dataset(details).valid
    comparison = esd.compare_match_statistics(details, details, metrics=["home_shots", "away_shots"])
    assert comparison.rows[0].status == "equal" and comparison.rows[0].delta == 0
    assert comparison.rows[1].status == "missing_both" and comparison.rows[1].delta is None
    detail_payload["rosters"] = [{"team": {"id": "10"}, "roster": [
        {"athlete": {"id": "101"}, "starter": False, "stats": [{"name": "totalGoals", "value": 0}]},
        {"athlete": {"id": "102"}},
    ]}]
    with patch("esd._provider_datasets.get_api_json", return_value=detail_payload):
        players = esd.load_dataset(source="espn", league="example.cup", season=2026,
                                   tables=["player_match_stats"], match_ids=[1], max_match_requests=1)
    assert esd.validate_dataset(players).valid and players.complete
    assert players.lineup_records[0].starter is False and players.lineup_records[1].starter is None
    assert players.player_match_stat_records[0].goals == 0 and players.player_match_stat_records[0].minutes is None
    assert all(contract.tables for contract in esd.get_dataset_capabilities().values())
    now = datetime(2024, 8, 16, 19, tzinfo=timezone.utc)
    dataset = esd.SoccerDataset(
        esd.DatasetMetadata(
            "espn",
            "eng.1",
            2024,
            ("matches",),
            now,
            now,
            expected_tasks=("matches:1",),
            successful_tasks=("matches:1",),
        ),
        match_records=(
            esd.NormalizedMatch(
                "espn",
                match_id="1",
                competition_id="eng.1",
                home_team_id="10",
                away_team_id="20",
                kickoff=now,
                home_score=0,
                away_score=None,
            ),
        ),
    )
    assert esd.link_dataset_matches(dataset, dataset).links
    validation = esd.validate_dataset(dataset)
    assert validation.valid and not validation.errors
    assert "pandas" not in sys.modules and "pyarrow" not in sys.modules
    with TemporaryDirectory(prefix="esd-install-") as directory:
        cache = esd.ResponseCache(Path(directory) / "cache")
        cache.set("query", {"events": []})
        assert cache.get("query", ttl=60).data == {"events": []}
        if wants_arrow:
            assert esd.open_dataset(dataset.save(Path(directory) / "snapshot")) == dataset
            assert esd.open_dataset(details.save(Path(directory) / "statistics")) == details
            assert esd.open_dataset(players.save(Path(directory) / "players")) == players
        else:
            try:
                dataset.save(Path(directory) / "snapshot")
            except ImportError as exc:
                assert "EasySoccerData[parquet]" in str(exc)
            else:
                raise AssertionError("Saving without PyArrow must fail")
    if wants_pandas:
        frame = dataset.matches
        assert str(frame.home_score.dtype) == "Int64"
        assert str(frame.kickoff.dtype) == "datetime64[ns, UTC]"
        assert frame.home_score.iloc[0] == 0
        assert frame.away_score.isna().all()
        assert str(details.match_stats.home_shots.dtype) == "Int64"
        assert details.match_stats.away_shots.isna().all()
        assert str(comparison.to_dataframe().left_value.dtype) == "Float64"
        assert str(players.lineups.starter.dtype) == "boolean"
        assert players.lineups.starter.isna().sum() == 1
        assert str(players.player_match_stats.goals.dtype) == "Int64"
    else:
        assert "pandas" not in sys.modules
        try:
            comparison.to_dataframe()
        except ImportError as exc:
            assert "EasySoccerData[pandas]" in str(exc)
        else:
            raise AssertionError("Comparison DataFrames without pandas must fail")
        try:
            _ = dataset.matches
        except ImportError as exc:
            assert "EasySoccerData[pandas]" in str(exc)
        else:
            raise AssertionError("DataFrames without pandas must fail")
    print(f"Python {sys.version.split()[0]}: installed {args.extra} passed ({esd.__file__})")


if __name__ == "__main__":
    main()
