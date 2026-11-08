# Quickstart

## Query a provider client

Each provider has a client class at the top level of `esd`:

```py
import esd

espn = esd.ESPNClient()
matches = espn.get_scoreboard(league="eng.1", date="20250406")
for match in matches:
    print(f"{match.home_team.name} {match.home_team.score} - {match.away_team.score} {match.away_team.name}")

standings = espn.get_standings(league="eng.1", season=2024)
for row in standings[0].rows[:5]:
    print(row.rank, row.team.name, row.points)
```

Query player xG and shot coordinates from Understat:

```py
import esd

understat = esd.UnderstatClient()
shots = understat.get_match_shots(26602)
for shot in shots[:3]:
    print(shot.minute, shot.player, shot.result, round(shot.xG, 3))
```

## Convert client models to DataFrames

With `EasySoccerData[pandas]` installed, `esd.to_dataframe()` converts a sequence of client dataclass instances into a `pandas.DataFrame`:

```py
import esd

understat = esd.UnderstatClient()
players = understat.get_league_players("EPL", 2024)
df = esd.to_dataframe(players, convert_dtypes=True)
print(df[["player_name", "team_title", "goals", "xG"]].head())
```

## Run concurrent requests

`esd.fetch_many()` runs zero-argument callables across a thread pool:

```py
from functools import partial
import esd

espn = esd.ESPNClient()
scores365 = esd.Scores365Client()

eng_matches, esp_matches, live_games = esd.fetch_many(
    [
        partial(espn.get_scoreboard, "eng.1", "20250406"),
        partial(espn.get_scoreboard, "esp.1", "20250406"),
        scores365.get_games,
    ],
    max_workers=3,
)
```

## Download and inspect a normalized dataset

Use `esd.get_catalog()` and `esd.load_dataset()` to download normalized tables (`matches`, `teams`, `standings`, `match_stats`, `lineups`, `player_match_stats`, `match_events`, `shots`), validate them, save a Parquet snapshot, reopen a filtered subset and compute per-90 derived statistics:

```py
import esd

catalog = esd.get_catalog()

# 1. Discover seasons for UEFA Champions League on ESPN
seasons = catalog.list_seasons("uefa-champions-league", "espn", cache_dir="./cache")
season_2024 = next(s for s in seasons.seasons if s.year == 2024)
options = catalog.dataset_options("uefa-champions-league", season_2024)

# 2. Load match detail tables for a specific native match ID
dataset = esd.load_dataset(
    **options,
    tables=("matches", "teams", "match_stats", "lineups", "player_match_stats", "match_events", "shots"),
    match_ids=("704910",),
    cache_dir="./cache",
)

# 3. Validate and inspect coverage
validation = esd.validate_dataset(dataset)
assert validation.valid, validation.errors

coverage = esd.inspect_dataset_coverage(dataset, tables=("player_match_stats", "shots"))
for table in coverage.tables:
    print(table.table, table.row_count, table.task_status)

# 4. Save a Parquet snapshot and reopen a subset of tables
dataset.save("./snapshots/ucl-espn")
subset = esd.open_dataset(
    "./snapshots/ucl-espn",
    tables=("player_match_stats", "match_stats"),
    match_ids=("704910",),
)

# 5. Calculate per-90 rates and pass/shot accuracy
derived = [esd.derive_statistics(row) for row in subset.player_match_stat_records]
derived_df = esd.derived_statistics_to_dataframe(derived)
print(derived_df[["player_id", "name", "value", "status"]].head())
```
