"""Fetch an FBref schedule for a selected date and print scores, xG and notes.

Makes network requests when executed.
"""

import esd

client = esd.FBrefClient(language="en")  # you can change the language.

matchs: list[esd.fbref.Match] = client.get_matchs(date="2025-03-11")

for match in matchs:
    print(
        f"{match.home_team} {match.home_score} - {match.away_score} {match.away_team}"
    )
    print(f"xG: {match.home_xg} - {match.away_xg}")
    if match.notes:
        print(f"Notes: {match.notes}")
    print()
