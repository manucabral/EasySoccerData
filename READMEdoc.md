<h1 align="center">EasySoccerData</h1>

<p align="center">
<img alt="PyPI - Version" src="https://img.shields.io/pypi/v/EasySoccerData?color=00329e">
<img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dm/EasySoccerData?color=009903">
<img alt="GitHub License" src="https://img.shields.io/github/license/manucabral/easysoccerdata">
<img alt="GitHub Actions Workflow Status" src="https://img.shields.io/github/actions/workflow/status/manucabral/easysoccerdata/pylint.yml">
</p>

<p align="center">
A simple python package for extracting real-time soccer/football data from diverse online sources, providing essential statistics and insights.
</p>


> [!IMPORTANT]  
> Currently in the early development phase. Please take this into consideration.

# Installation
```
pip install EasySoccerData
```

# Usage

## Sofascore
```py
import esd

client = esd.SofascoreClient()
events = client.get_events(live=True)
for event in events:
    print(event)
```

[How to search for matches, teams, tournaments, and players](https://github.com/manucabral/EasySoccerData/blob/main/examples/sofascore/search_matchs.py)

[How to get tournament brackets](https://github.com/manucabral/EasySoccerData/blob/main/examples/sofascore/tournament_bracket.py)

[How to get live match statistics](https://github.com/manucabral/EasySoccerData/blob/main/examples/sofascore/get_live_matchs.py)


Check out [Sofascore module examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/sofascore/)

## FBRef
```py
import esd

client = esd.FBrefClient()
matchs = client.get_matchs()
for match in matchs:
    print(match)
```

Check out [FBref module examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/fbref/)

## Promiedos
```py
import esd

client = esd.PromiedosClient()
events = client.get_events()
for event in events:
    print(event)
```

Check out [Promiedos module examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/promiedos/)

## Goaloo
```py
import esd

client = esd.GoalooClient()
standings = client.get_standings(36)
```

Check out [Goaloo module examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/goaloo/)

## 365Scores
```py
import esd

client = esd.Scores365Client()
games = client.get_games("today")
```

Check out [365Scores module examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/scores365/)

## Understat
```py
import esd

client = esd.UnderstatClient()
matches = client.get_league_matches("EPL", 2024)
```

Check out [Understat module examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/understat/)

## Transfermarkt
```py
import esd

client = esd.TransfermarktClient()
player = client.get_player(28003)
```

Check out [Transfermarkt module examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/transfermarkt/)

## ESPN
```py
import esd

client = esd.ESPNClient()
matches = client.get_scoreboard("arg.1")
```

Check out [ESPN module examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/espn/)

## BeSoccer
```py
import esd

client = esd.BeSoccerClient()
matches = client.get_matches("today")
```

Check out [BeSoccer module examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/besoccer/)


## Pandas

Install with `pip install "EasySoccerData[pandas]"`. pandas remains optional
and is imported only when `esd.to_dataframe()` is called.

```py
import esd

client = esd.ESPNClient()
games = esd.to_dataframe(
    client.get_scoreboard("arg.1"),
    flatten=True,
    convert_dtypes=True,
    dtypes={"id": "string", "home_team.score": "Int64"},
    datetime_columns={"date": None},
)
for table in client.get_standings("arg.1"):
    standings = esd.to_dataframe(table.rows, flatten=True, convert_dtypes=True)
```

Flattening creates columns such as `home_team.name`; lists stay in cells.
Nullable type inference is optional. Explicit `dtypes` fix types even for
all-missing columns. Dates are converted only when declared: `None` parses
strings/datetime objects, `"s"` means Unix seconds and `"ms"` milliseconds.
Date output uses UTC and naive dates are treated as UTC. Invalid dates raise.
Missing values remain missing and zero remains zero. Provider field names are
preserved. Default calls keep nested dictionaries and normal pandas inference.

Empty input has no columns unless a schema is declared. Unknown columns in
nonempty input raise `KeyError`. Date columns belong only in `datetime_columns`.

## Common tables

`esd.normalize_match()`, `esd.normalize_team()` and `esd.normalize_standings()`
adapt supported provider models into flat `NormalizedMatch`, `NormalizedTeam`
and `NormalizedStanding` records. Existing client return types stay unchanged.
Unsupported provider models raise `TypeError`.

```py
records = [
    esd.normalize_match(match, competition_id="arg.1", season=2026)
    for match in client.get_scoreboard("arg.1")
]
matches = esd.normalized_to_dataframe(records, table="matches")
```

Understat adds match/team adapters and `normalize_match_stats()`,
`normalize_player_stats()` and `normalize_shot()`. The corresponding models are
`NormalizedMatchStats`, `NormalizedPlayerStats` and `NormalizedShot`.
Shots preserve native coordinates and player statistics retain native club-name
strings without resolving team identities.

The normalized DataFrame tables are `matches`, `teams`, `standings`,
`match_stats`, `player_stats`, `shots`, `players`, `market_values` and `transfers`. They
have fixed columns and types even when empty: nullable strings for identifiers
and names, `Int64` for counts, `Float64` for metrics and UTC nanosecond datetimes for `kickoff`.
`DataFrame.attrs` reports `schema_version="1"` and the table name.

Join entities using both `source` and their source-local ID. Adapters preserve
names without matching entities across providers. The caller-supplied `season`
label is separate from 365Scores' `source_season_id`; native competition IDs
cannot be replaced with conflicting values. Standings retain table, stage and
group context. Source status codes/text retain their original semantics.

Unknown values stay null, subject to defaults already applied by provider
parsers. Invalid or timezone-naive kickoff dates raise. Adapters require no
pandas and make no network requests; DataFrame export uses the optional extra.

## Season datasets

```py
dataset = esd.load_dataset(
    source="espn", league="eng.1", season=2024,
    tables=["matches", "standings"], on_error="collect",
)
matches = dataset.matches
teams = dataset.teams
standings = dataset.standings
```

The loader discovers ESPN's season calendar and fetches its days sequentially.
ESPN's season year `2024` selects the 2024-25 Premier League. Discovery uses
July 1 unless `anchor_date` is supplied. Day and stage-range calendars are
supported. A 0.25-second delay separates requests and HTTP retries are reused.
Repeated match IDs keep their last observation. Teams are derived from matches;
standings are an optional season snapshot, not matchday history.

`dataset.complete` reports successful coverage of the received calendar, not
proof of a finished season or an exhaustive source. `dataset.metadata` contains
the query, calendar and successful dates, schema version and UTC timestamps.
Failed tasks appear in `dataset.errors`. The default `on_error="raise"` stops
with `DatasetLoadError.dataset` holding partial results; `"collect"` continues.
`progress=callback` reports completed/total tasks and match count. Callback
exceptions propagate. Unrequested DataFrame tables raise `ValueError`.

Records remain available without pandas in
`match_records`, `team_records` and `standing_records`; DataFrame properties use
the optional pandas extra. Loading writes no files unless `cache_dir` is supplied.

`get_dataset_capabilities()` reports dataset contracts for all nine sources:

| Source | Selection and additional options |
| :--- | :--- |
| `espn` | League code and season year, optional `anchor_date` |
| `scores365` | Numeric competition ID, UTC `start_date`/`end_date` for matches; native `season_id` required for standings |
| `sofascore` | Unique tournament ID and required native `season_id`; bounded past/upcoming pagination |
| `understat` | League code and season year; explicit `source_timezone` for naive dates; optional `match_stats`, `player_stats`, `shots` and shot `match_ids` |
| `fbref` | Numeric competition ID, explicit dates, optional match xG; naive dates need `source_timezone` |
| `goaloo` | Numeric league ID, required `source_season` checked against native metadata; matches/teams/standings |
| `promiedos` | Native league ID, explicit dates and timezone for naive dates; matches/teams |
| `besoccer` | Competition slug, explicit dates for matches, year for standings |
| `transfermarkt` | Explicit `club_ids` for teams and `player_ids` for profiles, valuation history and transfer history |

365Scores validates dates and locally filters competition IDs. Its year is a
caller label and its coverage is a date range, not full-season discovery.
Sofascore validates native tournament/season IDs and requires explicit pagination
ends. Source blocks, maintenance pages and malformed responses produce errors.
Understat shot IDs must belong to completed matches in the selected season.
No loader launches a browser. FBref keeps sequential rate limits and rejects
unidentified fixtures or unrecognized HTML. Promiedos retains raw dates so
normalization does not depend on the host timezone. BeSoccer filters adjacent-day
fixtures by UTC date, or by `source_timezone` when supplied, and validates canonical
date URLs when present. Goaloo requires an explicit native season string, separate
from the year label. IANA timezones require system timezone data or `tzdata`.

Transfermarkt provides current entity snapshots and full native histories,
not historical season rosters. Its league/year are caller context; clubs must
match the native competition ID, while selected player histories are not filtered
by league/year. History dates remain source strings and monetary units are
preserved when available. It adds `player_records`, `market_value_records`,
`transfer_records` and lazy `players`, `market_values`, `transfers` DataFrames.
Entity selections and source-season metadata survive Parquet save/open.

Additional record tuples are `match_stat_records`, `player_stat_records` and
`shot_records`; lazy DataFrame properties are `match_stats`, `player_stats` and
`shots`. For non-ESPN loaders, metadata includes expected/successful tasks and
provider selection context. Progress totals can grow during discovery. `complete`
means all requested tasks succeeded, not that the source is exhaustive.

## Cross-source compatibility

`check_dataset_compatibility(left, right, identities=...)` reports schema and
identity compatibility separately, with shared tables and issues. `IdentityMap`
accepts explicit `EntityAlias(kind, canonical_id, source, source_id)` entries for
competitions and teams. No built-in entity mapping catalogue is assumed.

`link_dataset_matches(left, right, identities=..., tolerance_seconds=300)` links
mapped competitions and ordered teams with unique kickoff-time candidates on
both sides. It returns links, unmatched IDs and ambiguous IDs. It never matches
names or scores, mutates inputs or rewrites source IDs. Incomplete mappings and
missing dates leave matches unlinked. Metrics, scores and source statuses retain
their provider semantics. Both utilities work without pandas or PyArrow.

## Response caching and resume

`load_dataset(..., cache_dir="./my-cache")` persists validated dataset responses
using only the base dependencies. Repeating the query in another process resumes
the download from fresh responses. Failed or expired responses are fetched again.
Expired calendar responses discover new dates. No request delay applies to cache
hits. `DatasetProgress.cached` reports response reuse.
`metadata.response_fetched_at` preserves original UTC fetch timestamps per task,
and `metadata.cached_tasks` records which responses were reused. These metadata
also survive snapshot save/open.

`CachePolicy` configures TTLs for calendars, live/upcoming/recent/historical
matches and standings. Old pending matches keep a short TTL. `refresh=True`
bypasses caches and publishes replacements after successful validation. Newest
fetch timestamps determine which observation wins when match IDs repeat.

Sofascore pages and Understat season responses use `calendar_ttl`; completed
Understat shots use `historical_ttl`. ESPN and 365Scores daily responses use
date/status freshness; standings use `standings_ttl`.
Goaloo and other dated match loaders cap freshness at `live_ttl`; Transfermarkt
profiles/histories use `calendar_ttl`. All nine loaders can reuse validated JSON
cache entries, including HTML responses wrapped inside JSON.

The caller chooses cache and snapshot paths independently. Cache entries are
atomic JSON files under `cache_dir/responses-v1`; snapshots use
`dataset.save(path)` with the optional parquet extra. Cache corruption becomes a
miss; I/O failures raise `CacheError`. `ResponseCache(directory).clear()` removes
owned entries. Disk entries are not pruned automatically. Reusing a cached
calendar reflects its TTL; force refresh to discover source changes immediately.

## Dataset files

Install `EasySoccerData[parquet]` to save and open Parquet snapshots. The parquet
extra installs PyArrow and does not require pandas. The base installation needs
neither package. Use `EasySoccerData[full]` or
`EasySoccerData[pandas,parquet]` for both features. The full extra includes
optional runtime features; development tools remain in the dev extra.

```py
path = dataset.save("./season-snapshot", format="parquet")
restored = esd.open_dataset(path)
print(restored.match_records)
print(restored.complete, restored.errors)
```

The new destination directory contains a Parquet file per selected table and a
versioned `manifest.json`. Types, source IDs, UTC dates, nulls, query metadata,
coverage and partial-result errors are preserved. Empty tables retain their
schema. Opening validates versions, checksums, row counts and table schemas
without contacting the source. Invalid files raise `DatasetFormatError`.

Existing destinations raise `FileExistsError`. Writes are staged before the
snapshot is published. Saving and opening work without pandas; DataFrame
properties require the pandas extra. Snapshots and the persistent response
cache are independent features. Schema migrations and
snapshot overwriting are not implemented yet.

# Supported modules

| Name | Implemented |
| :---  | :---: |
| Sofascore   | ✔️ |
| FBref    | ✔️ |
| Promiedos    | ✔️ |
| Goaloo    | ✔️ |
| 365Scores    | ✔️ |
| Understat    | ✔️ |
| Transfermarkt    | ✔️ |
| ESPN    | ✔️ |
| BeSoccer    | ✔️ |
...
> Keep in mind that it is still under active development.

### Contributions
All contributions, bug reports or fixes and ideas are welcome.
