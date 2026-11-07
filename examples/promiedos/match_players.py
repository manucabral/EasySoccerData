"""Fetch a Promiedos match and print goals, formations, starters and substitutes.

Makes network requests when executed.
"""

import sys

import esd
from esd.exceptions import ESDException
from esd.promiedos.exceptions import PromiedosException


def show_lineup_and_players(team: esd.promiedos.Team, lineup: esd.promiedos.LineupTeam):
    if lineup is None:
        print(f"No lineup available for {team.short_name}.")
        return
    print(f"{team.short_name} formation: {lineup.formation}")
    for player in lineup.starting:
        print(player.name, "-", player.position)
    print("Substitutes:")
    for player in lineup.bench:
        print(player.name, "-", player.position)


def main():
    try:
        client = esd.PromiedosClient()

        match = client.get_match("ediecjh")

        home = match.home_team

        away = match.away_team

        print(f"{home.short_name} {match.scores.home} - {match.scores.away} {away.short_name}")

        print(f"{match.status.name} - {match.time_to_display}")

        if len(match.tv_networks) > 0:
            print("Watch on:")
            for tv in match.tv_networks:
                print(tv.name)

        goals = home.goals + away.goals

        if len(goals) > 0:
            print("Goals: ")
            for goal in goals:
                print(f"{goal.short_name} ({goal.time})")

        show_lineup_and_players(home, match.players.lineups.home_team)

        print()

        show_lineup_and_players(away, match.players.lineups.away_team)
    except (ESDException, PromiedosException) as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
