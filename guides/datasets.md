# Dataset guide

This guide describes the unreleased 0.2.0 source checkout. Run commands from
the repository root after `python -m pip install -e .`. The base installation
returns records. Add pandas for DataFrames or PyArrow for Parquet files.

## Reviewed competition and team catalog

`get_catalog()` reads bundled identities without HTTP, pandas or PyArrow. The
version `2026-11-08.1` covers five competitions and 96 reviewed team identities
from ESPN, 365Scores and Sofascore. References retain their source URLs and
review dates. New references were checked on November 8, 2026 against each
provider's native league/team responses or public team pages.
This is a sample of identities, not a full list of leagues, season participants
or historical squads. A reviewed ID does not establish current source availability.

```py
import esd

catalog = esd.get_catalog()
print(catalog.version)
competition = catalog.competition("Champions League")
print(competition.for_source("espn").source_id)       # uefa.champions
print(competition.for_source("espn").native_id)       # 775
print(competition.for_source("scores365").source_id)  # 572
team = catalog.team("FC Barcelona")
print(team.for_source("espn").source_id)              # 83
print(team.for_source("scores365").source_id)         # 132
```

| Catalog competition | ESPN dataset selector | ESPN numeric ID | 365Scores ID | Sofascore ID |
| :--- | :--- | :--- | :--- | :--- |
| Champions League | `uefa.champions` | `775` | `572` | `7` |
| Premier League | `eng.1` | `700` | `7` | `17` |
| La Liga | `esp.1` | `740` | `11` | `8` |
| Bundesliga | `ger.1` | `720` | `25` | `35` |
| Serie A | `ita.1` | `730` | `17` | `23` |

Lookups use canonical IDs, names and declared aliases, ignoring case and
whitespace. They do not use fuzzy matching or treat an arbitrary native ID as a
name. Unknown names and unreviewed provider references raise `ValueError` before
network access. Other providers remain available through their existing clients,
discovery and dataset APIs, or through caller-reviewed catalog extensions.

### Choose native seasons

Season discovery is a separate, explicit source request. Cache paths, refresh,
source errors and original fetch timestamps follow the existing discovery API:

```py
seasons = catalog.list_seasons("Champions League", "espn", cache_dir="./my-data/responses")
for row in seasons.seasons:
    print(row.season_id, row.name, row.year, row.source_season)
```

Select an exact returned `SeasonInfo`. `dataset_options()` returns keyword
arguments for `load_dataset()` without making a request. For ESPN, it uses the
reported native year. For 365Scores/Sofascore, the caller supplies a year label
and the native season ID remains separate. No year is inferred from a name such
as `2026/2027`:

```py
selected = next(row for row in seasons.seasons if row.season_id == "2026")
options = catalog.dataset_options("Champions League", selected)
dataset = esd.load_dataset(
    **options, match_ids=[401915310], tables=["match_stats"],
    max_match_requests=1, cache_dir="./my-data/responses",
)
```

The above match ID was checked with the ESPN native year `2026`; select your
own returned season and match IDs for a different query. For 365Scores, query
its seasons separately and pass `year=2026` to `dataset_options()` when choosing
an observed native season for that caller label. A missing history entry is not
filled in or inferred. During the November 7, 2026 check, 365Scores returned only
its current season in these competition indexes. An older Champions League
date also failed to return an explicit games list. These source limits remain
errors/limited listings rather than successful empty historical coverage.

The bounded live check linked all 17 fixtures in the selected 2026 dates across
these three competitions. An older LaLiga date returned three fixtures per
source, with one linked match and two unresolved matches because the sample
lacks some historical team identities. The older Premier League request to
365Scores timed out. Twelve snapshots, including partial results and their
errors, reopened unchanged. These checks describe the selected dates and
environment, not complete source history or an availability guarantee.

For caller-reviewed extensions, Goaloo keeps its exact `source_season` and
BeSoccer its explicit selector year. Transfermarkt season discovery does not
make current profiles or unfiltered histories season-specific;
`dataset_options()` rejects that historical selection.

### Link and extend identities

Use the catalog explicitly with the existing linker or statistics comparator:

```py
identities = catalog.identities()
# left/right are datasets you have downloaded or opened.
# links = esd.link_dataset_matches(left, right, identities=identities)
# report = esd.compare_match_statistics(left, right, identities=identities)
```

Native dataset IDs remain unchanged. An unmapped team stays unresolved. The
catalog does not establish common metric definitions or link player identities.
Two sources can use the same numeric ID for different teams, so IDs retain their
source namespace.

`FootballCatalog`, `CatalogCompetition`, `CatalogTeam` and `CatalogReference`
allow applications to maintain their own reviewed entries. Each reference
requires a source ID, evidence URL and aware review timestamp. For example, add
a local lookup alias to an existing reviewed competition:

```py
from dataclasses import replace

champions = catalog.competition("Champions League")
custom = catalog.with_entries(
    competitions=[replace(champions, aliases=(*champions.aliases, "My Champions"))],
    version="my-project-1",
)
assert custom.competition("My Champions") == custom.competition("Champions League")
path = custom.save_json("./my-data/catalog-1.json")
restored = esd.open_catalog(path)
assert restored == custom
```

Add new entities or provider references with reviewed IDs. Extensions leave the
original catalog unchanged and reject conflicting names, source IDs or review
metadata. Deliberate replacements require constructing a new complete catalog.
`save_json()` stages a complete document and publishes a new file without
overwriting existing paths. JSON format version `1` is independent of normalized
dataset schema version `6`. Saving the catalog with your snapshots preserves
the particular identities used for later comparisons. Catalog JSON needs no
optional dependencies; dataset snapshots still require `[parquet]`.

Run `python examples/datasets/catalog.py --list` for local selections, or
`python examples/datasets/catalog.py --competition "Premier League" --source espn --seasons`
for an explicit season query. The artificial
`catalog_workflow_offline.py` example exercises all three competitions in two
seasons, linking records and retaining cached fetch dates. Optional `--parquet`
verifies twelve dataset snapshots using a saved catalog; `--pandas` independently
checks report DataFrames. Its source seasons and match observations are fixtures,
not claims about live historical coverage.

## Field contracts and observed coverage

Table support does not mean that every column is populated. Query the current
dataset adapter without downloading anything or importing optional packages:

```py
fields = esd.get_dataset_field_capabilities("espn", "shots")
assert fields["x"].support == "mapped"
assert fields["x"].coordinate_system == "espn-native-field"
assert fields["xg"].support == "unavailable"

players = esd.get_dataset_field_capabilities("sofascore", "player_match_stats")
assert players["minutes"].support == "mapped"
assert players["shots"].support == "unavailable"
```

The returned dictionary contains every normalized column for that supported
source/table. Its entries are immutable. Changing the dictionary does not
change later lookups. Unsupported pairs and unknown selections raise `ValueError`.
The contracts cover the implemented dataset tables of all nine providers.

| `support` | Meaning |
| :--- | :--- |
| `mapped` | The current adapter has a mapping for this column; individual responses can omit it |
| `context` | The value uses query/verified match context or a provider/convention label |
| `derived` | An explicit normalization rule produces it, such as a side flag or response position |
| `unavailable` | The current dataset adapter leaves this column null |

`dtype` describes nullable DataFrame export without importing pandas. Units
identify minutes, seconds and percentage-point possession where relevant.
`model` labels provider-specific metrics without asserting a shared definition
or model version. `coordinate_system` retains native conventions. These
contracts describe `load_dataset()`, not every individual client method or
every league/season. For example, ESPN season team rows may carry short names,
while its explicit detail loader derives teams from matches without that field.

Inspect the actual normalized rows separately:

```py
# dataset is a dataset you downloaded or opened; no new source query occurs.
report = esd.inspect_dataset_coverage(dataset)
for row in report.fields:
    print(row.table, row.field, row.capability.support,
          row.present_count, row.missing_count, row.zero_count)
for table in report.tables:
    print(table.table, table.row_count, table.task_status, table.task_keys)
document = report.to_dict()        # JSON-compatible, no optional packages
# frame = report.to_dataframe()    # optional [pandas]
```

`present_count` counts non-null values in existing rows. `missing_count` counts
`None`; a numeric zero is present and also increments `zero_count`. Boolean
`False` increments `false_count`, never numeric zero. `true_count` is separate.
`blank_count` identifies blank/whitespace-only strings that are still non-null.
Counters for unrelated types are null. `present_ratio` is a fraction from zero
to one and remains null when the table has no rows. Field `status` is `empty`,
`missing`, `partial` or `populated`, independently of download outcomes.

Counts do not prove raw source observations. Existing parser defaults can
already have filled missing source fields with zeros or empty strings, and
normalization cannot recover their absence. `unmapped_values=True` identifies
non-null values in a column the current adapter does not populate; caller
enrichment or an older adapter may account for them. These values are retained.
The inspector does not infer omitted players, matches or attempts.

Each selected table lists its relevant task keys and `task_status`: `complete`,
`partial`, `failed`, `pending` or `unknown`. A successful empty table has zero
rows and complete tasks; a failed table is not treated as an empty success.
Missing task evidence stays unknown. Sofascore context reads are retained as
prerequisites. If some explicitly requested match IDs have no relevant detail
task, table coverage remains partial rather than reporting a complete task set.
Sofascore context reads cannot establish successful lineup, statistics or shot reads.
Understat shot coverage also includes its required season discovery. ESPN
season calendars use their saved flags/dates when no explicit task list exists.

The report retains all dataset tasks, original response dates, cached flags,
download errors, query metadata and validation warnings. Table filtering only
limits the inspected rows; it does not turn an incomplete overall download
into a complete one or discard errors from other tables. Invalid datasets raise
`ValueError` rather than producing misleading counts.

Coverage JSON format `1` is a derived report, independent of normalized schema
`6`. It changes no dataset rows, selected tables, source timestamps or files.
Recompute it after `open_dataset()` to inspect a saved snapshot. Saving/opening
the source still needs `[parquet]`; inspection itself needs no extras, and the
optional report DataFrame uses nullable counts, flags and ratios.

Run `python examples/datasets/coverage.py --source espn --table shots` for a
local contract query. `--open-dir PATH --table shots` inspects a source
snapshot without HTTP. `--output-json PATH` saves a new report file without
overwriting existing files. `coverage_offline.py` demonstrates artificial
missing values, zero/False counters, cache dates and a partial download; its
`--pandas` and `--parquet` flags exercise the independent extras.

## Player identity scope

Player aliases can restrict an equivalence to a native team and a time window.
The team ID belongs to the same source as the player ID. `valid_from` is
inclusive and `valid_until` exclusive. Supply aware timestamps. These are
caller-reviewed scopes, not transfer dates inferred from names or rosters.

```py
import json
from datetime import datetime, timezone

boundary = datetime(2026, 7, 1, tzinfo=timezone.utc)
identities = esd.IdentityMap([
    esd.EntityAlias("player", "example-person", "espn", "001",
                    team_id="old-native-team", valid_until=boundary),
    esd.EntityAlias("player", "example-person", "espn", "001",
                    team_id="new-native-team", valid_from=boundary),
])
decision = identities.lookup("player", "espn", "001", team_id="new-native-team", at=boundary)
assert decision.canonical_id == "example-person" and decision.status == "resolved"
restored = esd.IdentityMap.from_dict(json.loads(json.dumps(identities.to_dict())))
assert restored.aliases == identities.aliases
```

`lookup()` distinguishes `unmapped`, `context_required` and `out_of_scope`.
`resolve()` returns the canonical ID or `None`. Missing team/time context never
satisfies a scoped alias. Conflicting identities with overlapping scopes are
rejected, while disjoint team/date scopes can describe reused native IDs.
Optional `source_url` and `verified_at` retain caller evidence. URLs must use
HTTP(S) without embedded credentials, and review timestamps must be aware.

The event and player comparators supply each original match kickoff and native
player team. Own-goal beneficiaries do not establish player membership: scoped
event identity requires a selected lineup for that player in this case.
Reports retain the supplied `identity_aliases`, including scope/evidence.
Same-source comparisons continue using native IDs directly. Cross-source
comparisons never fall back to names, shirt numbers or the separate 365Scores
athlete ID. Unknown scopes remain unresolved with an explicit reason.

Identity JSON format `1` preserves ISO timestamps. `IdentityMap.from_dict()`
also reads the older list of four-field aliases. The Champions comparison and
workflow examples accept both formats and save the versioned document beside
snapshots. Run `python examples/datasets/scoped_players_offline.py` for an
artificial transfer boundary without HTTP or optional packages.

## Choose records or DataFrames

Clients return each provider's models. `load_dataset()` returns normalized,
immutable record tuples plus selection/coverage metadata. Neither requires pandas.
With `python -m pip install -e ".[pandas]"`, the corresponding properties return
DataFrames with fixed columns and nullable types, including empty tables.

| Table | Records without pandas | DataFrame property | Available sources |
| :--- | :--- | :--- | :--- |
| Matches | `match_records` | `matches` | All except Transfermarkt |
| Teams | `team_records` | `teams` | All nine |
| Standings | `standing_records` | `standings` | ESPN, 365Scores, Sofascore, Goaloo, BeSoccer |
| Match metrics | `match_stat_records` | `match_stats` | ESPN, 365Scores, Sofascore, FBref, Understat |
| Lineups | `lineup_records` | `lineups` | ESPN, 365Scores, Sofascore |
| Player-match statistics | `player_match_stat_records` | `player_match_stats` | ESPN, 365Scores, Sofascore |
| Player-season statistics | `player_stat_records` | `player_stats` | Understat |
| Shots | `shot_records` | `shots` | Understat, Sofascore, ESPN recognized attempts |
| Current player profiles | `player_records` | `players` | Transfermarkt |
| Valuation history | `market_value_records` | `market_values` | Transfermarkt |
| Transfer history | `transfer_records` | `transfers` | Transfermarkt |

Request tables explicitly. Matches also request teams automatically. Goaloo can
load its native team list on its own; Transfermarkt teams require explicit clubs.
Other loaders derive teams from matches. An unrequested DataFrame property raises
`ValueError`, even if its record tuple happens to be empty.

```py
import esd

dataset = esd.load_dataset(
    source="espn", league="eng.1", season=2024,
    tables=["matches", "standings"], on_error="collect",
)
for match in dataset.match_records[:5]:
    print(match.match_id, match.kickoff, match.home_score, match.away_score)

# Optional pandas access:
# print(dataset.matches[["match_id", "kickoff", "home_score", "away_score"]])
```

`None` represents an unknown score. Zero is a recorded score. Check the source
status to determine whether a match has finished. Status fields retain native
source codes and text.

## Match statistics by native ID

ESPN, 365Scores and Sofascore support an optional `match_stats` detail selection.
Supply the exact native `match_ids`; this path also returns their matches and
teams, without fetching a calendar, date range or season pagination:

```py
import esd

dataset = esd.load_dataset(
    source="espn", league="uefa.champions", season=2026,
    tables=["match_stats"], match_ids=[401915311], max_match_requests=1,
    cache_dir="./my-data/match-responses", on_error="collect",
)
for row in dataset.match_stat_records:
    print(row.match_id, row.home_shots, row.away_shots, row.home_possession_pct)
# Optional pandas: print(dataset.match_stats)
```

The ESPN ID in this example was verified on November 7, 2026. Choose match IDs
from your provider. 365Scores and Sofascore additionally require their native
`season_id`, separate from the caller `season` label. Event/competition/season
identity is checked before publishing the response cache. Team statistics use
native team IDs; ESPN group order does not determine home and away.

`max_match_requests` defaults to `20` and bounds endpoint reads before normal
transport retries. ESPN and 365Scores cost one read per unique ID; Sofascore
needs an event response and a statistics response, so each ID costs two reads.
Selections exceeding the budget fail before HTTP. Repeated IDs are fetched once.
Cache hits count toward this conservative preflight budget. Details use
`CachePolicy.live_ttl`, including completed matches, and support `refresh`.

`metadata.coverage_scope="match_ids"` and `requested_match_ids` describe only the
chosen matches. `complete=True` means their tasks succeeded, not that a season
was downloaded. Failed tasks retain their IDs and source errors under
`on_error="collect"`. This detail selection cannot be combined with date ranges,
calendar anchors, standings or other entity filters; load those selections
separately. Ordinary match/season downloads make no extra statistics requests.

These fields use the source's whole-match totals, including extra time where
the provider includes it. `source_period` retains `boxscore` (ESPN), `-1`
(365Scores, null when its selector metadata is absent) or `ALL` (Sofascore).
Sofascore's half-period values are not added to
`ALL` or used to fill an absent total period. Its explicit empty statistics list
returns null metrics; a missing list or malformed response raises instead.

| Metric stem, prefixed by `home_` or `away_` | ESPN native name | 365Scores native ID | Sofascore native key |
| :--- | :--- | :--- | :--- |
| `possession_pct` | `possessionPct` | `10` | `ballPossession` |
| `shots` | `totalShots` | `3` | `totalShotsOnGoal` |
| `shots_on_target` | `shotsOnTarget` | `4` | `shotsOnGoal` |
| `corners` | `wonCorners` | `8` | `cornerKicks` |
| `fouls` | `foulsCommitted` | `12` | `fouls` |
| `offsides` | `offsides` | `9` | `offsides` |
| `yellow_cards` | `yellowCards` | `1` | `yellowCards` |
| `red_cards` | `redCards` | `2` | `redCards` |
| `saves` | `saves` | `23` | `goalkeeperSaves` |
| `passes` | `totalPasses` | `21` | `passes` |
| `accurate_passes` | `accuratePasses` | `19` | `accuratePasses` |
| `xg` | Not mapped by this adapter | `76` | `expectedGoals` |

Possession uses percentage points from `0` to `100`. Counts use nullable integers
and xG uses nullable floats. Missing metrics remain `None`, and reported zeros
remain zero. 365Scores' `valuePercentage` can represent a team's share of another
metric, so it is not used as possession. Unknown native keys are not guessed from
localized labels. Equal column names do not establish identical collection rules
or xG models across sources. FBref and Understat retain their existing xG/forecast
fields; the new count columns remain null for those adapters.

`examples/datasets/match_statistics.py` provides live, cache and snapshot options.
`match_statistics_offline.py` uses artificial responses and supports independent
`--pandas` and `--parquet` flags. HTTP blocks remain source failures; no browser
is launched. ESPN and 365Scores detail responses were verified live on November
7, 2026. Sofascore's adapter has offline contract tests, but event/statistics
requests returned HTTP 403 from that verification environment.

## Lineups and player-match statistics

`lineups` contains one row per listed player, including unused substitutes.
`player_match_stats` contains the source's observed individual metrics for that
match. Selecting player match statistics also selects lineups, matches and
teams. Add `match_stats` to get team totals in the same dataset:

```py
dataset = esd.load_dataset(
    source="espn", league="uefa.champions", season=2026,
    tables=["lineups", "player_match_stats", "match_stats"],
    match_ids=[401915310], max_match_requests=1,
)
for player in dataset.lineup_records:
    print(player.match_id, player.team_id, player.player_id,
          player.player_name, player.starter, player.formation)
for row in dataset.player_match_stat_records:
    print(row.player_id, row.minutes, row.goals, row.assists)
# Optional: dataset.lineups and dataset.player_match_stats require [pandas].
```

ESPN uses its native season year. 365Scores and Sofascore require native
`season_id`, separately from the caller year label. All three use explicit
`match_ids`, without calendar discovery or season pagination. Endpoint budgets
are checked before any source request, after deduplicating IDs:

| Source | Lineups and/or player-match statistics | With team `match_stats` |
| :--- | :--- | :--- |
| ESPN | 1 summary per ID | Same summary, 1 read total |
| 365Scores | 1 game detail per ID | Detail plus statistics, 2 reads total |
| Sofascore | Event context plus lineup, 2 reads per ID | Adds statistics, 3 reads total |

Counts are before transport retries. `max_match_requests` defaults to `20`.
The existing match-statistics-only path keeps its previous request cost.
Do not combine explicit detail selections with standings, date ranges or entity
filters. Other providers reject these new tables before network access;
`get_dataset_capabilities()` reports the implemented scope for all nine sources.

Lineup keys are `(source, match_id, team_id, player_id)`. ESPN uses its athlete
ID and Sofascore its player ID. For 365Scores, `player_id` is the lineup member
ID and `source_athlete_id` retains the separate athlete ID when reported. Member
IDs are not treated as a person identifier across clubs. Player identity linkage
across providers is not implemented. Names and jersey numbers are display values.

`starter`, `captain` and `confirmed` are nullable booleans. A missing flag is not
`False`. Sofascore supplies an explicit confirmation flag. 365Scores' localized
lineup status remains in `source_lineup_status` without guessing confirmation
from its text. Positions and formations retain native labels. 365Scores missing
and management roles and Sofascore's `missingPlayers` are excluded from lineups.

| Metric | ESPN roster native key | 365Scores player-stat type | Sofascore player-stat key |
| :--- | :--- | :--- | :--- |
| `minutes` | Not mapped | `30`, including the native trailing apostrophe | `minutesPlayed` |
| `goals`, `assists` | `totalGoals`, `goalAssists` | `27`, `26` | `goals`, `goalAssist` |
| `shots`, `shots_on_target` | `totalShots`, `shotsOnTarget` | `3`, `4` | Total not inferred; `onTargetScoringAttempt` |
| `passes`, `accurate_passes` | Not mapped | `19`: explicit completed/attempted pair, or completed count alone | `totalPass`, `accuratePass` |
| `xg`, `xa` | Not mapped | `76`, `78` | `expectedGoals`, `expectedAssists` |
| `source_rating` | Not mapped | Lineup member `ranking` | `rating` |

The adapter also maps reported appearances, own goals, cards, fouls, offsides,
saves and goals conceded where available. 365Scores/Sofascore add reported
touches, key passes and interceptions; Sofascore adds tackles. Not every source
supplies every field. Source rating and xG/xA models are not harmonized.
365Scores' numeric rating sentinel `-1` becomes null; reported zero stays zero.

Missing values remain `None`. No 90-minute duration, appearance, unused-bench
zero or shot total is inferred. A source can explicitly report zero statistics
for an unused substitute; those observations are retained. A player with no
statistics observation has a lineup row without a manufactured statistics row.
Player-season aggregates remain in Understat's separate `player_stats` table.

ESPN's shared response uses task key `match_details:<ID>`. 365Scores uses
`lineups:<ID>` for its game detail and `match_stats:<ID>` when selected.
Sofascore uses `match:<ID>`, `lineups:<ID>` and optionally `match_stats:<ID>`.
`response_fetched_at` and `cached_tasks` retain the original observations for
those requests. A failed source remains an explicit error, not an empty roster.
With `on_error="collect"`, valid independent tasks remain available and
`complete` stays false. A successful empty source lineup is allowed and does
not establish complete real-world squad coverage.

`validate_dataset()` checks native match selection, duplicate player keys,
team membership, nullable flag types and numeric constraints. DataFrame flags
use pandas `boolean`, counts `Int64` and floating metrics `Float64`, including
empty tables. Snapshot save/open requires only PyArrow and retains both tables.
The public `normalize_match_players(payload, match=verified_match)` adapter
also works without downloading. It accepts raw source responses to preserve
missing flags that older provider models may already have defaulted.
Sofascore lineup responses can omit their event ID; obtain them from the supplied
match's lineup URL. `include_statistics=False` skips unselected metrics.

The [live CLI](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/datasets/match_players.py)
supports caller-selected cache/snapshot paths and offline reads. Its
[offline example](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/datasets/match_players_offline.py)
uses artificial records, with independent `--pandas` and `--parquet` flags.
On November 7, 2026, the Champions League Shakhtarâ€“Sporting query returned
46 listed players from ESPN and 365Scores, with 46 and 31 player-statistic rows
respectively. Both snapshot round trips were verified. These are observations
from that check. Sofascore's lineup path has offline contract tests; this check
does not establish its current network availability.

## Match shots

`tables=["shots"]` supports Understat, Sofascore and ESPN. The existing Understat
loader keeps its season selection and optional completed-match IDs. ESPN and
Sofascore use explicit match IDs, include verified matches/teams, and skip
calendar discovery. For example, select a match already identified in ESPN:

```py
dataset = esd.load_dataset(
    source="espn", league="uefa.champions", season=2026,
    tables=["shots", "match_events"], match_ids=["401915310"],
    max_match_requests=1, cache_dir="./my-data/shot-responses", on_error="collect",
)
for shot in dataset.shot_records:
    print(shot.shot_id, shot.result, shot.minute, shot.xg, shot.coordinate_system)
```

The ID above selects Shakhtar-Sporting on November 3, 2026. In the ESPN summary
checked on November 8, recognized attempts were present in `commentary.play`,
with native `fieldPositionX/Y` and no xG. The adapter retains those positions
without assuming their scale or direction. Unreported positions/xG remain null. ESPN's `keyEvents`
and commentary can omit attempts, so `complete=True` establishes successful
requested tasks, not a complete attempt feed. Do not use its row count to
recompute team totals. Source commentary types identify on-target (`106`),
off-target (`117`), blocked (`135`), woodwork (`136`), goals and penalties.
Own goals are kept in events and excluded from the shot adapter.

| Source | Native collection | Coordinates | Expected goals | Endpoint reads per match |
| :--- | :--- | :--- | :--- | :--- |
| Understat | `shotsData` | `understat-native`, original X/Y | `xg`, model `understat` on new observations | Existing season loader plus selected match reads |
| Sofascore | `shotmap` | `sofascore-native-player`, original `playerCoordinates.x/y` | `xg` and `xgot`, model `sofascore` when observed | Event context plus shotmap, 2 reads |
| ESPN | Recognized `keyEvents`/`commentary.play` | `espn-native-field`, original `fieldPositionX/Y` when reported | Null | Summary, 1 read shared with all selected detail tables |

Sofascore requires native `season_id`. Each additionally selected lineup,
incident or match-statistics endpoint adds one read; event context is shared.
The preflight budget counts unique match IDs and endpoints before transport
retries. `shots:{id}` retains the shotmap fetch time separately from `match:{id}`.
ESPN attempts use the `match_details:{id}` summary observation. Both paths use
the caller-selected response cache and `CachePolicy.live_ttl`.

The raw adapter `normalize_match_shots(payload, match=normalized_match)` needs
verified match context but no HTTP or optional packages. `normalize_shot()`
continues accepting Understat's existing model. Shot keys are scoped to the
match: native `shot_id` when supplied, otherwise response-local `source_order`.
Sofascore's array position is not a persistent identity. ESPN deduplicates
native play IDs across its two collections, giving `keyEvents` precedence.

`source_details_json` retains the complete ESPN play or Sofascore shot,
including extra coordinates such as `goalMouthCoordinates` and unrecognized
fields. `team_id`, `home_away`, `body_part`, clocks and shootout flags remain
null when absent. Negative Sofascore unknown-time markers remain in raw details
and do not become match minutes. Explicit shootout counters stay outside
`minute`/`added_minute`. Periods are not inferred from minute thresholds.

Coordinate systems are never rescaled, mirrored or mixed. xG labels identify
providers, not model versions, and xGOT is distinct from xG. No cross-source xG
comparison or common pitch orientation is implied. Current Sofascore shotmap
responses could not be verified live in this environment because its API
returned HTTP 403; these parsing, cache and failure paths have offline tests.

Use `python examples/datasets/match_shots.py --help` for download/open options.
`python examples/datasets/match_shots_offline.py` runs invented source responses
without HTTP. Add `--pandas` for nullable DataFrames or `--parquet` for verified
snapshot round trips. Both extras remain independent.

## Match events

ESPN, 365Scores and Sofascore accept `tables=["match_events"]` with explicit `match_ids`.
The selection adds matches/teams for context, without calendar discovery.
Other providers reject this table before HTTP. Base installs return immutable
`match_event_records`; `.match_events` imports pandas only when accessed.

```py
import esd

dataset = esd.load_dataset(
    source="espn", league="uefa.champions", season=2023,
    tables=["match_events"], match_ids=[700722], max_match_requests=1,
    cache_dir="./my-data/event-responses",
)
for event in dataset.match_event_records:
    print(event.event_type, event.minute, event.added_minute, event.is_shootout,
          event.player_id, event.player_name)
```

This example selects Manchester Cityâ€“Real Madrid on April 17, 2024. ESPN's
native season year is `2023`. The source response checked November 7, 2026
contained ten shootout attempts in `commentary.play`, absent from `keyEvents`.
Some commentary participants had names but no IDs. They remain unresolved:
the adapter never matches their names to rosters or guesses a team ID.

| Field | Contract |
| :--- | :--- |
| `event_id` | Native ESPN/Sofascore event ID when present; null for 365Scores, which supplies an order instead |
| `source_order` | Native ESPN commentary sequence, 365Scores order, or zero-based position in the Sofascore response; scoped to this response |
| `source_collection` | `keyEvents`, `commentary.play`, `game.events` or `incidents` |
| `event_type` | Reviewed goal/card/substitution/penalty mappings; unrecognized native types remain `other` |
| `source_type_id`, `source_subtype_id` and names | Original source classification, retained independently of normalized type |
| `source_period`, `source_status_id` | Native codes, not shared period names across providers |
| `minute`, `added_minute` | Explicit match minute and added minutes, nullable; no default zero and no conversion from elapsed seconds |
| `clock_seconds` | ESPN clock or Sofascore `timeSeconds`; not a displayed rounded minute |
| `source_game_time`, `source_clock` | Native 365Scores/Sofascore numeric time and displayed clock, or ESPN displayed clock |
| `is_shootout` | ESPN flag/penalty period, 365Scores stage `11` or Sofascore `penaltyShootout`; null when not established |
| `scoring_play` | ESPN's explicit flag when present; does not recalculate match scores |
| `team_id` | Native event team; for own goals it can be the beneficiary rather than the player's team |
| `player_id`, `related_player_id` | Native player IDs for ESPN/Sofascore; native member IDs for 365Scores |
| `source_athlete_id`, `related_source_athlete_id` | Separate 365Scores athlete IDs when included in member metadata |
| Participant names and `source_participants_json` | Source names plus all original participant references, including missing IDs or more than two participants |
| `player_role`, `related_player_role` | `incoming`/`outgoing` for substitutions; `assist` for Sofascore's explicit `assist1`; other roles remain null |
| `source_text` | Original description when present, without interpreting free text |
| `rescinded` | Nullable Sofascore annulment flag; absent observations stay null |
| `source_details_json` | Complete native Sofascore incident, including sequence, reasons and unknown fields; null for other sources |

Reviewed normalized types are `goal`, `own_goal`, `penalty_scored`,
`penalty_missed`, `yellow_card`, `red_card`, `second_yellow_card`, `substitution` and `other`.
ESPN maps native types 70/137/173 to goals, 97 to own goals, 98/104 to converted
penalties, 113/115 to missed penalties, 94/93 to yellow/red cards and 76 to
substitutions. 365Scores maps type 1 to goals, subtype 2 to own goals, subtype
3 to converted penalties, type 6 to missed penalties, 2/3 to yellow/red cards
and 1000 to substitutions. Names can be localized and never select a mapping.
Unreviewed ESPN/365Scores classifications, including distinct second-yellow codes,
stay `other` with the native type preserved.

Sofascore uses `incidentType` and `incidentClass`, without reading localized text:

| Native type | Native class | Normalized type |
| :--- | :--- | :--- |
| `goal` | `ownGoal` / `penalty` / other goal classes | `own_goal` / `penalty_scored` / `goal` |
| `card` | `yellow` / `red` / `yellowRed` | `yellow_card` / `red_card` / `second_yellow_card` |
| `substitution` | Any | `substitution`, with `playerIn` and `playerOut` |
| `inGamePenalty` / `penaltyShootout` | `scored` / `missed` / `saved` | `penalty_scored` / `penalty_missed` / `penalty_missed` |
| Other type/class pairs | Native value retained | `other` |

These Sofascore mappings have offline contract tests. Direct live queries on
November 8, 2026 returned HTTP 403 from this connection. The loader retains
`SourceBlocked` and does not launch a browser or report successful empty coverage.
This implementation does not establish current source availability.

`isHome` maps a side only when the source includes an explicit boolean. A
missing flag leaves the team unknown. `rescinded=True` preserves an annulled
incident with its original type; records are not silently discarded. Unknown
annulment flags remain null. VAR decisions remain separate native incidents,
without rewriting another event or recalculating scores. Injury-time lengths,
additional assists, shootout sequences and native reasons remain in
`source_details_json`. Sofascore's `time=-1` marker becomes a null minute while
the raw value remains in that JSON. Shootout minutes/added minutes are always
null. A missing event ID uses the observed response position for deduplication,
independently of any native shootout sequence. Response positions can change.
Periods stay null unless explicitly included; neither minutes nor neighboring
period-marker rows establish an inferred period.

ESPN retains every `keyEvents` record and appends recognized goals, penalties,
cards and substitutions from commentary, deduplicating by native event ID.
Key-event fields take precedence; contradictory known participant/team/type
IDs fail validation. Repeated commentary descriptions do not duplicate a play.
365Scores retains every explicit event and keys it by match plus native order.
An order can change between responses and must not serve as an audit-log ID.
Returned records preserve collection order, not a common chronological order.
The CLI sorts its preview by observed minute and puts shootout attempts last.
Unknown clocks remain unknown.

ESPN period 5 identifies penalty shootout attempts even when their flag is
absent. 365Scores stage 11 uses counters such as 121 and a displayed attempt
number: these remain in `source_game_time`/`source_clock`, while `minute` and
`added_minute` are null. Events never change `home_score`/`away_score`, and should
not be summed to reconstruct the match result. An own goal's event team must
not be used as the player's roster membership.

For ESPN/365Scores, adding `lineups` or `player_match_stats` costs no extra read: ESPN shares one
summary per ID, 365Scores one game detail per ID. Adding `match_stats` also
shares the ESPN summary but costs one additional 365Scores endpoint read.
365Scores and Sofascore require native `season_id`; the year remains a caller label.
Sofascore needs two reads for events alone: verified event context and incidents.
Selected lineups/player statistics add one read, and selected team statistics
add another. The context is fetched once per ID. If it fails, dependent reads
are skipped and reported as failed tasks. If a lineup or incidents read fails,
the other selected parts can still succeed with `on_error="collect"`.
All selected parts of a shared response are checked before caching/committing.
Failed shared details remain partial, while separately valid team statistics
can still be retained with `on_error="collect"`.

Empty explicit event lists are valid. Missing/malformed lists are source
errors and are never cached as successful empty coverage. `complete` describes
the requested tasks, not a full event feed, all historical events or matching
coverage across sources. Datasets retain original fetch timestamps under
`match_details:{id}` for ESPN, `match_events:{id}` for 365Scores events alone,
or the existing `lineups:{id}` task when 365Scores player tables are selected.
Sofascore retains separate `match:{id}` and `match_events:{id}` timestamps;
an incidents read never replaces the original match-context timestamp.

Join participants to lineups/player statistics using `source`, `match_id` and
native `player_id`. Unresolved participants remain null or generate reference
warnings. Cross-provider player equivalence is not inferred by the catalog.
`normalize_match_events(payload, match=...)` offers the same raw-response
adapter without downloads, optional dependencies or input mutation.

See [event CLI and offline examples](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/README.md#match-events)
for cache paths, independent extras, saving and reopening snapshots.

## Discover competitions and seasons

Discovery returns immutable records without pandas or PyArrow. Inspect the
implemented operations before making a request:

```py
import esd

support = esd.get_discovery_capabilities()
competitions = esd.list_competitions("espn", query="Champions")
for row in competitions.competitions:
    print(row.competition_id, row.native_id, row.name)

seasons = esd.list_seasons("espn", "uefa.champions")
for row in seasons.seasons:
    print(row.season_id, row.year, row.name)
```

`DiscoveryResult.scope` identifies the source listing, search page, category, date or
season response. None of these asserts complete worldwide or historical coverage.
`fetched_at` is the original UTC fetch time, including cache reuse; `cached` reports
reuse. `notes` records selection limitations. Competition and season records remain
separate tuples. Queries make one source request before normal transport retries,
without following per-entry references or launching a browser.

| Source | Competition query | Season query |
| :--- | :--- | :--- |
| ESPN | Soccer dropdown, optional local name filter | Native season-year index for a league slug |
| 365Scores | Required `query`, football results only | Seasons included in competition details, possibly current season only |
| Sofascore | Required football `category_id`, all returned groups | Native tournament season IDs and period labels |
| Goaloo | Manual competition ID | Native `SeasonList` strings |
| Promiedos | Required source `date`, leagues listed that day | Manual selection |
| FBref | Manual selection | Manual selection |
| Understat | Manual selection | Manual selection |
| BeSoccer | Manual competition slug | Native standings year selector |
| Transfermarkt | Required `query`, explicit `page` (default 1), competition grid only | Native options, requiring `competition_url` from a search result |

Manual selection means that this common API has no verified adapter for that
operation; it does not establish that the provider has no such feature elsewhere.
These calls raise `DiscoveryNotSupported` before I/O. Implemented routes may
still raise `SourceBlocked`, `SourceNotFound` or `SourceError`. Malformed responses
are errors, not empty lists. Explicitly empty source lists remain empty.

`CompetitionInfo.competition_id` is the value to pass as `load_dataset(league=...)`.
For ESPN this is a slug such as `uefa.champions`, while `native_id` retains its
separate numeric ID. Both fields retain native IDs for other implemented sources.
Names do not establish cross-provider identity.

`SeasonInfo.season_id` is kept separate from `year` and `source_season`. ESPN's
index explicitly provides a year, usable as `season`. BeSoccer's `year` preserves
the native standings selector, which can be `2027` for a `2026-27` label. For Sofascore or 365Scores,
pass the native ID as `season_id` and choose the caller year label separately.
Goaloo's `source_season` selects the listed season string. Discovery does not
derive years from labels such as `26/27`, assume every integer is a year or fill
missing historical seasons with generated values. An ESPN index requiring more
than one page raises rather than silently returning a partial list.

Transfermarkt search includes both league (`wettbewerb`) and cup
(`pokalwettbewerb`) links. `page` and `scope="search_page"` describe one response,
not the whole search catalogue. Pass the competition's `source_url` to season
discovery so it can retain the native slug and route:

```py
results = esd.list_competitions("transfermarkt", query="Champions", page=1)
competition = next(row for row in results.competitions if row.competition_id == "CL")
seasons = esd.list_seasons(
    "transfermarkt", competition.competition_id,
    competition_url=competition.source_url,
)
```

Only official Transfermarkt competition links matching the selected ID are
accepted. Its native season option remains an ID and label; it does not select
historical entity datasets. Transfermarkt profiles remain current and histories
remain unfiltered, as described below. HTML selectors are checked against their
competition, and missing structures or browser challenges raise instead of
becoming empty lists. `DiscoveryResult.source_url` records the requested route.
If Transfermarkt clamps an out-of-range search page to another page, discovery
raises `SourceError` rather than labeling those results with the requested number.

The remaining discovery adapters were investigated on November 7, 2026. FBref's
[competition index](https://fbref.com/en/comps/) and
[history page](https://fbref.com/en/comps/9/history/Premier-League-Seasons) returned
HTTP 403 from the verification environment. Understat's
[home](https://understat.com/) and [league page](https://understat.com/league/EPL)
returned maintenance HTML. BeSoccer's competition listing returned a page shell
without the catalogue or a challenge, although its
[Champions season selector](https://es.besoccer.com/competicion/clasificacion/champions)
was readable. These observations do not establish permanent provider limitations.
Their unverified operations retain manual selection; no static catalogue or
generated historical seasons substitutes for a source response.

Supply `cache_dir`, `cache_policy` and `refresh` to either discovery function for
validated response reuse and refresh. The directory is caller-selected; no files
are written without it. Original fetch times survive cache hits. Failed refreshes
do not replace a valid entry. `proxies` is forwarded to the existing HTTP helper.

The routes use provider responses, including ESPN's
[soccer listing](https://site.api.espn.com/apis/site/v2/leagues/dropdown?region=us&lang=en&sport=soccer),
[season index](https://sports.core.api.espn.com/v2/sports/soccer/leagues/uefa.champions/seasons?limit=1000),
Sofascore's [native seasons](https://www.sofascore.com/api/v1/unique-tournament/7/seasons)
and Goaloo's [season strings](https://football.goaloo.com/jsData/leagueSeason/sea36.json).
These responses are not stability guarantees. Use the
[CLI examples](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/README.md#discover-selectors-before-loading-data)
or run `python examples/datasets/discovery_offline.py` for artificial responses
showing selector differences and cache behavior.

For a full 365Scores example, use `examples/datasets/discover_and_download.py`.
It checks the exact competition and native season IDs against discovery results,
downloads one to seven UTC days plus standings and validates the normalized data.
`--output-dir` saves a new Parquet snapshot and reopens it to compare all records
and metadata. Validation errors prevent saving. A partial download retains its
errors in the snapshot and returns exit code `1`; warnings alone do not fail a
complete download. `--open-dir` validates a snapshot without discovery or HTTP.
The base install supports download/validation; storage needs `[parquet]`, without
pandas. `discovery_workflow_offline.py` runs the same flow with artificial responses;
add `--parquet` for temporary storage and offline reopening.

## Provider selection

The same Python call has provider-specific selection requirements. Inspect
`esd.get_dataset_capabilities(source)` before constructing a query.

| Source | `league` | Selection details |
| :--- | :--- | :--- |
| ESPN | Code, e.g. `eng.1` | `season=2024` selects the source season year; optional `anchor_date` changes calendar discovery |
| 365Scores | Native numeric competition ID | Explicit UTC `start_date`/`end_date` for matches; native `season_id` required for standings and optionally checks match seasons |
| Sofascore | Native unique tournament ID | Required native `season_id`; `season` is a separate year label; both pagination directions must finish |
| FBref | Numeric competition ID | Explicit dates; timezone for naive kickoffs; match-report IDs required; no automatic browser launch |
| Goaloo | Numeric league ID | Required `source_season`, e.g. `2024-2025`, checked against native metadata; timezone for naive kickoffs |
| Promiedos | Native league ID | Explicit dates and timezone for naive kickoffs; year is a label, not a historical season filter |
| BeSoccer | Competition slug | Explicit dates for matches, year for standings; adjacent-day games filtered in UTC or the supplied timezone |
| Understat | League code, e.g. `EPL` | Season year; timezone for naive kickoffs; optional shot `match_ids` must belong to completed matches in that league/season |
| Transfermarkt | Caller competition context | Explicit `club_ids`/`player_ids`; current profiles and full histories, not historical season rosters |

Transfermarkt validates clubs against the requested native competition. Player
profiles and histories are not filtered by league/year. Historical dates remain
source strings. Valuations retain currency; the current transfer model does not
provide a separate fee currency, so the source fee display is preserved.

Missing timezone information requires a decision based on the source convention.
`source_timezone="UTC"` assumes UTC; it does not discover the timezone. IANA names
such as `Asia/Shanghai` require system timezone data or the optional `tzdata`
package, independently of pandas and Parquet.

FBref queries remain sequential, at least `60/9` seconds apart. `request_delay=0`
does not bypass that cap. Sofascore's `max_pages` guards each pagination direction;
reaching it before an explicit end produces an error, not complete coverage.

See [all nine live CLI selections](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/README.md#live-dataset-queries).

For a two-day Champions League download without pandas, run
`python examples/datasets/champions_league.py` from the checkout root. Use
`--start-date` and `--end-date` to select up to seven UTC days. The
[Champions League example](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/datasets/champions_league.py)
prints records and reports failed days. Supply `--cache-dir ./my-data/champions-responses`
to reuse validated responses, or add `--refresh` to fetch the range again.
With `python -m pip install -e ".[parquet]"`, add
`--output-dir ./my-data/champions-snapshot-1` to save the records to a new directory.
Run `python examples/datasets/champions_league.py --open-dir ./my-data/champions-snapshot-1`
to display the saved results without source requests. Empty tables, task coverage
and errors survive export. Opening a partial snapshot still reports its failures
and returns exit code `1`. No pandas installation is needed.

To analyze the saved range with pandas, install `".[pandas,parquet]"` or `".[full]"`
and run `python examples/pandas/champions_analysis.py ./my-data/champions-snapshot-1`.
The [analysis example](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/pandas/champions_analysis.py)
lists matches in UTC and groups finished results by source and team ID. It excludes
unknown scores, invalid team IDs and statuses other than 365Scores group `4` from
the summary, while retaining those matches in the fixture list. Goals remain as
stored, without inferring shootout winners. The summary covers the saved dates
and does not reproduce official standings. Partial downloads retain their errors.
Use `match_records` or the download example's `--open-dir` to read the same
fixtures without pandas.

For a comparison of the same Champions League UTC range across 365Scores and ESPN,
run `python examples/datasets/champions_compare.py`. The
[comparison example](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/datasets/champions_compare.py)
loads explicit aliases from a JSON example map, links unique candidates and reports
unmatched or ambiguous native IDs. It retains source scores, status codes and
original fetch times per query. Review aliases for other date ranges. Score
differences are observations, not automatic corrections or proof of a source error.
With the Parquet extra, `--output-dir ./my-data/champions-pair-1` saves both datasets,
aliases and report. `--open-dir ./my-data/champions-pair-1` repeats the comparison
offline, without pandas, using the saved tolerance and identities. ESPN queries
only daily scoreboards, with adjacent-day padding before UTC filtering.

## Partial downloads

`complete` means that every requested task succeeded. It does not establish that
the season has finished or the provider lists every fixture. Failed requests
appear in `dataset.errors`, including those that returned no records.

```py
try:
    dataset = esd.load_dataset(source="espn", league="eng.1", season=2024)
except esd.DatasetLoadError as exc:
    dataset = exc.dataset

print(dataset.complete)
for issue in dataset.errors:
    print(issue.step, issue.target, issue.error_type, issue.message)
```

The default `on_error="raise"` stops after a failure. `"collect"` continues with
other tasks and returns the partial dataset. Invalid query arguments fail before
download; `on_error` does not turn them into collected source errors. Exceptions
from a user progress callback propagate directly.

ESPN exposes `calendar_dates` and `successful_dates` in metadata. Other loaders
expose `expected_tasks` and `successful_tasks`. Progress totals can grow during
page or shot discovery, so do not assume a fixed denominator at the first event.

Try [the offline partial-result example](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/datasets/partial_results.py).

## Validate a dataset

`esd.validate_dataset(dataset)` inspects a `SoccerDataset` without network calls,
file writes, pandas or PyArrow. It returns an immutable `DatasetValidationReport`.
Each issue has `severity`, `code`, `message`, and optional `table`, zero-based
`row_index` and `field`. An argument of another type raises `TypeError`.

```py
import esd

report = esd.validate_dataset(dataset)
print(report.valid, len(report.errors), len(report.warnings))
for issue in report.issues:
    print(issue.severity, issue.code, issue.table, issue.row_index, issue.field, issue.message)
```

`valid` means no errors were found. It does not establish complete download
coverage or agreement with another source. Incomplete coverage and saved source
failures are warnings. A task marked both successful and failed is an error.
Unknown scores remain allowed, including zero for a known score on one side and
`None` on the other. Validation never infers whether a match is finished.

Errors include invalid metadata or record types, blank IDs, duplicate record keys,
negative match scores, source/competition conflicts, invalid date bounds and
kickoffs outside those bounds. Missing native IDs or kickoff times are warnings.
If a referenced team or match is absent from a selected table, validation warns
without assuming that table is a complete source catalogue. Unselected tables
are not used for reference checks. Records in an unselected table are an error.

Standings keys retain competition, season, table, stage and group context. The
same team in two groups is allowed. Valuation keys use player, native date, club
and source season, so repeated players across history are allowed. Native
Transfermarkt dates and historical club references are not checked against
current roster membership or the caller's season label. Source status codes,
points systems and penalty conventions are not interpreted.

Kickoffs must be timezone-aware. Nonzero UTC offsets generate a warning, without
modifying the time. For dated FBref, Promiedos and BeSoccer pages, bounds are
checked in `metadata.source_timezone`; BeSoccer defaults to UTC when unspecified.
FBref and Promiedos bounds without a known source timezone, or IANA zones not
available on the machine, generate a warning and skip that range check. Other
date bounds use UTC. Cached responses may predate the current loader invocation.

Run the [offline validation example](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/datasets/validate_dataset.py)
with `python examples/datasets/validate_dataset.py`. It creates artificial records
and shows a partial download, duplicate IDs, invalid scores and unresolved teams.
Calling validation does not automatically reject saves or alter loader behavior.

To check real samples, run `python scripts/check_sources.py --source espn scores365`.
The command reports download failures separately from validation errors and warnings.
With `--check-parquet`, it also saves and reopens each returned dataset in temporary
storage, including partial results. Supply `--snapshot-dir ./my-data/source-samples-1`
to retain snapshots in a new directory instead. PyArrow is needed only for snapshot
checks. Both modes work without pandas. See the
[live check options](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/README.md#live-provider-checks)
for request limits, report fields and exit codes.

## Response caches and snapshots

Choose each storage path when calling the library:

- `cache_dir` stores validated raw responses as JSON, including wrapped HTML for
  page sources. Repeating a query reuses fresh responses and fetches expired or
  failed tasks. It requires only the base installation.
- `dataset.save(path)` creates an offline Parquet snapshot with records, errors,
  metadata and checksums. It requires `[parquet]`, and `path` must not exist.

```py
dataset = esd.load_dataset(
    source="espn", league="eng.1", season=2024,
    cache_dir="./my-data/responses", on_error="collect",
)
path = dataset.save("./my-data/snapshot-1")  # Needs the parquet extra.
restored = esd.open_dataset(path)             # No network and no pandas needed.
assert restored == dataset
```

Saving a partial result preserves `complete=False` and its errors. Reopening a
snapshot never resumes a download. To resume, repeat `load_dataset()` with the
same selection and cache directory. `refresh=True` bypasses response reuse;
it does not overwrite an existing snapshot directory.

The normalized schema is version `6`. Existing version `1`â€“`5` Parquet
snapshots remain readable. The reader validates their original table schemas
and checksums, adds absent version-1 match-statistic columns as null and returns
version `6` records. Schema-4 event snapshots gain null `rescinded` and
`source_details_json` columns, preserving original observations. Older shots gain
null team, order, source/model, xGOT, body-part, clock, shootout and raw-detail
columns. Existing xG and native coordinates remain unchanged; the reader does
not invent a model label for a historical observation. Tables absent from the original schema, including events
and older lineup/player tables, are not selected or fabricated.
Source timestamps, IDs, values, errors and coverage are
retained. Saving the opened dataset writes version `6`; the original snapshot
is not changed.

`metadata.started_at`/`finished_at` describe the current loader call.
`dict(metadata.response_fetched_at)` preserves original fetch dates per task,
including cached responses; `cached_tasks` identifies reuse. Use the original
fetch dates to measure data age.

`CachePolicy` adjusts freshness. Its date/status rules apply to ESPN/365Scores
daily responses. Other loaders use their documented calendar/live/standings/
historical TTLs. Disk entries are not pruned automatically; `ResponseCache(path).clear()`
removes owned cache entries without deleting snapshot files.

Try [offline cache reuse](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/datasets/cache_resume_offline.py) or
[snapshot round trips](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/datasets/parquet_roundtrip.py).

## Joins and match linkage

Within one provider, join on both `source` and the native ID. Standings can have
several rows for a team across groups/stages/tables: select one table before
expecting a many-to-one join. Do not join standings to matches solely by a team
name, or treat today's standings as standings at each historical kickoff.

To link providers, supply an `IdentityMap` with competition and team aliases
that you have checked. You can use `get_catalog().identities()` for the reviewed
sample above or maintain your own map. The linker does not infer identities from
names, source IDs or scores.

Store your own aliases wherever your application needs them. For example, a
JSON list can contain objects with `kind`, `canonical_id`, `source`, `source_id`:

```py
import json
from pathlib import Path

aliases = json.loads(Path("./my-data/identities.json").read_text(encoding="utf-8"))
identities = esd.IdentityMap.from_dict(aliases)
left = esd.open_dataset("./my-data/espn-snapshot")
right = esd.open_dataset("./my-data/other-snapshot")
```

Create the alias file and snapshots before running this example. Opening the
snapshots requires `[parquet]`. The compatibility and linkage functions use
only the base installation.

```py
report = esd.check_dataset_compatibility(left, right, identities=identities)
print(report.schema_compatible, report.identity_compatible, report.issues)
result = esd.link_dataset_matches(left, right, identities=identities)
for link in result.links:
    print(link.left_source, link.left_match_id, link.right_source, link.right_match_id)
print(result.unmatched_left, result.unmatched_right)
print(result.ambiguous_left, result.ambiguous_right)
```

The linker checks mapped competition, ordered home/away teams and kickoff
distance (default 300 seconds). Both sides must have exactly one candidate.
Missing dates, absent mappings, reversed teams, rescheduled games or ambiguous
candidates remain unlinked. Partial mappings can still yield partial links.
`can_match` checks schema, table selection and identity coverage. Matching also
requires kickoff times within the tolerance and a unique candidate on each side.
`issues` can include notes about source fields even for compatible schemas.

Linkage preserves inputs and native IDs. It does not harmonize xG models, penalty
conventions, statuses, currencies or pitch coordinates. Understat shots stay in
their native coordinate system. Player/event comparisons use explicit player
aliases and the [scope rules](#player-identity-scope) above.

Run [the offline linkage example](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/datasets/link_matches.py) for an
identity map and an ambiguous case, or
[the pandas analysis example](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/pandas/dataset_analysis.py) for nullable
scores and validated team joins.

## Compare match statistics

`compare_match_statistics()` reads two validated datasets selecting `matches`
and `match_stats`. It makes no requests or file writes and needs neither pandas
nor PyArrow. It reuses the identity and one-to-one kickoff rules above. Unmatched
and ambiguous matches remain in `report.linkage`; they do not produce metric rows.

Given two statistics snapshots and checked aliases:

```py
report = esd.compare_match_statistics(
    left, right, identities=identities,
    metrics=["home_shots", "away_shots", "home_possession_pct", "home_xg"],
    tolerances={"home_possession_pct": 0.1},
)
for row in report.rows:
    print(row.left_match_id, row.right_match_id, row.metric,
          row.left_value, row.right_value, row.status, row.delta)
print(report.linkage.unmatched_left, report.linkage.ambiguous_right)
print(report.left_complete, report.right_complete, report.left_errors)
# Optional: frame = report.to_dataframe()  # Requires [pandas].
```

`delta` is right minus left. A tolerance is an absolute difference in that
field's units, with zero as default. Possession tolerances use percentage points,
so `0.1` accepts `51.5` against `51.6`. Counts retain integer values in the report.
The optional DataFrame uses nullable `Float64` for mixed numeric metrics,
nullable booleans and aware UTC timestamps, including when it has no rows.

| Status | Meaning |
| :--- | :--- |
| `equal`, `different` | Numeric observations within/outside the absolute tolerance |
| `missing_left`, `missing_right`, `missing_both` | A metric is null in an existing statistics record |
| `record_missing_left`, `record_missing_right`, `record_missing_both` | A linked match lacks a statistics record |
| `period_unknown`, `period_mismatch` | A period is absent/unrecognized, or the known periods differ |
| `source_specific` | Both values exist, but xG/forecast models belong to different providers |

Only `equal` and `different` rows have a numeric delta. Missing observations are
checked first and remain distinct from reported zeros. `report.differences`
contains `different` rows; `report.unresolved` contains every other status except
`equal`. Unlinked matches are separate linkage diagnostics, not unresolved rows.

The native selectors ESPN `boxscore`, 365Scores `-1` and Sofascore `ALL` are
recognized source totals. Comparing these observations does not establish equal
extra-time rules or collection methods, and the report never chooses a correct
provider. Same-source records can compare an identical explicit native period.
Unknown periods, including older xG records without period metadata, remain
unresolved. Cross-source xG/forecast values get no delta even when they agree.

Per-row fetch dates come only from exact `match_stats:<native ID>` task keys,
or the shared ESPN `match_details:<native ID>` response when no separate
statistics task is present.
Calendar/batch timestamps are not attributed to individual matches. A missing
exact timestamp stays null. The report also retains both complete metadata
records, original errors and validation warnings. Partial downloads can produce
comparisons for their available linked matches without becoming complete.

Run `python examples/datasets/compare_statistics_offline.py` for artificial
values, with optional `--pandas` or `--parquet`. For a real bounded Champions
League query, use:

```sh
python examples/datasets/champions_statistics.py --espn-match-id 401915310 --scores365-match-id 4828447 --season 2026 --season-id 74
```

These IDs identified Shakhtar Donetsk vs Sporting CP on November 3, 2026 in a
live check on November 7. The sources agreed on shots (`14`, `11`), but differed
on home passes (`437` vs `441`) and home possession (`54.4` vs `54.0`). These
are observations from that check, not fixed expected output. Each provider costs
one endpoint read before retries. The included aliases are a checked sample.
See [the example options](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/README.md#compare-match-statistics)
for caller-selected cache/snapshot paths and offline recomputation.

## Compare match events

`compare_match_events()` compares selected ESPN/365Scores/Sofascore observations without
HTTP, writes, pandas or PyArrow. Both datasets must select `matches` and
`match_events`, pass validation and identify every event's native match.
The existing match linker supplies unique competition/team/kickoff links.
All three sources support same-source and cross-source comparisons. Sofascore's
native player IDs need explicit caller-reviewed aliases; the bundled catalog
still supplies competition/team aliases for ESPN/365Scores only.

Player identity is explicit. `IdentityMap` accepts `EntityAlias(kind="player", ...)`
for the native ID used by the normalized event. For 365Scores this is the member
ID, not `source_athlete_id`. Names, jersey numbers, descriptions and a shared
numeric ID across different providers never establish a player link. The bundled
catalog supplies competition/team aliases only. Extend its map independently:

```py
import esd

identities = esd.get_catalog().identities().with_aliases([
    esd.EntityAlias("player", "issa-doumbia", "espn", "386592"),
    esd.EntityAlias("player", "issa-doumbia", "scores365", "75430996"),
])
# left/right are downloaded or reopened match-event datasets.
# report = esd.compare_match_events(left, right, identities=identities)
```

These example player IDs were reviewed for Shakhtarâ€“Sporting on November 3,
2026. They are not a player registry. Native member IDs can change with team
membership. Applications must review additional equivalences. `.aliases` returns
an immutable tuple of `EntityAlias` entries. `IdentityMap.to_dict()` serializes
scope dates and evidence into JSON-compatible values, and `from_dict()` restores
them. The earlier bare list format is also accepted.
`with_aliases()` returns a new map and rejects conflicting native-ID assignments.
The original map and dataset IDs remain unchanged. Existing match compatibility
continues to check competition/team coverage; it does not certify player coverage.

### Candidate rules

By default, candidates require a known player identity, a mapped event team,
explicit shootout state and compatible known periods. Goal/own-goal/penalty observations
share a scoring family; yellow/red/second-yellow cards share a card family.
Different known types within a family can therefore be reported as a difference.
Substitutions require both mapped players in explicit incoming/outgoing roles.
Event teams are compared as source observations and can differ for own goals
without establishing which source is correct.

Non-shootout events also require observed minutes within `minute_tolerance`
(default 1). When both added-time values are known, their minute-plus-added-time
difference must also fit. A missing added-time value remains unknown, never zero.
The tolerance admits candidates; a known 59 versus 60 remains a reported minute
difference. `minute_tolerance=0` requires exact observed clocks for candidates.
Shootout attempts use player/period identity without comparing match minutes
or treating a 365Scores order as a persistent event ID. Repeated attempts by one
player remain ambiguous when they cannot be identified uniquely.

Only candidates unique in both directions are paired. The comparator does not
choose a nearest event, use list position or force a one-to-one assignment to
resolve ambiguity. Within one source and the same native match, a shared native
event ID anchors revisions even when a player, clock or period observation has
changed. Different known native event IDs in one source remain distinct.

Default period aliases map ESPN 1/2/3/4/5 to the two halves, two extra-time
halves and shootout, and 365Scores 7/9/11 to first half/second half/shootout.
Other native periods are unknown across sources unless the caller supplies an
explicit `period_aliases={(source, native_code): canonical_period}` mapping.
The final map is retained in the report. No period is inferred from a minute
threshold. Identical explicit native periods can be used for same-source comparisons.

Sofascore incident periods often are absent. No default Sofascore period mapping
or minute-based half inference is supplied. The strict default reports those
events as `period_unknown`. `allow_unknown_period=True` explicitly permits a
candidate when either mapped period is unknown, while preserving
`source_period` in `unknown_fields`. Known conflicting mapped periods still
cannot pair. Player/team identities, explicit shootout state, clock requirements,
substitution roles and mutual uniqueness still apply. This option broadens
candidate scope; it does not verify the missing period. It is stored as
`report.allow_unknown_period`, including when recomputing saved workflows.

### Report and provenance

`MatchEventsReport.rows` retains each paired or unresolved native event in full:

| Status | Meaning |
| :--- | :--- |
| `equal` | Known comparable observations agree; `unknown_fields` remains unverified |
| `different` | A unique pair has differing known observations, named in `differences` |
| `unresolved_left` / `unresolved_right` | Match, player/team identity, clock, role or period evidence is missing |
| `ambiguous_left` / `ambiguous_right` | Candidate identity is not unique in both directions; `candidate_keys` lists opposite native references |
| `unmatched_left` / `unmatched_right` | A usable event has no candidate in the linked fixture |

Compared observations are normalized type, team/player identity, shootout state,
period, known match/added minutes, annulment flag and substitution participants/roles.
Native descriptions, source orders, ratings and elapsed-clock precision do not
serve as equivalence tests. Original fields remain in `left_event`/`right_event`.
Absent annulments, including null/null, appear in `unknown_fields`. Equal observed
fields do not prove that an event was not annulled or that both collections are complete.

Every selected event appears in exactly one report row, with two observations
in a paired row. Unselected/native `other` types are retained in `excluded_left`
and `excluded_right`. `event_types` can restrict the default scoring/card/change
selection. Match ambiguity/unmatched IDs remain in `report.linkage`, including
fixtures with no selected events. `.differences` selects differing pairs;
`.unresolved` selects all unpaired rows. Unmatched records do not prove that a
provider omitted an event: identity coverage, timing and collection rules can differ.

`left_coverage`/`right_coverage` separate exact event-task success, raw record count
and original fetch date per native match. A successfully obtained empty list is
different from a failed task with no records. Metadata, source errors, validation
warnings, complete flags, candidate tolerance and period aliases are retained.
Rows use exact ESPN `match_details:{id}`, 365Scores `match_events:{id}`/`lineups:{id}`
or Sofascore `match_events:{id}` fetch dates. A Sofascore lineup task cannot
establish incident success or dates. Calendar/context/loader timestamps are never substitutes. Conflicting
timestamps for multiple possible event tasks leave the row date unknown.

`report.to_dataframe()` lazily imports pandas and returns fixed columns, including
empty reports, nullable counts/flags and UTC timestamps. Diagnostic tuple fields
become JSON strings in the frame; the report keeps structured tuples and full
native event records. The report format version is 1, independent of normalized
schema 6. The comparison itself adds no normalized columns.

The [Champions comparison example](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/README.md#compare-match-events)
downloads two bounded summaries, saves source snapshots/identities/options/report,
and recomputes offline from the original records. An artificial example exercises
minute differences, penalty outcomes, ambiguous cards and unknown players.

## Compare lineups and player statistics

`compare_match_players()` compares ESPN/365Scores/Sofascore observations without HTTP,
file writes, pandas or PyArrow. Both datasets must select `matches` and
`lineups`, pass validation and identify every lineup's native match. Any
player-statistics record must reference a selected lineup using the exact native
match/team/player key. All three sources support same-source and cross-source
comparisons. Sofascore positions use the same caller-reviewed alias contract,
and its xG/xA/ratings retain their source-specific models across providers.

The existing match linker establishes unique competition, ordered team and UTC
kickoff links. Within each fixture, player aliases establish a pair only when
the canonical identity is unique on both sides. Names, jerseys, positions and
365Scores `source_athlete_id` never establish player links. Use the normalized
member `player_id` for 365Scores aliases. Same-source comparisons use native
player IDs without cross-source aliases.

```py
import esd

identities = esd.get_catalog().identities().with_aliases([
    esd.EntityAlias("player", "issa-doumbia", "espn", "386592"),
    esd.EntityAlias("player", "issa-doumbia", "scores365", "75430996"),
])
# left/right select lineups and optionally player_match_stats.
# report = esd.compare_match_players(
#     left, right, identities=identities,
#     metrics=["minutes", "goals", "assists", "shots", "xg"],
#     tolerances={"minutes": 1},
# )
```

Every listed player occurs once in `report.rows`, paired or unresolved. Original
records remain in `left_lineup`/`right_lineup`, with any exact native statistics
record in `left_statistics`/`right_statistics`. Those records remain attached
even when a player's identity is unresolved. No source IDs or observations are
rewritten. A differing team observation can be reported for a uniquely mapped
player. Unknown event team membership is not inferred from goal events.

### Lineup fields and identities

Known canonical team, home/away side, starter, captain, jersey, formation and
confirmation observations are compared. Formation and jersey comparisons are
literal: they do not establish identical tactical or formatting conventions.
Missing flags remain unknown, including unknown/unknown. A listed substitute
does not establish participation or zero minutes.

Positions retain native labels and need explicit cross-source aliases, for
example `position_aliases={(source, native_label): canonical_position}`. This
mapping is caller-reviewed and saved in the report. Even identical labels are
unknown across providers without that mapping. ESPN's `SUB` label describes a
lineup role rather than a field position; do not map it to a tactical position.
Same-source positions compare their native labels. Source role/status codes
and source position IDs remain in the records without cross-source comparisons.

| Lineup status | Meaning |
| :--- | :--- |
| `equal` | Known comparable fields agree; `unknown_fields` remains unverified |
| `different` | A unique player pair differs in the fields named by `differences` |
| `unresolved_left` / `unresolved_right` | Player identity or fixture linkage is unavailable |
| `ambiguous_left` / `ambiguous_right` | Multiple native players map to one canonical identity on either side |
| `unmatched_left` / `unmatched_right` | A usable unique identity has no opposite observation |

`reason` distinguishes unknown player identity, no candidate, multiple candidates,
unlinked fixtures and ambiguous fixtures. `candidate_keys` lists opposite native
player IDs scoped to the linked fixture. Multiple aliases are never resolved by
names, jersey numbers or ordering. A repeated alias within one fixture stays
ambiguous even if the opposite source has no candidate. Fixture decisions also
remain in `report.linkage`, including matches with empty lineups.

### Individual metrics and unknowns

If either dataset selects `player_match_stats`, `report.statistics` contains one
row per player-comparison row and selected metric. `metrics` defaults to the
normalized count fields plus xG, xA and source rating. `tolerances` supplies finite
nonnegative absolute differences per selected metric, default zero. Minutes use
minute units; other integer metrics use counts. A comparable `delta` is right
minus left. Original integer values remain integers in the report.

Statistics are independent of lineup differences. Missing observations are never
zero, and an unused player's lineup can have no statistics record. Match metrics
have no period breakdown in these records. Numeric differences describe source
totals without asserting identical regulation, extra-time, stoppage-time or
collection conventions. Cross-source xG, xA and ratings retain their source
models and have no delta even when their numbers agree. Same-source xG/xA/ratings
can be compared as source observations without certifying model stability.

| Metric status | Meaning |
| :--- | :--- |
| `equal` / `different` | Comparable observations within/outside the absolute tolerance |
| `table_unselected_left` / `table_unselected_right` | A source did not request player statistics |
| `record_missing_left` / `record_missing_right` / `record_missing_both` | A selected table has no player-statistics record |
| `missing_left` / `missing_right` / `missing_both` | A record exists but the metric was not observed |
| `source_specific` | Both values exist, but cross-source xG/xA/rating models remain separate |
| Any unpaired lineup status | Player/fixture linkage must be resolved before comparing its metrics |

An unpaired player's status takes precedence over metric diagnostics. When
neither dataset selects statistics, `statistics` is empty. `.differences` and
`.unresolved` select lineup rows; `.statistic_differences` and
`.unresolved_statistics` select metric rows. Equal lineup fields do not imply
that all individual metrics were observed or agreed.

### Coverage, timestamps and export

`left_coverage`/`right_coverage` retain exact player-task success, lineup and
statistics counts, whether statistics were selected and the original fetch date
for each native match. A successful empty response differs from a failed task.
Only ESPN `match_details:{id}` and 365Scores/Sofascore `lineups:{id}` establish
these dates. A successful Sofascore event/context read cannot establish lineup
success. Calendar, event-only, context and loader timestamps are not substitutes.
Metadata, download errors, validation warnings, complete flags and comparison
settings remain in the report.

`report.to_dataframe()` exports lineup rows; `report.to_dataframe("statistics")`
exports metrics. Both import pandas lazily, keep fixed columns when empty and
use nullable strings/booleans/numbers with UTC nanosecond dates. Lineup diagnostic
tuples become JSON strings in frames. Statistics use nullable Float64 columns;
raw records retain integer counts. Frame report version 1 is independent of
normalized schema 6. The comparison itself adds no normalized columns.

The [Champions/offline examples](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/README.md#compare-lineups-and-player-statistics)
cover bounded downloads, partial player identities and saved source pairs with
aliases/settings. Reopening recomputes observations from source snapshots.

## Integrated Champions workflow

`examples/datasets/champions_workflow.py` combines match context, team totals,
lineups, player statistics and events. It compares every selected source pair
using the contracts above. The three-source demo uses artificial native
responses, verifies seven shared endpoint reads and reuses their original
timestamps from cache:

```sh
python examples/datasets/champions_workflow.py --demo --allow-unknown-period
python examples/datasets/champions_workflow.py --demo --allow-unknown-period --parquet
```

Live mode accepts explicit ESPN/365Scores Champions match and season selectors,
with optional Sofascore match/season IDs and caller-reviewed aliases. It reads
three endpoints for the two-source selection or seven with Sofascore, before
transport retries. A source error keeps that source partial while retaining
successful tables and other providers. The workflow does not enumerate a full
season calendar or infer native selectors from labels.

`--cache-dir` chooses response storage and `--output-dir` publishes a new bundle
only after all source snapshots reopen unchanged. The bundle contains the
selected sources, reviewed identities, pinned metric/period/position options and
diagnostic reports. `--open-dir` recomputes from source snapshots and saved
settings, ignoring saved report rows and making no HTTP requests. Base operation
needs no extras; storage uses `[parquet]` and frames independently use `[pandas]`.
`--parquet` verifies a temporary demo bundle without retaining files.

The [example index](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/README.md#integrated-champions-workflow)
documents live commands, partial identity coverage, exact exit codes and the
scope of live checks. Sofascore compatibility has offline contract tests; its
API returned HTTP 403 in this environment on November 8, 2026. This does not
establish permanent availability or equivalent collection rules.

## Troubleshooting

| Symptom | What to check |
| :--- | :--- |
| Dataset function absent after PyPI install | Use the 0.2.0 source checkout until it is published |
| DataFrame property raises `ImportError` | Install `[pandas]`; raw record tuples still work |
| Save/open raises `ImportError` | Install `[parquet]`; pandas alone does not install PyArrow |
| `ZoneInfoNotFoundError` | Check the IANA name and install system timezone data or `tzdata` |
| Table not requested or unsupported | Inspect `get_dataset_capabilities(source)` and the selected `tables` |
| `SourceBlocked`, 403 or maintenance page | Inspect source errors; these are not valid empty datasets |
| Season/competition mismatch | Use the provider's actual native ID, not a code copied from another source |
| Snapshot destination exists | Choose a new directory; snapshots do not overwrite existing paths |
| No cross-source links | Inspect identity mappings, source timestamps, tolerance and ambiguous IDs |

Use a small date range or a few entity IDs to reproduce download errors. Run
`scripts/check_examples.py` to check offline examples without querying providers.

## Read selected tables and matches

```python
from esd import open_dataset

selected = open_dataset(
    "./my-data/champions", tables=("matches", "shots"), match_ids=("401915310",),
)
print(selected.metadata.original_tables)
print(selected.metadata.snapshot_match_ids)
```

`tables` must be a nonempty subset of the saved tables. Omit it to open every
saved table. `match_ids` accepts native string IDs, preserving leading zeros.
An empty sequence or an unknown ID produces no matching rows. Tables containing
`match_id` are filtered, including events, lineups and player-match statistics.
Other selected tables retain all rows. Season statistics, standings and entity
histories are not attributed to individual fixtures.

The reader checks every file's checksum, schema and footer row count, including
omitted tables. Selected match tables are decoded in batches of up to 65,536
rows, retaining only matches that pass the filter. All file bytes are still read
for checksum verification. Omitted tables are not decoded. The resulting records
remain in memory, so a selection containing many rows still requires memory for
those rows. Opening requires `[parquet]` and does not import pandas.

`metadata.tables` describes the available tables. `original_tables` retains the
original download selection, while `snapshot_match_ids` records the local filter
(`None` means no filter, an empty tuple means no selected matches). Requested IDs,
tasks, errors, cache flags and response timestamps keep their original meanings.
`complete` refers to the original download. Field coverage counts the rows loaded
locally, while task coverage describes the original requests.

Saving to a new directory preserves these selection fields. Reopening a selection
cannot recover omitted rows. A further match filter intersects the saved filter.
Older snapshots without selection metadata remain supported, including their
schema migrations. Reading does not modify the source directory.

Run `python examples/datasets/select_snapshot.py --help` for an offline reader.

## Derived statistics

`derive_statistics(record)` accepts `NormalizedPlayerMatchStats`,
`NormalizedPlayerStats` or `NormalizedMatchStats`. It performs no requests and
requires neither pandas nor PyArrow. Apply it to the corresponding record tuples
from a download or a reopened snapshot:

```python
from esd import derive_statistics, derived_statistics_to_dataframe

results = tuple(derive_statistics(row) for row in dataset.player_match_stat_records)
# Optional [pandas], one row per metric with native source/match/player IDs:
frame = derived_statistics_to_dataframe(results)
# JSON-compatible definitions, input observations and results:
documents = [result.to_dict() for result in results]
```

Each `DerivedStatistics` retains the original frozen row in `record`. Its
`metrics` tuple contains `DerivedMetric` objects with the numerator/denominator
field names, their observed values, scale, unit, result and status. JSON uses
`easysoccerdata-derived-statistics` format version 1. This format is separate
from normalized snapshot schema 6, which does not change.

| Calculation | Formula | Available rows |
| --- | --- | --- |
| Player metric per 90 | metric / minutes × 90 | Player-match and player-season |
| Pass accuracy | accurate_passes / passes × 100 | Player-match and each match side |
| Shot accuracy | shots_on_target / shots × 100 | Player-match and each match side |
| xG per shot | xg / shots | Player-match, player-season and each match side |

Player-match rates cover observed counts except minutes and appearances, plus
xG and xA. Player-season rates cover goals, assists, shots, key passes, cards,
xG, xA, npxG, xG chain and xG buildup. Ratings and percentages are not scaled
per 90. A provider may leave any input absent. ESPN's current player-match
adapter, for example, does not populate minutes, and Sofascore's adapter does
not populate total shots. The corresponding rates remain null.

Reported minutes are used as supplied, including values above 90 for extra time.
They are never inferred from starters, appearances or match clocks. Team match
statistics have no minutes field and receive no per-90 values. Per-90 rates for
short appearances can be large and do not predict a player's full-match output.

All operands come from one row, source and reported period. No player aliases,
fixtures or opposing-team counts are joined. The provider name labels expected-
value models, without claiming a version or comparability between providers.
Identical column names do not establish identical statistical definitions.
The calculation cannot recover missing provider observations or parser defaults.

| Status | Result |
| --- | --- |
| `calculated` | Finite computed value, including zero |
| `missing_numerator` | Null numerator; denominator is still retained |
| `missing_denominator` | Numerator exists, denominator is null |
| `zero_denominator` | Denominator is zero, including 0 / 0 |
| `inconsistent_inputs` | Completed/on-target count exceeds the reported total |
| `nonfinite_result` | Inputs were finite but the result overflowed |

Missing numerator takes precedence when both inputs are missing. Percentages
are never clipped to fit 0–100. Negative, nonnumeric, boolean and nonfinite
operands raise `ValueError`; unsupported record types raise `TypeError`.

These are row-level calculations, not season aggregation. A season rate should
use compatible season totals and minutes, rather than the mean of match rates.
Deriving metrics does not change `dataset.complete`, errors, cache timestamps,
source values or saved files. Check download and field coverage separately.
Saving the original dataset preserves the inputs, and deriving again after
`open_dataset()` reproduces the results. Calculated fields are not appended to
normalized tables or silently written into snapshots.

```console
python examples/datasets/derived_statistics.py
python examples/datasets/derived_statistics.py --json
python examples/datasets/derived_statistics.py --pandas
python examples/datasets/derived_statistics.py --open-dir ./my-data/champions --table player_match_stats --match-id 401915310
```

Without `--open-dir`, the example uses invented observations. Opening a snapshot
requires `[parquet]`; displaying frames independently requires `[pandas]`. The
CLI rejects match filters on player-season statistics. JSON mode prints row
calculations only; inspect the dataset separately for original task coverage.
