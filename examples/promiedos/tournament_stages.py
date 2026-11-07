"""Fetch Promiedos tournament stages, then print matches in the first stage.

Makes network requests when executed.
"""

import sys

from esd import PromiedosClient, PromiedosTypes
from esd.exceptions import ESDException
from esd.promiedos.exceptions import PromiedosException


def main():
    try:
        client = PromiedosClient()

        tournament: PromiedosTypes.Tournament = client.get_tournament("fhc")

        stages: list[PromiedosTypes.Stage] = tournament.stages
        if not stages:
            print("No tournament stages available.")
            return 0

        for stage in stages:
            print(stage.name, stage.selected)

        stage = stages[0]

        matches = client.get_tournament_matchs(tournament.league.id, stage.id)

        for match in matches:
            print(match.home_team.name, "vs", match.away_team.name)
    except (ESDException, PromiedosException) as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
