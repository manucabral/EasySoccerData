"""Fetch today's BeSoccer matches and print teams, scores and status.

Makes network requests when executed.
"""

from __future__ import annotations

import sys

import esd
from esd.exceptions import ESDException


def main():
    try:
        client = esd.BeSoccerClient()

        matches: list[esd.besoccer.BeSoccerMatch] = client.get_matches("today")

        print(f"Found {len(matches)} matches\n")

        for match in matches[:20]:
            if match.home_team.score is not None and match.away_team.score is not None:
                score = f"{match.home_team.score} - {match.away_team.score}"
            else:
                score = "vs"
            print(
                f"[{match.competition_name}] {match.home_team.name} {score} "
                f"{match.away_team.name} ({match.time_display})"
            )
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
