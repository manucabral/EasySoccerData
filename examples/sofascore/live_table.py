import esd


def clear_screen() -> None:
    print("\033[H\033[J")


def shorten(text: str | None, max_length: int) -> str:
    if not text:
        return "?"
    return text if len(text) <= max_length else text[: max_length - 3] + "..."


def update_table(client: esd.SofascoreClient) -> list[esd.SofascoreTypes.Event]:
    live_events = client.get_events(live=True)
    print("Found", len(live_events), "live events.")

    for index, event in enumerate(live_events):
        home_name = shorten(event.home_team.short_name, 15)
        away_name = shorten(event.away_team.short_name, 15)
        total_elapsed_minutes = str(event.total_elapsed_minutes) + "'"
        print(
            str(index).ljust(5),
            total_elapsed_minutes.ljust(5),
            home_name.ljust(20),
            event.home_score.current,
            "vs",
            event.away_score.current,
            away_name.ljust(20),
            event.status.description.ljust(10),
            event.tournament.name,
        )

    return live_events


def show_match(event: esd.SofascoreTypes.Event):
    print(event.home_team.name, "vs", event.away_team.name)
    print("Score:", event.home_score.current, "-", event.away_score.current)
    print("Status:", event.status.description)


def show_match_details(details: esd.SofascoreTypes.MatchStats):
    print(
        "Win probability:",
        details.win_probability.home,
        "% -",
        details.win_probability.away,
        "%",
    )

    if details.all is None:
        print("No detailed information available.")
        return

    print(
        "Ball possession:",
        details.all.match_overview.ball_possession.home_value,
        "% -",
        details.all.match_overview.ball_possession.away_value,
        "%",
    )
    print(
        "Shots on goal:",
        details.all.shots.shots_on_goal.home_value,
        "-",
        details.all.shots.shots_on_goal.away_value,
    )
    print(
        "Expected goals:",
        details.all.match_overview.expected_goals.home_value,
        "-",
        details.all.match_overview.expected_goals.away_value,
    )
    print(
        "Goalkeeper saves:",
        details.all.match_overview.goalkeeper_saves.home_value,
        "-",
        details.all.match_overview.goalkeeper_saves.away_value,
    )


if __name__ == "__main__":
    client = esd.SofascoreClient()

    while True:
        clear_screen()
        events = update_table(client)
        choice = input("Enter the index for more details (q to quit, r to refresh): ")
        if choice == "q":
            break
        if choice == "r":
            continue
        try:
            while True:
                index = int(choice)
                event = events[index]
                details = client.get_match_stats(event.id)
                clear_screen()
                show_match(event)
                show_match_details(details)
                other_choice = input(
                    "Press any key to refresh, or q to back to the list: "
                )
                if other_choice == "q":
                    break

        except ValueError:
            print("Invalid input.")
