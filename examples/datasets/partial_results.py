"""Offline demonstration of strict and collected partial results. Base install."""

from unittest.mock import patch

import esd
from esd.espn.types import ESPNMatch, ESPNSeasonCalendar, ESPNTeam


def demonstrate(on_error):
    # Simulate a good day, a blocked day and another good day.
    with patch("esd.datasets.ESPNClient") as factory:
        client = factory.return_value
        client.get_season_calendar.return_value = ESPNSeasonCalendar(
            "eng.1",
            2024,
            ("2024-08-16", "2024-08-17", "2024-08-18"),
        )
        client.get_scoreboard.side_effect = [
            [
                ESPNMatch(
                    id="example-1",
                    date="2024-08-16T19:00:00Z",
                    home_team=ESPNTeam(id="home", name="Home", score=0),
                    away_team=ESPNTeam(id="away", name="Away", score=1),
                )
            ],
            esd.SourceBlocked("Simulated source block"),
            [ESPNMatch(id="example-2", date="2024-08-18T19:00:00Z")],
        ]
        try:
            result = esd.load_dataset(
                source="espn", league="eng.1", season=2024, on_error=on_error, request_delay=0
            )
        except esd.DatasetLoadError as exc:
            result = exc.dataset
            print("Strict mode stopped; partial records are attached to the exception")
    assert not result.complete
    assert len(result.match_records) == (1 if on_error == "raise" else 2)
    assert "2024-08-16" in result.metadata.successful_dates
    assert ("2024-08-18" in result.metadata.successful_dates) == (on_error == "collect")
    print(on_error, "matches:", len(result.match_records), "complete:", result.complete)
    for issue in result.errors:
        print(issue.step, issue.target, issue.error_type, issue.message)
    return result


def main():
    demonstrate("raise")
    demonstrate("collect")


if __name__ == "__main__":
    main()
