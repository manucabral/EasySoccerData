# Normalized Datasets Guide

`esd.load_dataset` downloads football data from a chosen provider, normalizes it into typed dataclasses (`SCHEMA_VERSION == "6"`), tracks task-level provenance, and optionally caches raw JSON responses or writes local Parquet snapshots.

## Choose records or DataFrames

Every `SoccerDataset` stores immutable tuples of normalized dataclasses in memory without requiring `pandas` or `pyarrow`:

| Table name | Tuple attribute on `SoccerDataset` | DataFrame property (`EasySoccerData[pandas]`) | Model class |
| :--- | :--- | :--- | :--- |
| `"matches"` | `dataset.match_records` | `dataset.matches` | `NormalizedMatch` |
| `"teams"` | `dataset.team_records` | `dataset.teams` | `NormalizedTeam` |
| `"standings"` | `dataset.standing_records` | `dataset.standings` | `NormalizedStanding` |
| `"match_stats"` | `dataset.match_stat_records` | `dataset.match_stats` | `NormalizedMatchStats` |
| `"lineups"` | `dataset.lineup_records` | `dataset.lineups` | `NormalizedLineup` |
| `"player_match_stats"` | `dataset.player_match_stat_records` | `dataset.player_match_stats` | `NormalizedPlayerMatchStats` |
| `"match_events"` | `dataset.match_event_records` | `dataset.match_events` | `NormalizedMatchEvent` |
| `"shots"` | `dataset.shot_records` | `dataset.shots` | `NormalizedShot` |
| `"player_stats"` | `dataset.player_stat_records` | `dataset.player_stats` | `NormalizedPlayerStats` |
| `"players"` | `dataset.player_records` | `dataset.players` | `NormalizedPlayer` |
| `"market_values"` | `dataset.market_value_records` | `dataset.market_values` | `NormalizedMarketValue` |
| `"transfers"` | `dataset.transfer_records` | `dataset.transfers` | `NormalizedTransfer` |

```python
import esd

dataset = esd.load_dataset(
    source="espn",
    league="eng.1",
    season=2024,
    tables=("matches", "teams", "standings"),
    cache_dir="./cache",
)

# Tuple access (no optional dependencies required)
print(len(dataset.match_records), len(dataset.standing_records))

# DataFrame access (requires EasySoccerData[pandas])
matches_df = dataset.matches
```

## Provider selection

Each provider requires specific selection arguments in `load_dataset`. Inspect them programmatically with `esd.get_dataset_capabilities(source)`:

```python
import esd

# ESPN: discovers calendar dates from season year (and optional anchor_date)
espn_ds = esd.load_dataset(
    source="espn",
    league="eng.1",
    season=2024,
    tables=("matches", "teams", "standings"),
)

# Sofascore: requires native season_id
sofascore_ds = esd.load_dataset(
    source="sofascore",
    league="17",
    season=2024,
    season_id=61627,
    tables=("matches", "teams", "standings"),
)

# 365Scores: date window for matches; season_id for standings
scores365_ds = esd.load_dataset(
    source="scores365",
    league="7",
    season=2024,
    season_id=2024,
    start_date="2024-08-16",
    end_date="2024-09-01",
    tables=("matches", "teams", "standings"),
)

# Understat: season year + source_timezone for naive match kickoffs
understat_ds = esd.load_dataset(
    source="understat",
    league="EPL",
    season=2024,
    source_timezone="Europe/London",
    tables=("matches", "teams", "match_stats", "player_stats"),
)

# Goaloo: requires native source_season string and source_timezone
goaloo_ds = esd.load_dataset(
    source="goaloo",
    league="36",
    season=2024,
    source_season="2024-2025",
    source_timezone="Europe/London",
    tables=("matches", "teams", "standings"),
)

# Transfermarkt: entity loader using explicit club_ids and/or player_ids
tm_ds = esd.load_dataset(
    source="transfermarkt",
    league="GB1",
    season=2024,
    club_ids=("11",),
    player_ids=("433177",),
    tables=("teams", "players", "market_values", "transfers"),
)
```

## Discover competitions and seasons

Use `esd.get_discovery_capabilities()`, `esd.list_competitions()`, and `esd.list_seasons()` to inspect native competition and season identifiers before calling `load_dataset`:

```python
import esd

print(esd.get_discovery_capabilities("sofascore"))

# List competitions (Sofascore uses category_id; 365Scores and Transfermarkt use query)
uefa_tournaments = esd.list_competitions("sofascore", category_id=1465, cache_dir="./cache")
ucl_seasons = esd.list_seasons("sofascore", 7, cache_dir="./cache")
for season in ucl_seasons.seasons[:3]:
    print(season.season_id, season.name, season.source_season)
```

## Reviewed competition and team catalog

`esd.get_catalog()` loads the bundled `FootballCatalog` with reviewed competition and club references across providers. It converts discovered seasons directly into `load_dataset` options and builds `IdentityMap` objects for cross-provider linkage:

```python
import esd

catalog = esd.get_catalog()
ucl = catalog.competition("uefa-champions-league")
print(ucl.for_source("espn").source_id)       # "uefa.champions"
print(ucl.for_source("sofascore").source_id)  # "7"
print(ucl.for_source("scores365").source_id)  # "572"

# Discover seasons through the catalog and generate load_dataset keyword arguments
seasons = catalog.list_seasons("uefa-champions-league", "sofascore", cache_dir="./cache")
options = catalog.dataset_options("uefa-champions-league", seasons.seasons[0], year=2025)

# Extend the catalog without mutating the bundled instance
extended = catalog.with_entries(teams=[
    esd.CatalogTeam(
        canonical_id="custom-club",
        name="Custom Club",
        references=(
            esd.CatalogReference(
                source="espn",
                source_id="9999",
                source_name="Custom Club",
                verified_at=ucl.references[0].verified_at,
            ),
        ),
    ),
])
```

## Match statistics by native ID

On `espn`, `scores365`, and `sofascore`, team match statistics (`match_stats`) are downloaded for an explicit list of native `match_ids` (bounded by `max_match_requests`, default `20`):

```python
import esd

stats_ds = esd.load_dataset(
    source="sofascore",
    league="7",
    season=2024,
    season_id=61644,
    tables=("matches", "teams", "match_stats"),
    match_ids=("12173507",),
    cache_dir="./cache",
)
row = stats_ds.match_stat_records[0]
print(row.match_id, row.home_shots, row.away_shots, row.home_xg, row.away_xg)
```

## Lineups and player-match statistics

Requesting `lineups` or `player_match_stats` on `espn`, `scores365`, or `sofascore` downloads squad lists and individual match performance for the given `match_ids`:

```python
import esd

players_ds = esd.load_dataset(
    source="espn",
    league="uefa.champions",
    season=2024,
    tables=("matches", "teams", "lineups", "player_match_stats"),
    match_ids=("704910",),
    cache_dir="./cache",
)
print(len(players_ds.lineup_records), len(players_ds.player_match_stat_records))
```

## Match shots

Normalized shot tables (`shots`) are supported on `understat`, `sofascore` and `espn` when explicit `match_ids` are supplied:

- Understat (`understat-native` coordinates) and Sofascore (`sofascore-native-player` coordinates) include provider-specific `xg` (and `xgot` on Sofascore).
- ESPN (`espn-native-field` coordinates) extracts recognized shot attempts from the match summary (`xg` and `xgot` remain `None`).

```python
import esd

shots_ds = esd.load_dataset(
    source="sofascore",
    league="7",
    season=2024,
    season_id=61644,
    tables=("matches", "teams", "shots"),
    match_ids=("12173507",),
    cache_dir="./cache",
)
for shot in shots_ds.shot_records[:3]:
    print(shot.player_id, shot.minute, shot.outcome, shot.xg, shot.coordinate_system)
```

## Match events

Normalized match events (`match_events`: goals, own goals, penalties, cards, and substitutions) are available on `espn`, `scores365`, and `sofascore` by `match_ids`:

```python
import esd

events_ds = esd.load_dataset(
    source="scores365",
    league="572",
    season=2024,
    season_id=7685,
    tables=("matches", "teams", "match_events"),
    match_ids=("4217792",),
    cache_dir="./cache",
)
for event in events_ds.match_event_records:
    print(event.minute, event.event_type, event.player_id, event.related_player_id)
```

## Partial downloads

By default (`on_error="raise"`), a failed download task raises `DatasetLoadError` with partial results attached to `exc.dataset`. Pass `on_error="collect"` to continue downloading remaining tasks and inspect failures in `dataset.errors`:

```python
import esd

dataset = esd.load_dataset(
    source="espn",
    league="eng.1",
    season=2024,
    tables=("matches", "standings"),
    on_error="collect",
)
if not dataset.complete:
    for issue in dataset.errors:
        print(issue.step, issue.target, issue.error_type, issue.message)
```

## Validate a dataset

`esd.validate_dataset(dataset)` checks schema types, primary keys, score and metric ranges, date bounds, task accounting, and cross-table references without network calls:

```python
import esd

report = esd.validate_dataset(dataset)
assert report.valid, report.errors
for warning in report.warnings:
    print(warning.code, warning.table, warning.message)
```

## Field contracts and observed coverage

Use `esd.get_dataset_field_capabilities(source, table)` to inspect static column support (`"always"`, `"mapped"`, `"derived"`, or `"unavailable"`) and `esd.inspect_dataset_coverage(dataset)` to audit observed row counts, non-null rates, zeros, booleans, and task statuses:

```python
import esd

field_caps = esd.get_dataset_field_capabilities("sofascore", "player_match_stats")
print(field_caps["xg"].support, field_caps["xg"].model)

coverage = esd.inspect_dataset_coverage(dataset)
for table_cov in coverage.tables:
    print(table_cov.table, table_cov.row_count, table_cov.task_status)
```

## Response caches and snapshots

`cache_dir` stores validated raw JSON responses on disk using atomic file replacement (`ResponseCache` and `CachePolicy`), resuming interrupted downloads from cached tasks automatically. `dataset.save` and `esd.open_dataset` write and read normalized tables as Parquet files alongside a JSON manifest containing SHA-256 checksums, row counts and task provenance (requires `EasySoccerData[parquet]`).

```python
import esd

# Save to a new directory
saved_path = dataset.save("./snapshots/epl-2024")

# Reopen without network access
reopened = esd.open_dataset(saved_path)
assert reopened.metadata.schema_version == esd.SCHEMA_VERSION
```

## Read selected tables and matches

`esd.open_dataset(path, tables=..., match_ids=...)` decodes only the requested tables and filters match-scoped tables (`matches`, `match_stats`, `lineups`, `player_match_stats`, `match_events`, `shots`) to the specified native `match_ids` while still verifying SHA-256 checksums across the entire snapshot:

```python
import esd

subset = esd.open_dataset(
    "./snapshots/ucl-espn",
    tables=("player_match_stats", "match_stats"),
    match_ids=("704910",),
)
print(subset.metadata.tables)             # ('player_match_stats', 'match_stats')
print(subset.metadata.original_tables)    # full tuple of stored tables
print(subset.metadata.snapshot_match_ids) # ('704910',)
```

## Joins and match linkage

`esd.check_dataset_compatibility` and `esd.link_dataset_matches` link fixtures one-to-one across providers using mapped competition IDs, home/away team IDs, and UTC kickoff times within `tolerance_seconds` (default `300`):

```python
import esd

catalog = esd.get_catalog()
identities = catalog.identities()

compat = esd.check_dataset_compatibility(espn_ds, sofascore_ds, identities=identities)
linkage = esd.link_dataset_matches(espn_ds, sofascore_ds, identities=identities, tolerance_seconds=300)
for link in linkage.links:
    print(link.left_match_id, "<->", link.right_match_id, link.kickoff_difference_seconds)
```

## Player identity scope

Catalog identities cover competitions and clubs. Cross-provider event and player comparisons require explicit `EntityAlias("player", ...)` entries, which can be scoped by native `team_id`, `valid_from`, and `valid_until`:

> **365Scores player IDs**: On `scores365`, `lineups`, `player_match_stats`, and `match_events` use the game-level `member["id"]` as `player_id` (while preserving `athleteId` in `source_athlete_id`). Always map the normalized `player_id` in `EntityAlias("player", canonical_id, "scores365", member_id)`.

```python
import esd

identities = catalog.identities().with_aliases([
    esd.EntityAlias("player", "ucl-p1", "espn", "301234", team_id="359"),
    esd.EntityAlias("player", "ucl-p1", "sofascore", "901234", team_id="42"),
    esd.EntityAlias("player", "ucl-p1", "scores365", "1101", team_id="134"),
])
```

## Compare match statistics

`esd.compare_match_statistics` compares numeric team totals across linked matches and supports per-metric tolerances:

```python
import esd

report = esd.compare_match_statistics(
    espn_ds,
    sofascore_ds,
    identities=identities,
    metrics=("home_shots", "away_shots", "home_possession_pct", "home_xg"),
    tolerances={"home_possession_pct": 1.0},
)
for row in report.comparisons:
    print(row.metric, row.status, row.left_value, row.right_value, row.delta)
```

## Compare match events

`esd.compare_match_events` pairs goals, cards, and substitutions across linked matches using mapped player/team identities, event families, and `minute_tolerance`. When comparing against `sofascore` (which leaves `source_period` null on incidents), pass `allow_unknown_period=True`:

```python
import esd

events_report = esd.compare_match_events(
    espn_ds,
    sofascore_ds,
    identities=identities,
    minute_tolerance=1,
    allow_unknown_period=True,
)
```

## Compare lineups and player statistics

`esd.compare_match_players` compares squad membership, starter flags, jersey numbers, positions (with optional `position_aliases`), and individual `player_match_stats` metrics:

```python
import esd

players_report = esd.compare_match_players(
    espn_ds,
    sofascore_ds,
    identities=identities,
    metrics=("minutes", "goals", "shots", "passes"),
    position_aliases={("espn", "F"): "FW", ("sofascore", "F"): "FW"},
)
```

## Derived statistics

`esd.derive_statistics(record)` computes per-90 rates, `pass_accuracy_pct`, `shot_accuracy_pct`, and `xg_per_shot` from a single `NormalizedPlayerMatchStats`, `NormalizedPlayerStats`, or `NormalizedMatchStats` record without inferring missing minutes:

```python
import esd

derived = [esd.derive_statistics(row) for row in espn_ds.player_match_stat_records]
for metric in derived[0].metrics:
    if metric.status == "calculated":
        print(metric.name, round(metric.value, 3), metric.unit)

df = esd.derived_statistics_to_dataframe(derived)
```

## Integrated Champions workflow

[`examples/datasets/champions_workflow.py`](../examples/datasets/champions_workflow.py) runs the complete UEFA Champions League pipeline across `espn`, `sofascore` and `scores365`:

1. Discover seasons (`discover_seasons`) via `catalog.list_seasons` and build `load_dataset` options with `catalog.dataset_options`.
2. Download match details (`load_MatchDetails`), validate each dataset (`validate_dataset`) and inspect field coverage (`inspect_dataset_coverage`).
3. Save Parquet snapshots (`dataset.save`), reopen a filtered subset (`open_dataset(..., tables=..., match_ids=...)`) and calculate derived metrics (`derive_statistics`).
4. Link matches and compare `match_stats`, `match_events` and `lineups`/`player_match_stats` across providers (`run_champions_workflow`).

Run the offline demonstration (bundled synthetic fixtures, no network required):

```bash
python examples/datasets/champions_workflow.py
```

Or run against live provider endpoints with a persistent response cache:

```bash
python examples/datasets/champions_workflow.py --live --cache-dir ./cache/champions \
  --espn-match-id 704910 --sofascore-match-id 12173507 --scores365-match-id 4217792
```

## Provider limitations

| Provider | Selection contract | Supported normalized tables | Source constraints |
| :--- | :--- | :--- | :--- |
| `espn` | `season` year (calendar discovered from `anchor_date` or July 1); `match_ids` for detail tables | `matches`, `teams`, `standings`, `match_stats`, `lineups`, `player_match_stats`, `match_events`, `shots` | `shots` include only recognized descriptive summary attempts (`xg` and `xgot` are `None`). Detail downloads derive `teams` without `short_name`. |
| `sofascore` | Requires native numeric `season_id`; `match_ids` for detail tables | `matches`, `teams`, `standings`, `match_stats`, `lineups`, `player_match_stats`, `match_events`, `shots` | `match_events` leave `source_period` as `None` (use `allow_unknown_period=True` in `compare_match_events`). Subject to rate/WAF blocks (`403`) on some IPs; `SofascoreClient(use_playwright=True)` uses system Chrome (`channel="chrome"` or `chrome_path`) without downloading Chromium. |
| `scores365` | `start_date`/`end_date` for `matches`; native `season_id` for `standings` and detail tables | `matches`, `teams`, `standings`, `match_stats`, `lineups`, `player_match_stats`, `match_events` | No normalized `shots` table. `player_id` uses the game-level `member["id"]` (distinct from `source_athlete_id`). Anonymous placeholder `members` entries without an `"id"` are skipped. |
| `understat` | `season` year; `source_timezone` required for naive match kickoffs; `match_ids` for `shots` | `matches`, `teams`, `match_stats`, `player_stats`, `shots` | Covers 6 European leagues (`EPL`, `La_liga`, `Bundesliga`, `Serie_A`, `Ligue_1`, `RFPL`) from 2014+. No `standings`, `lineups`, `player_match_stats`, or `match_events`. |
| `fbref` | `start_date` and `end_date` required for `matches`; `season` year for `standings` | `matches`, `teams`, `standings` | Sequential rate limit enforced (~3s between requests). Frequently gated by Cloudflare anti-bot challenges on automated or cloud IPs; `FBrefClient(use_playwright=True)` uses system Chrome (`channel="chrome"` or `chrome_path`) without `playwright install`. |
| `goaloo` | Requires native `source_season` (e.g. `"2024-2025"`) and `source_timezone` | `matches`, `teams`, `standings` | No match-detail tables (`match_stats`, `lineups`, `player_match_stats`, `match_events`, `shots`). |
| `promiedos` | `start_date` and `end_date` required for `matches`; `season` year for `standings` | `matches`, `teams`, `standings` | Date-page loader only; no historical season discovery index or match-detail tables. |
| `besoccer` | `start_date` and `end_date` required for `matches`; native standings year for `standings` | `matches`, `teams`, `standings` | Season option values on multi-year seasons may use the ending year (e.g. `2025` for `2024/25`). No match-detail tables. |
| `transfermarkt` | Explicit `club_ids` and/or `player_ids` | `teams`, `players`, `market_values`, `transfers` | Entity/history loader only: `players` reflects current profiles at download time, and `market_values`/`transfers` return full career histories rather than season-filtered slices. |

## Troubleshooting

- `ValueError: Table '...' was not requested`: include the table name in the `tables=(...)` argument passed to `load_dataset` or `open_dataset`.
- `ImportError: Install EasySoccerData[pandas] ...` / `EasySoccerData[parquet]`: install the required optional extra (`pip install "EasySoccerData[full]"`), or access the built-in `*_records` tuples directly.
- `Unmatched` events when comparing against Sofascore: Sofascore incidents do not carry a native period label (`source_period is None`). Pass `allow_unknown_period=True` to `compare_match_events`.
- `Unmapped` players on 365Scores: verify that `EntityAlias("player", ..., "scores365", source_id)` uses the normalized `player_id` (`member["id"]`), not `source_athlete_id` (`athleteId`).
