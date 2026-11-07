"""Fetch Liverpool's Sofascore squad and print positions, shirt numbers and contracts.

Makes network requests when executed.
"""

import datetime
import sys

import esd
from esd.exceptions import ESDException


def format_month(timestamp):
    if not timestamp:
        return "Unknown"
    try:
        return datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc).strftime("%B %Y")
    except (ValueError, OSError, OverflowError, TypeError):
        return "Unknown"


def main():
    try:
        with esd.SofascoreClient() as client:
            teams: list[esd.sofascore.Team] = client.search(
                "Liverpool", entity=esd.sofascore.EntityType.TEAM
            )

            liverpool_team = next((team for team in teams if str(team.id) == "44"), None)
            if liverpool_team is None:
                print("Liverpool FC was not found in these results.")
                return 0

            liverpool_players = client.get_team_players(liverpool_team.id)

            for player in liverpool_players:
                print("---------------------------------")
                print(f"{player.name}, position {player.position}, number {player.jersey_number}")
                date_of_birth = format_month(player.date_of_birth)
                contract_until = format_month(player.contract_until)
                print(f"Date of birth: {date_of_birth}")
                print(f"Contract until: {contract_until}")
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
