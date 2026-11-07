"""Offline persistent cache reuse and refresh. Base install, temporary files only."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import esd


def main():
    payload = {
        "events": [],
        "leagues": [
            {
                "slug": "eng.1",
                "season": {"year": 2024},
                "calendarType": "day",
                "calendar": ["2024-08-16T00:00:00Z"],
            }
        ],
    }
    with TemporaryDirectory(prefix="esd-cache-example-") as directory:
        query = {
            "source": "espn",
            "league": "eng.1",
            "season": 2024,
            "cache_dir": Path(directory) / "responses",
            "request_delay": 0,
        }
        with patch("esd.espn.service.get_api_json", return_value=payload) as fetch:
            first = esd.load_dataset(**query)
            assert first.complete and fetch.call_count == 2
            print("First download: 2 simulated source responses")
        with patch("esd.espn.service.get_api_json", side_effect=AssertionError("Unexpected HTTP")):
            resumed = esd.load_dataset(**query)
            assert resumed.complete and len(resumed.metadata.cached_tasks) == 2
            assert first.metadata.response_fetched_at == resumed.metadata.response_fetched_at
            print("Resumed download: 0 source responses; original fetch dates preserved")
        with patch("esd.espn.service.get_api_json", return_value=payload) as fetch:
            refreshed = esd.load_dataset(**query, refresh=True)
            assert refreshed.complete and fetch.call_count == 2
            assert not refreshed.metadata.cached_tasks
            print("Forced refresh: 2 simulated source responses")


if __name__ == "__main__":
    main()
