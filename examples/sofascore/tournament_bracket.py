"""Fetch a selected Sofascore Champions League bracket and print its current round.

Makes network requests when executed.
"""

import sys

import esd
from esd.exceptions import ESDException


def main():
    try:
        with esd.SofascoreClient() as client:
            uefa_tournament_id = 7

            last_season_id = 61644

            brackets: list[esd.sofascore.Bracket] = client.get_tournament_brackets(
                uefa_tournament_id, last_season_id
            )

            if not brackets:
                print("No bracket available for this season.")
                return 0
            unique_bracket: esd.sofascore.Bracket = brackets[0]

            print(unique_bracket.name)

            print("Current round is", unique_bracket.current_round)

            print()

            for round in unique_bracket.rounds:
                if (
                    round.order is not None
                    and unique_bracket.current_round is not None
                    and round.order < unique_bracket.current_round
                ):
                    # Skip past rounds
                    continue

                print(
                    "Round:",
                    round.order,
                    "Description:",
                    round.description,
                    "has:",
                    len(round.blocks),
                    "matchs",
                )

                for block in round.blocks:
                    if len(block.events) == 0:
                        print("No events data available")
                        continue

                    first_match: esd.sofascore.Event = client.get_event(block.events[0])
                    home_team = first_match.home_team.name
                    away_team = first_match.away_team.name

                    print(
                        "Match:",
                        home_team,
                        block.home_team_score,
                        "-",
                        block.away_team_score,
                        away_team,
                    )

                    print()
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
