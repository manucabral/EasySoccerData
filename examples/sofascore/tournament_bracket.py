"""Fetch a selected Sofascore Champions League bracket and print its current round.

Makes network requests when executed.
"""

import esd


client = esd.SofascoreClient()

# Find tournament IDs with search() and season IDs with get_tournament_seasons().
uefa_tournament_id = 7
last_season_id = 61644

brackets: list[esd.sofascore.Bracket] = client.get_tournament_brackets(
    uefa_tournament_id, last_season_id
)

# Select the first bracket returned for this season.
unique_bracket: esd.sofascore.Bracket = brackets[0]

# Print the name of the bracket (e.g. "UEFA Champions League 24/25, Knockout Phase")
print(unique_bracket.name)
print("Current round is", unique_bracket.current_round)

print()

for round in unique_bracket.rounds:

    if round.order < unique_bracket.current_round:
        # Skip past rounds
        continue

    print(
        "Round:",
        round.order,
        "Description:",
        round.description,
        "has:",
        len(round.blocks),
        "matchs",
    )

    for block in round.blocks:

        if len(block.events) == 0:
            print("No events data available")
            continue

        first_match: esd.sofascore.Event = client.get_event(block.events[0])
        home_team = first_match.home_team.name
        away_team = first_match.away_team.name

        print(
            "Match:",
            home_team,
            block.home_team_score,
            "-",
            block.away_team_score,
            away_team,
        )

        print()
