"""Run discovery, download and validation with artificial responses and no HTTP.

Add --parquet to save, reopen and compare a temporary snapshot without pandas.
"""

import argparse
import runpy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


def responses(url, **kwargs):
    """Small artificial source payloads for this example, not recorded live results."""
    if "/search/" in url:
        return {"competitions": [{"id": 572, "name": "Example cup", "sportId": 1}]}
    if "/competitions/" in url:
        return {"competitions": [{"id": 572, "sportId": 1, "seasons": [{"num": 74, "name": "2026/2027"}]}]}
    if "/standings/" in url:
        return {"standings": [{"competitionId": 572, "seasonNum": 74, "displayName": "Example table", "rows": [
            {"competitor": {"id": 10, "name": "Home"}, "position": 1, "points": 3},
        ]}]}
    if "/games/" in url:
        return {"games": [{"id": 123, "competitionId": 572, "seasonNum": 74,
                           "startTime": "2026-11-03T20:00:00Z", "statusGroup": 4,
                           "homeCompetitor": {"id": 10, "name": "Home", "score": 1},
                           "awayCompetitor": {"id": 20, "name": "Away", "score": 0}}]}
    raise AssertionError(f"Unexpected example URL: {url}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parquet", action="store_true", help="Exercise temporary snapshot storage with [parquet]")
    args = parser.parse_args(argv)
    workflow = runpy.run_path(str(Path(__file__).with_name("discover_and_download.py")))["main"]
    with TemporaryDirectory(prefix="esd-discovery-workflow-") as directory:
        options = ["--season-id", "74", "--start-date", "2026-11-03", "--end-date", "2026-11-03",
                   "--cache-dir", str(Path(directory) / "cache")]
        if args.parquet:
            options += ["--output-dir", str(Path(directory) / "snapshot")]
        with patch("esd.discovery.get_api_json", side_effect=responses) as discover, patch(
            "esd._provider_datasets.get_api_json", side_effect=responses,
        ) as download:
            assert workflow(options) == 0
            assert discover.call_count == 2 and download.call_count == 2
        if args.parquet:
            with patch("esd.discovery.get_api_json", side_effect=AssertionError("Unexpected discovery")), patch(
                "esd._provider_datasets.get_api_json", side_effect=AssertionError("Unexpected download"),
            ):
                assert workflow(["--open-dir", str(Path(directory) / "snapshot")]) == 0
        print("Artificial discovery and download workflow completed without HTTP")


if __name__ == "__main__":
    main()
