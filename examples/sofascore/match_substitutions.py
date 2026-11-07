"""Fetch Sofascore match incidents and print substitutions.

Makes network requests when executed.
"""

import sys

from esd.exceptions import ESDException
from esd.sofascore import IncidentType, SofascoreClient


def main():
    try:
        with SofascoreClient() as client:
            incidents = client.get_match_incidents(13511924)

            for incident in incidents:
                if incident.type != IncidentType.SUBSTITUTION:
                    continue

                print(
                    f"{incident.player_out.short_name} is substituted by {incident.player_in.short_name} at {incident.time}'"
                )
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
