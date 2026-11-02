"""
In this example, we get today's scheduled matches using the FBref client
and print the teams, score, expected goals, round and venue.

The output will be something like:

Arsenal 2 - 1 Chelsea
    xG: 1.8 - 0.9 | Round: Premier League (Matchweek 1)
    Time: 2025-08-16 | Venue: Emirates Stadium

Liverpool 0 - 0 Man City
    xG: 1.1 - 1.4 | Round: Premier League (Matchweek 1)
    Time: 2025-08-16 | Venue: Anfield

...
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
