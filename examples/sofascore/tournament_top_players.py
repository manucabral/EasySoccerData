"""Fetch Sofascore top-scorer rankings for a selected Champions League season.

Makes network requests when executed.
"""

import sys

from esd.exceptions import ESDException
from esd.sofascore import SofascoreClient


def main():
    try:
        with SofascoreClient() as client:
            uefacl_id = 7

            last_season = 61644

            top = client.get_tournament_top_players(uefacl_id, last_season)

            for index, item in enumerate(top.goals):
                print(f"{index + 1}. {item.player.name} - {item.stat.value}")
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
