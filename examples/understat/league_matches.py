"""Fetch Understat league matches and print scores, kickoff strings and xG.

Makes network requests when executed.
"""

from __future__ import annotations

import sys

import esd
from esd.exceptions import ESDException


def main():
    try:
        client = esd.UnderstatClient()

        matches: list[esd.understat.UnderstatMatch] = client.get_league_matches("EPL", 2024)

        print(f"Found {len(matches)} matches in EPL 2024\n")

        for match in matches[:15]:
            if match.is_result and match.home_xg is not None and match.away_xg is not None:
                print(
                    f"{match.datetime} | {match.home_team} {match.home_goals} - "
                    f"{match.away_goals} {match.away_team} "
                    f"(xG: {match.home_xg:.2f} - {match.away_xg:.2f})"
                )
            else:
                print(f"{match.datetime} | {match.home_team} vs {match.away_team}")
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
