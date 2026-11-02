"""
In this example, we get the full match report (per-player statistics) of
a single match using the FBref client.

We first fetch today's matches, then pull the details of the first match
that has an FBref report, and print the home/away players.

The output will be something like:

Match: Arsenal - Chelsea

Home players:
    Player                 Min  G  A  Sh  SoT
    Bukayo Saka             90  1  0  3    2
    Martin Odegaard         90  0  1  2    1
    ...

Away players:
    Player                 Min  G  A  Sh  SoT
    Cole Palmer             90  1  0  4    2
    ...

"""

import esd

client = esd.FBrefClient(language="en")

matchs = client.get_matchs()

match = next((m for m in matchs if m.id and m.id_type == "matches"), None)
if match is None:
    print("No matches with an FBref report available today.")
    raise SystemExit

details = client.get_match_details(match.id)

print(f"Match: {match.home_team} - {match.away_team}\n")

for label, table in [("Home", details.home_players), ("Away", details.away_players)]:
    print(f"{label} players:")
    print(f"    {'Player':<25} {'Min':>4} {'G':>2} {'A':>2} {'Sh':>3} {'SoT':>3}")
    for row in table.rows[:11]:
        print(
            f"    {row.player:<25} {row.minutes:>4} {row.goals:>2} "
            f"{row.assists:>2} {row.shots:>3} {row.shots_on_target:>3}"
        )
    print()
