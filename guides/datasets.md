# Dataset cookbook

This guide describes the unreleased 0.2.0 source checkout. Run commands from
the repository root after `python -m pip install -e .`. Examples below keep pandas
and PyArrow optional.

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
| Match metrics | `match_stat_records` | `match_stats` | FBref, Understat |
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

`None` means unknown; it is not a score of zero. A score alone does not prove
that a match has finished. Status fields retain native source codes and text.

## Select the source's actual scope

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

## Keep partial results visible

`complete` means that every requested task succeeded. It does not establish that
the season has finished or the provider lists every fixture. An empty successful
selection is different from a failed request returning no records.

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

## Choose storage locations and preserve age

Two paths serve different purposes:

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

`metadata.started_at`/`finished_at` describe the current loader call.
`dict(metadata.response_fetched_at)` preserves original fetch dates per task,
including cached responses; `cached_tasks` identifies reuse. A newly opened
snapshot or a cache hit does not make the source data newer.

`CachePolicy` adjusts freshness. Its date/status rules apply to ESPN/365Scores
daily responses. Other loaders use their documented calendar/live/standings/
historical TTLs. Disk entries are not pruned automatically; `ResponseCache(path).clear()`
removes owned cache entries without deleting snapshot files.

Try [offline cache reuse](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/datasets/cache_resume_offline.py) or
[snapshot round trips](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/datasets/parquet_roundtrip.py).

## Join data without losing identity or scope

Within one provider, join on both `source` and the native ID. Standings can have
several rows for a team across groups/stages/tables: select one table before
expecting a many-to-one join. Do not join standings to matches solely by a team
name, or treat today's standings as standings at each historical kickoff.

Across providers, common columns do not establish common identities. Build an
`IdentityMap` from verified competition/team `EntityAlias` entries. There is no
built-in verified catalogue. Equal names, source IDs or scores are insufficient.

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

Those files are application inputs, not files created by the library. The two
snapshots need the parquet extra to open; compatibility/linkage itself does not.

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
`can_match` checks preconditions; it does not guarantee linked games. `issues`
can include informational source-semantic notes even for compatible schemas.

Linkage preserves inputs and native IDs. It does not harmonize xG models, penalty
conventions, statuses, currencies or pitch coordinates. Understat shots stay in
their native coordinate system. Player identity linkage is not implemented.

Run [the offline linkage example](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/examples/datasets/link_matches.py) for a
complete identity map and an ambiguous case, or
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

Use small date ranges or explicit entity selections while debugging. Ordinary
tests and the offline example runner require no live provider access.
