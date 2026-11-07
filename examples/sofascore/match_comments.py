"""Fetch Sofascore match commentary and print each entry's time and text.

Makes network requests when executed.
"""

import sys

from esd.exceptions import ESDException
from esd.sofascore import SofascoreClient


def main():
    try:
        with SofascoreClient() as client:
            comments = client.get_match_comments(13511924)

            for comment in comments:
                print(f"{comment.time}'", comment.text)
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
