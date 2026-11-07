"""Goaloo: league schedule + standings example."""

import sys

from esd.exceptions import ESDException
from esd.goaloo import GoalooClient
from esd.goaloo.exceptions import GoalooException


def main():
    try:
        client = GoalooClient()

        league = client.get_league(36)

        print(f"{league.name} {league.season}: {len(league.teams)} teams")

        standings = client.get_standings(36)

        print("\nStandings (top 5):")

        for row in standings[:5]:
            print(f"  {row.rank}. {row.team.name:<22} PTS {row.points}")

        matches = client.get_matches(36)

        print(f"\nMatches: {len(matches)}")

        for match in matches[:5]:
            print(
                f"  R{match.round} {match.home_team.name} "
                f"{match.home_score}-{match.away_score} {match.away_team.name}"
            )
    except (ESDException, GoalooException) as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
