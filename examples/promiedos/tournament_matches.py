"""Fetch a Promiedos tournament and print matches in its selected stage.

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

        print(tournament.league.name, tournament.league.slug)

        stage: PromiedosTypes.Stage = tournament.current_stage()
        if stage is None or not stage.id:
            print("No selected tournament stage available.")
            return 0

        print("Current stage is", stage.name)

        matches: list[PromiedosTypes.Match] = client.get_tournament_matchs(
            tournament.league.id, stage.id
        )

        print("Matches:")

        for match in matches:
            print(match.home_team.name, "vs", match.away_team.name)
    except (ESDException, PromiedosException) as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
