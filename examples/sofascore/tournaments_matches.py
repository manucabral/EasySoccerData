"""Fetch upcoming and recent Sofascore tournament matches, including a second page.

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

            events = client.get_tournament_events(uefacl_id, last_season, upcoming=True)

            print("Upcoming matches")

            for event in events:
                print(event.id, event.slug)

            events = client.get_tournament_events(uefacl_id, last_season)

            print("Last matches")

            for event in events:
                print(event.id, event.slug)

            events = client.get_tournament_events(uefacl_id, last_season, page=1)

            print("Last last matches")

            for event in events:
                print(event.id, event.slug)
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
