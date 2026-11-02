"""
In this example, we will get the matchs of a specific date.
Also we will print the result, xG and notes of each match using the FBref client.

The output will be something like:

Barcelona 3 - 1 Benfica
xG: 2.5 - 0.7
Notes: Leg 2 of 2. Barcelona won

Liverpool 1 - 0 Paris S-G
xG: 1.6 - 2.6
Notes: Leg 2 of 2. Paris S-G won. Paris S-G won on penalty kicks following extra time

Inter 2 - 1 Feyenoord
xG: 2.2 - 1.5
Notes: Leg 2 of 2. Inter won

....

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
