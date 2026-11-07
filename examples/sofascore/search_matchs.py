"""Search Sofascore for Manchester United matches and print their status and times.

Makes network requests when executed.
"""

import datetime
import sys

import esd
from esd.exceptions import ESDException


def main():
    try:
        with esd.SofascoreClient() as client:
            matchs: list[esd.sofascore.Event] = client.search(
                "Manchester United", entity=esd.sofascore.EntityType.EVENT
            )
            if not matchs:
                print("No matching fixtures available.")
                return 0

            for match in matchs:
                print(f"Match ID: {match.id}, Status: {match.status.description}")
                print(f"{match.home_team.name} vs {match.away_team.name}")
                if match.status.type == esd.sofascore.StatusType.NOT_STARTED:
                    try:
                        start_time = (
                            datetime.datetime.fromtimestamp(
                                match.start_timestamp, datetime.timezone.utc
                            )
                            if match.start_timestamp
                            else "Unknown"
                        )
                    except (ValueError, OSError, OverflowError, TypeError):
                        start_time = "Unknown"
                    print(f"Start time: {start_time}")
                print("--------------------")
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
