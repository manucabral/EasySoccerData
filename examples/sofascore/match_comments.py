"""Fetch Sofascore match commentary and print each entry's time and text.

Makes network requests when executed.
"""

from esd.sofascore import SofascoreClient

client = SofascoreClient()

comments = client.get_match_comments(13511924)

for comment in comments:
    print(f"{comment.time}'", comment.text)
    # see esd.sofascore.Comment for more attributes
