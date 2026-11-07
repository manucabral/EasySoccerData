# Dataset guide

This guide describes the unreleased 0.2.0 source checkout. Run commands from
the repository root after `python -m pip install -e .`. The base installation
returns records. Add pandas for DataFrames or PyArrow for Parquet files.

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
| Player-season statistics | `player_stat_records` | `player_stats` | Understat |
| Shots | `shot_records` | `shots` | Understat |
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

The normalized schema is version `2`. Existing version `1` Parquet snapshots
remain readable: the reader validates their original table schemas and checksums,
adds the new match-statistic columns as null and returns version `2` records.
Source timestamps, IDs, values, errors and coverage are retained. Saving the
opened dataset writes version `2`; the original snapshot is not changed.

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
that you have checked. The library has no built-in alias catalogue and does not
infer identities from names, source IDs or scores.

Store your own aliases wherever your application needs them. For example, a
JSON list can contain objects with `kind`, `canonical_id`, `source`, `source_id`:

```py
import json
from pathlib import Path

aliases = json.loads(Path("./my-data/identities.json").read_text(encoding="utf-8"))
identities = esd.IdentityMap(esd.EntityAlias(**item) for item in aliases)
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
their native coordinate system. Player identity linkage is not implemented.

Run [the offline linkage example](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/datasets/link_matches.py) for an
identity map and an ambiguous case, or
[the pandas analysis example](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/pandas/dataset_analysis.py) for nullable
scores and validated team joins.

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
