"""Search 365Scores for competitions, teams and players.

Makes network requests when executed.
"""

from __future__ import annotations

import sys

import esd
from esd.exceptions import ESDException


def main():
    try:
        client = esd.Scores365Client()

        result: esd.scores365.SearchResult = client.search("River Plate")

        print("Competitions:")

        for comp in result.competitions[:5]:
            print(f"  [{comp.id}] {comp.name}")

        print("\nTeams:")

        for team in result.competitors[:5]:
            print(f"  [{team.id}] {team.name}")

        print("\nAthletes:")

        for athlete in result.athletes[:5]:
            print(f"  [{athlete.id}] {athlete.name}")
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
