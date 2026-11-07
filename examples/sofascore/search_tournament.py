"""Search Sofascore for UEFA tournaments and fetch seasons for a selected result.

Makes network requests when executed.
"""

import sys

import esd
from esd.exceptions import ESDException


def main():
    try:
        with esd.SofascoreClient() as client:
            tournaments: list[esd.sofascore.Tournament] = client.search(
                "uefa", entity=esd.sofascore.EntityType.TOURNAMENT
            )

            for tournament in tournaments:
                print(f"{tournament.id}, {tournament.name}, {tournament.slug}")
                print("---------------------------")

            uefa = next((item for item in tournaments if str(item.id) == "7"), None)
            if uefa is None:
                print("UEFA Champions League was not found in these results.")
                return 0

            seasons: list[esd.sofascore.Season] = client.get_tournament_seasons(uefa.id)

            print("Seasons:")

            for season in seasons:
                print(f"{season.id}, {season.name}")
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
