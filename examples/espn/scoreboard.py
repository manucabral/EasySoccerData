"""Fetch an ESPN league scoreboard and print teams, scores, status and venue.

Makes network requests when executed.
"""

from __future__ import annotations

import sys

import esd
from esd.exceptions import ESDException


def main():
    try:
        client = esd.ESPNClient()

        matches: list[esd.espn.ESPNMatch] = client.get_scoreboard("arg.1", date="today")

        print(f"Found {len(matches)} matches in Liga Profesional Argentina (arg.1)\n")

        for match in matches:
            if match.home_team.score is not None and match.away_team.score is not None:
                score = f"{match.home_team.score} - {match.away_team.score}"
            else:
                score = "vs"
            print(
                f"{match.home_team.name} {score} {match.away_team.name} "
                f"({match.status_detail}) | Venue: {match.venue_name}"
            )
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
