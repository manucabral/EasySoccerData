"""Fetch the first live Sofascore match and print its clock, score and statistics.

Makes network requests when executed.
"""

import sys

import esd
from esd.exceptions import ESDException


def main():
    try:
        with esd.SofascoreClient() as client:
            events = client.get_events(live=True)
            if not events:
                print("No live matches available.")
                return 0

            match = events[0]

            print(f"Match ID: {match.id}, Status: {match.status.description}")

            print(f"Time: {match.current_elapsed_minutes}' (total: {match.total_elapsed_minutes}')")

            print(
                f"Board: {match.home_team.name} {match.home_score.current} - {match.away_score.current} {match.away_team.name}"
            )

            details = client.get_match_stats(match.id)
            if details is None or details.all is None:
                print("No match statistics available.")
                return 0

            print(
                f"Possession: {details.all.match_overview.ball_possession.home_value}% - {details.all.match_overview.ball_possession.away_value}%"
            )

            print(
                f"Shots: {details.all.shots.shots_on_goal.home_value} - {details.all.shots.shots_on_goal.away_value}"
            )
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
