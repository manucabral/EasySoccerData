# Datasets, cache and snapshots

`esd.load_dataset` downloads normalized tables into an immutable `SoccerDataset`, tracks task-level provenance, caches validated HTTP responses on disk and writes checksummed Parquet snapshots.

## Choose records or DataFrames

Every `SoccerDataset` holds immutable tuples of normalized dataclasses in memory without requiring `pandas` or `pyarrow`. When `EasySoccerData[pandas]` is installed, accessing the corresponding property converts the records into a typed `pandas.DataFrame`:

| Table name | Tuple attribute | DataFrame property |
| :--- | :--- | :--- |
| `"matches"` | `dataset.match_records` | `dataset.matches` |
| `"teams"` | `dataset.team_records` | `dataset.teams` |
| `"standings"` | `dataset.standing_records` | `dataset.standings` |
| `"match_stats"` | `dataset.match_stat_records` | `dataset.match_stats` |
| `"lineups"` | `dataset.lineup_records` | `dataset.lineups` |
| `"player_match_stats"` | `dataset.player_match_stat_records` | `dataset.player_match_stats` |
| `"match_events"` | `dataset.match_event_records` | `dataset.match_events` |
| `"shots"` | `dataset.shot_records` | `dataset.shots` |
| `"player_stats"` | `dataset.player_stat_records` | `dataset.player_stats` |
| `"players"` | `dataset.player_records` | `dataset.players` |
| `"market_values"` | `dataset.market_value_records` | `dataset.market_values` |
| `"transfers"` | `dataset.transfer_records` | `dataset.transfers` |

```py
import esd

dataset = esd.load_dataset(
    source="espn",
    league="eng.1",
    season=2024,
    tables=("matches", "teams", "standings"),
    cache_dir="./cache",
)

# Tuple access without optional dependencies
print(len(dataset.match_records), dataset.complete)

# DataFrame access (requires EasySoccerData[pandas])
matches_df = dataset.matches
```

## Response cache (`cache_dir` and `CachePolicy`)

Pass `cache_dir` to `load_dataset`, `list_competitions` or `list_seasons` to store validated JSON responses on disk using atomic file replacement (`ResponseCache`). Repeating a query reuses fresh cached responses and fetches only missing, expired or previously failed tasks:

```py
import esd

policy = esd.CachePolicy(
    calendar_ttl=600.0,
    live_ttl=30.0,
    recent_ttl=3600.0,
    historical_ttl=604800.0,
)

dataset = esd.load_dataset(
    source="sofascore",
    league="17",
    season=2024,
    season_id=61627,
    tables=("matches", "teams", "standings"),
    cache_dir="./cache",
    cache_policy=policy,
    refresh=False,
)
print("Cached tasks:", len(dataset.metadata.cached_tasks))
```

## Partial downloads (`on_error`)

By default (`on_error="raise"`), a failed download task raises `DatasetLoadError` with partial results attached to `exc.dataset`. Pass `on_error="collect"` to continue downloading remaining tasks and inspect failures in `dataset.errors`:

```py
import esd

dataset = esd.load_dataset(
    source="espn",
    league="eng.1",
    season=2024,
    tables=("matches", "standings"),
    on_error="collect",
    progress=lambda p: print(f"[{p.completed}/{p.total}] {p.step}:{p.target} ok={p.success}"),
)
if not dataset.complete:
    for issue in dataset.errors:
        print(issue.step, issue.target, issue.error_type, issue.message)
```

## Parquet snapshots (`save` and `open_dataset`)

With `EasySoccerData[parquet]` installed, `dataset.save(path)` writes each selected table as a Parquet file alongside a versioned JSON manifest containing metadata, errors, row counts and SHA-256 checksums.

`esd.open_dataset(path, tables=..., match_ids=...)` validates all stored checksums and optionally loads only a subset of tables or filters match-scoped tables (`matches`, `match_stats`, `lineups`, `player_match_stats`, `match_events`, `shots`) to specific native `match_ids`:

```py
import esd

# Save to a new snapshot directory
dataset.save("./snapshots/epl-2024")

# Reopen only selected tables and specific match IDs without network access
subset = esd.open_dataset(
    "./snapshots/epl-2024",
    tables=("matches",),
    match_ids=("704279",),
)
print(subset.metadata.tables)             # ('matches',)
print(subset.metadata.original_tables)    # ('matches', 'teams', 'standings')
print(subset.metadata.snapshot_match_ids) # ('704279',)
```
