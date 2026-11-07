"""Fetch today's FBref schedule and print scores, xG, rounds and venues.

Makes network requests when executed.
"""

import esd

client = esd.FBrefClient(language="en")

matchs: list[esd.fbref.Match] = client.get_matchs()  # defaults to today

print(f"Found {len(matchs)} matches\n")

for match in matchs:
    print(f"{match.home_team} {match.home_score} - {match.away_score} {match.away_team}")

    line = f"    xG: {match.home_xg} - {match.away_xg}"
    if match.round:
        line += f" | Round: {match.round}"
    if match.gameweek:
        line += f" | GW: {match.gameweek}"
    print(line)

    if match.start_time:
        meta = f"    Time: {match.start_time}"
        if match.venue:
            meta += f" | Venue: {match.venue}"
        print(meta)
    print()
