"""Fetch shots for a Sofascore match and print player, xG, body part and minute.

Makes network requests when executed.
"""

import sys

from esd import SofascoreClient, SofascoreTypes
from esd.exceptions import ESDException


def main():
    try:
        with SofascoreClient() as client:
            match_id = 13511931

            shots: list[SofascoreTypes.Shot] = client.get_match_shots(match_id)

            for shot in shots:
                print(shot.player.short_name, shot.xg, shot.xg_got, shot.body_part, shot.time)
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
