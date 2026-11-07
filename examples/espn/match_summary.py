"""Fetch an ESPN match summary and print team statistics, players and events.

Makes network requests when executed.
"""

from __future__ import annotations

import sys

import esd
from esd.exceptions import ESDException


def main():
    try:
        client = esd.ESPNClient()

        matches = client.get_scoreboard("arg.1", date="today")

        if not matches:
            print("No matches on today's arg.1 scoreboard.")
            return 0

        summary: esd.espn.ESPNMatchSummary = client.get_match_summary(matches[0].id, league="arg.1")

        print(
            f"Match: {summary.home_team.name} {summary.home_team.score} - "
            f"{summary.away_team.score} {summary.away_team.name}"
        )

        print(f"Venue: {summary.venue_name}\n")

        if summary.home_stats:
            print("Home Stats:")
            for stat in summary.home_stats[:8]:
                print(f"  {stat.label}: {stat.value}")

        if summary.key_events:
            print("\nKey Events:")
            for ev in summary.key_events:
                print(f"  {ev.clock_display} [{ev.type_text}] {ev.text}")
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
