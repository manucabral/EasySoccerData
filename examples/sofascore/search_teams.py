"""Search Sofascore for Liverpool teams and print IDs, names and slugs.

Makes network requests when executed.
"""

import sys

import esd
from esd.exceptions import ESDException


def main():
    try:
        with esd.SofascoreClient() as client:
            teams: list[esd.sofascore.Team] = client.search(
                "Liverpool", entity=esd.sofascore.EntityType.TEAM
            )

            for team in teams:
                print(f"{team.id}, {team.name}, {team.slug}")
                print("---------------------------")
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
