"""Save and reopen a sample snapshot offline with EasySoccerData[parquet].

This example uses no pandas and writes only inside a temporary directory.
"""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import esd


def main():
    date = datetime(2024, 8, 16, 21, tzinfo=timezone.utc)
    dataset = esd.SoccerDataset(
        metadata=esd.DatasetMetadata(
            source="espn", league="eng.1", season=2024,
            tables=("matches", "teams"), started_at=date, finished_at=date,
            calendar_dates=("2024-08-16",), successful_dates=("2024-08-16",),
            calendar_loaded=True, calendar_type="day",
        ),
        match_records=(esd.NormalizedMatch(
            source="espn", match_id="001", kickoff=date,
            home_team_id="home", home_score=0, away_score=None,
        ),),
        team_records=(esd.NormalizedTeam(source="espn", team_id="home", name="Home"),),
    )
    with TemporaryDirectory(prefix="esd-example-") as directory:
        path = dataset.save(Path(directory) / "season", format="parquet")
        restored = esd.open_dataset(path)
        assert restored == dataset
        print("Snapshot restored without network access")
        print("Calendar coverage complete:", restored.complete)
        print("Match ID:", restored.match_records[0].match_id)
        print("Scores:", restored.match_records[0].home_score, restored.match_records[0].away_score)


if __name__ == "__main__":
    main()
