"""Download an ESPN season snapshot. Requires EasySoccerData[pandas].

This example makes network requests when run directly. Importing it does not
download anything. Calendar coverage and failed tasks are reported explicitly.
"""

import esd


def main():
    def progress(event):
        print(f"{event.completed}/{event.total} {event.step}: {event.target} "
              f"success={event.success} matches={event.match_count}")

    dataset = esd.load_dataset(
        source="espn",
        league="eng.1",
        season=2024,
        tables=["matches", "standings"],
        on_error="collect",
        progress=progress,
    )
    print("Calendar fully downloaded:", dataset.complete)
    print("Days received:", len(dataset.metadata.successful_dates),
          "/", len(dataset.metadata.calendar_dates))
    for issue in dataset.errors:
        print(issue.step, issue.target, issue.error_type, issue.message)
    print(dataset.matches[["match_id", "kickoff", "home_team_name", "away_team_name"]])
    print(dataset.standings[["table_name", "team_name", "rank", "points"]])


if __name__ == "__main__":
    main()
