"""Fetch Promiedos matches in progress and print their available statistics.

Makes network requests when executed.
"""

import esd

client = esd.PromiedosClient()
events = client.get_events()

for event in events:
    for match in event.matches:

        # ignore matches that are not in progress
        if match.status.value != esd.promiedos.MatchStatus.IN_PROGRESS:
            continue

        print(f"League name: {event.league.name} - {event.date} - {match.id}")

        print(
            f"{match.home_team.name} {match.scores.home} - {match.scores.away} {match.away_team.name}"
        )
        print(f"Status: {match.status.name} - {match.time_to_display}")

        # Fetch details for each match still in progress.
        match = client.get_match(match.id)

        print(
            f"Formations -> {match.players.lineups.home_team.formation} - {match.players.lineups.away_team.formation}"
            + "\n"
            f"Possession -> {match.stats.possession.home_value} - {match.stats.possession.away_value}"
            + "\n"
            f"Shots -> {match.stats.total_shots.home_value} - {match.stats.total_shots.away_value}"
            + "\n"
            f"Yellow/Red cards -> {match.stats.yellow_cards.home_value}/{match.stats.red_cards.home_value} - {match.stats.yellow_cards.away_value}/{match.stats.red_cards.away_value}"
        )
        print("-------------------")
