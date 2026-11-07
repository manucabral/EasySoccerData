# Examples

Dataset examples target the unreleased 0.2.0 checkout. From the repository root:

```sh
python -m pip install -e .
python examples/datasets/providers.py --list
```

Add `".[pandas]"` for DataFrames, `".[parquet]"` for snapshots or `".[full]"`
for both. The base library and identity-linking helpers require neither extra.

## Offline examples

These scripts do not contact a provider or launch a browser. Most use artificial
records or mocked responses. The Champions League analysis reads your saved
snapshot. Temporary-file examples clean up after themselves.

| Script | Extra | Behavior shown |
| :--- | :--- | :--- |
| [Provider contracts](datasets/providers.py) with `--list` | Base | All nine sources and supported tables |
| [Discovery selectors and cache](datasets/discovery_offline.py) | Base | ESPN slugs, native season IDs, source labels and cache provenance |
| [Discovery support](datasets/discover.py) with `--list` | Base | Implemented competition and season query modes for all nine providers |
| [Discovery workflow](datasets/discovery_workflow_offline.py) | Base | Artificial discovery, exact native selection, download and validation |
| [Discovery workflow](datasets/discovery_workflow_offline.py) with `--parquet` | Parquet | Same flow, temporary snapshot verification and offline reopening |
| [Partial results](datasets/partial_results.py) | Base | `raise`, `collect`, attached records and failed days |
| [Dataset validation](datasets/validate_dataset.py) | Base | Errors, warnings, nullable scores, partial downloads and duplicate keys |
| [Cache reuse](datasets/cache_resume_offline.py) | Base | First download, disk reuse, original timestamps and forced refresh |
| [Match linkage](datasets/link_matches.py) | Base | Explicit competition/team mappings and ambiguous candidates |
| [Native models to DataFrames](pandas/matches_and_standings.py) | pandas | Flattening, nullable scores and ID joins |
| [Common provider tables](pandas/normalized_tables.py) | pandas | ESPN/365Scores columns and source-local identifiers |
| [Dataset analysis](pandas/dataset_analysis.py) | pandas | Unknown scores, UTC dates and validated team joins |
| [Snapshot round trip](datasets/parquet_roundtrip.py) | parquet | Save/open without pandas or network access |
| [Champions League analysis](pandas/champions_analysis.py) | pandas + parquet | Read a saved snapshot and summarize finished matches by team ID |

Run the applicable set with network and browser calls blocked:

```sh
python scripts/check_examples.py --extra base
python scripts/check_examples.py --extra full
```

Install the matching extras before choosing `pandas`, `parquet` or `full`.
The Champions League analysis needs a snapshot path. The runner checks its
`--help` in every environment without requiring optional packages or a file.

### Analyze a saved Champions League snapshot

After exporting matches with `datasets/champions_league.py --output-dir`, run:

```sh
python -m pip install -e ".[pandas,parquet]"
python examples/pandas/champions_analysis.py "./my-data/champions-snapshot-1"
```

`[full]` includes both dependencies. Analysis reads the snapshot without source
requests or new files. It lists matches by UTC kickoff, keeping unknown scores
as `<NA>`, and prints a team summary for the saved date range. The summary shows
played, wins, draws, losses, goals for, goals against and goal difference.

Only 365Scores status group `4` is counted as finished. Both scores must be
known and nonnegative, and both teams must have distinct native IDs. Other
matches remain in the fixture list, with counts explaining their exclusion from
the summary. Team names are display labels. Grouping uses `(source, team_id)`,
so two teams with the same name remain separate.

Results compare the stored goals. They do not determine shootout winners or
qualification. The summary covers only the matches in the file and is not the
official Champions League standings. A partial snapshot still produces a summary,
reports its saved errors on stderr and exits with `1`. Complete snapshots,
including empty ones, return `0`. Invalid snapshots or missing extras return `2`.

To read the same records without pandas, keep only the Parquet extra and run:

```sh
python examples/datasets/champions_league.py --open-dir "./my-data/champions-snapshot-1"
```

Or iterate over `esd.open_dataset(path).match_records` in Python. That path
requires PyArrow and does not import pandas.

### Compare Champions League providers

[champions_compare.py](datasets/champions_compare.py) compares 365Scores competition
`572` with ESPN `uefa.champions`, using normalized records without pandas.
The default selection is November 3-4, 2026 in UTC. The included
[identity file](datasets/champions_identities.json) contains explicit competition
and team mappings checked against both sources on November 7, 2026 for that
selection. It is an example map, not a complete club catalogue. Review it when
changing dates or provide your own JSON list with `--identities`.

```sh
python examples/datasets/champions_compare.py
python examples/datasets/champions_compare.py --cache-dir "./my-data/champions-responses"
python examples/datasets/champions_compare.py --start-date 2026-11-03 --end-date 2026-11-04 --season 2026 --espn-season 2026 --identities "./examples/datasets/champions_identities.json"
```

The selected range is one to seven inclusive UTC days. 365Scores fetches each
selected day. ESPN also fetches one boundary day before and after the range,
then filters kickoff times in UTC and deduplicates native match IDs. A two-day
selection therefore makes six daily queries before transport retries. ESPN's
source season is validated with `--espn-season`; `--season` is the 365Scores
caller label. No full-season calendar or match-detail requests are made.

Links require mapped competition IDs, ordered home/away team IDs and a unique
kickoff candidate within `--tolerance-seconds` (default `300`). Names and scores
do not establish identity. Missing mappings, unknown kickoff times, swapped
teams or schedule changes outside tolerance leave matches unresolved. Multiple
candidates remain ambiguous. Partial mappings can still produce some links.

The report lists linked, unmatched and ambiguous native match IDs separately.
Each link retains both sources' kickoff, score and native status. Score comparison
is `equal`, `different` or `unknown` when either source lacks a score. Equal raw
scores do not prove equivalent match states or penalty conventions. The report
also includes each loader's time window and original response fetch timestamps
per task, including cache hits. Those timestamps are not per-match provenance.

To save both datasets and repeat the comparison without network access:

```sh
python -m pip install -e ".[parquet]"
python examples/datasets/champions_compare.py --cache-dir "./my-data/champions-responses" --output-dir "./my-data/champions-pair-1"
python examples/datasets/champions_compare.py --open-dir "./my-data/champions-pair-1"
```

The new output directory contains `scores365/` and `espn/` snapshots,
`identities.json` and `comparison.json`. Both snapshots, including partial errors,
are staged before publishing the pair. Existing paths are not overwritten.
Opening a pair recomputes links using the saved aliases and tolerance. Use
`--identities` or `--tolerance-seconds` to override those values offline.
Download options cannot be combined with `--open-dir`.

The cache needs only the base installation. `--refresh` fetches all selected
and boundary days again. Parquet storage needs PyArrow, independently of pandas.
Exit code `0` means both downloads completed, even if records differ or remain
unlinked. `1` means a source query failed and the report contains partial results.
Invalid arguments, mismatched snapshot ranges or storage failures return `2`.
Import and `--help` work without source requests or optional packages.

## Live dataset queries

### Discover selectors before loading data

```sh
python examples/datasets/discover.py --list
python examples/datasets/discover.py --source espn --query Champions
python examples/datasets/discover.py --source espn --seasons --competition-id uefa.champions
python examples/datasets/discover.py --source scores365 --query Champions
python examples/datasets/discover.py --source scores365 --seasons --competition-id 572
python examples/datasets/discover.py --source goaloo --seasons --competition-id 36
python examples/datasets/discover.py --source sofascore --category-id 1
python examples/datasets/discover.py --source promiedos --date 2026-11-07
python examples/datasets/discover.py --source besoccer --seasons --competition-id champions
python examples/datasets/discover.py --source transfermarkt --query Champions --page 2
python examples/datasets/discover.py --source transfermarkt --seasons --competition-id CL --competition-url https://www.transfermarkt.com/uefa-champions-league/startseite/pokalwettbewerb/CL
```

Except for `--list` and `--help`, these commands query a provider. Each discovery
call reads one response. `--cache-dir ./my-data/discovery` enables persistent
response reuse; `--refresh` fetches again. Neither requires pandas or PyArrow.
Unsupported operations report `DiscoveryNotSupported` with exit code `1`, as
do source blocks and transport errors. Invalid arguments return `2`.

The output distinguishes the selector accepted by dataset loaders from ESPN's
numeric competition ID, and native season IDs from year labels. It includes scope,
original UTC fetch time and provider-specific notes. 365Scores may include only
the current season in competition details. Promiedos lists leagues on the supplied
day. No operation claims an exhaustive catalogue of all competitions or history.
Read the [discovery guide](../guides/datasets.md#discover-competitions-and-seasons)
before passing selectors to dataset loaders.

BeSoccer's year option can use `2027` for `2026-27`; pass its explicit year to
standings selection. Transfermarkt's `source_url` retains the league/cup route
needed for season discovery. Its season index does not make entity snapshots
historical. FBref and Understat discovery still require manual selection: their
HTML contracts could not be verified through the blocked/maintenance responses.

### Discover, download, validate and store

[discover_and_download.py](datasets/discover_and_download.py) uses 365Scores with
an exact competition ID, an explicitly chosen native season ID and at most seven
UTC days. First inspect the currently returned seasons:

```sh
python examples/datasets/discover.py --source scores365 --seasons --competition-id 572
python examples/datasets/discover_and_download.py --season-id 74 --start-date 2026-11-03 --end-date 2026-11-04 --cache-dir ./my-data/responses
python examples/datasets/discover_and_download.py --season-id 74 --output-dir ./my-data/champions-verified
python examples/datasets/discover_and_download.py --open-dir ./my-data/champions-verified
```

`74` was the returned Champions League native season ID during verification on
November 7, 2026. Choose an ID from your own discovery response. The caller year
label is separate, set with `--season` (default `2026`), and dates select matches.
The example checks that both requested IDs were actually returned before loading.

Downloads and validation use the base install. Saving and opening require
`[parquet]`; missing PyArrow and existing destinations fail before HTTP. Quality
errors prevent saving. A partial download may be saved with its source errors
and returns `1`. A saved snapshot is reopened and compared with the downloaded
dataset. `--open-dir` makes no source requests. Invalid arguments return `2`.

Run the same workflow with artificial responses and temporary files:

```sh
python examples/datasets/discovery_workflow_offline.py
python examples/datasets/discovery_workflow_offline.py --parquet
```

### Champions League: a short date range

[champions_league.py](datasets/champions_league.py) downloads matches for two UTC
days using the base installation. It prints IDs, kickoff times, teams, scores and
source statuses. Downloads do not require pandas or PyArrow. Files are written
only with `--cache-dir` or `--output-dir`.

```sh
python examples/datasets/champions_league.py
python examples/datasets/champions_league.py --start-date 2026-11-03 --end-date 2026-11-04 --season 2026
```

The default dates are November 3-4, 2026. Both bounds are inclusive, with a maximum
of seven days per call. The competition ID is `572` for the Champions League;
`332` is a separate qualifying competition. `--season` labels the records; the
date range selects the matches. Kickoff times use UTC; status codes come from 365Scores.
An unknown score is printed as `?`, and zero stays zero.

Choose a response cache directory to reuse valid responses across runs:

```sh
python examples/datasets/champions_league.py --cache-dir "./my-data/champions-responses"
python examples/datasets/champions_league.py --cache-dir "./my-data/champions-responses"
python examples/datasets/champions_league.py --cache-dir "./my-data/champions-responses" --refresh
```

The second run reports how many days came from cache. Successful days are reused
while fresh; failed or expired days are requested again. Cached responses keep
their original fetch times. `--refresh` fetches every selected day again and
replaces cache entries after validation. A failed refresh leaves an existing
entry intact and reports the failure.

To save the normalized records for later use, install the Parquet extra from
the checkout and choose a new snapshot directory:

```sh
python -m pip install -e ".[parquet]"
python examples/datasets/champions_league.py --cache-dir "./my-data/champions-responses" --output-dir "./my-data/champions-snapshot-1"
python examples/datasets/champions_league.py --open-dir "./my-data/champions-snapshot-1"
```

`[full]` also includes Parquet support. pandas is not needed for saving or opening
snapshots. Each snapshot contains `matches.parquet`, `teams.parquet` and a
`manifest.json` with coverage, errors and checksums. The output directory must
not exist. Choose a new path for each export, even when using `--refresh`.

The response cache avoids repeating source requests. A snapshot stores the
normalized dataset at export time, including empty or partial results.
`--open-dir` reads that snapshot without querying 365Scores or updating the cache.
It cannot be combined with dates, season, cache, refresh or output options.
The displayed date range comes from the saved metadata.

The same snapshot can be opened in Python without network access:

```py
import esd

dataset = esd.open_dataset("./my-data/champions-snapshot-1")
print(dataset.complete, dataset.errors)
for match in dataset.match_records:
    print(match.match_id, match.home_team_name, match.away_team_name)
```

If a day fails, the script displays the successful days and reports the failed
tasks on stderr, with exit code `1`. A requested export saves those partial
results and their errors. Opening that snapshot also returns `1`. A complete
request or snapshot returns `0`, including an empty selection. Invalid arguments,
missing PyArrow, and snapshot read/write failures return `2`. `--help` works offline.

### Other provider queries

`datasets/providers.py` runs one query. `--list` and `--help` work offline;
otherwise it makes network requests. Use the selection flags to replace the
sample IDs and dates. A provider may no longer serve the sample dates.

```sh
python examples/datasets/providers.py --source espn --league eng.1 --season 2024 --preview 2
python examples/datasets/providers.py --source scores365 --league 7 --season 2024 --start-date 2024-08-16 --end-date 2024-08-18
python examples/datasets/providers.py --source sofascore --league 17 --season 2024 --season-id 61627 --max-pages 100
python examples/datasets/providers.py --source understat --tables player_stats --preview 2
python examples/datasets/providers.py --source fbref --tables match_stats --source-timezone UTC
python examples/datasets/providers.py --source goaloo --source-season 2024-2025 --source-timezone Asia/Shanghai
python examples/datasets/providers.py --source promiedos --league hc --start-date 2026-11-06 --end-date 2026-11-06 --source-timezone America/Argentina/Buenos_Aires
python examples/datasets/providers.py --source besoccer --tables standings
python examples/datasets/providers.py --source transfermarkt --tables players market_values transfers --player-ids 418560
```

Set `--source-timezone` to the zone used by the source's naive timestamps.
The UTC and Asia/Shanghai values above illustrate the flag syntax.
IANA names require system timezone data or `python -m pip install tzdata`.

`--cache-dir C:/data/esd/responses` selects persistent response storage.
`--refresh` bypasses cached responses. `--output C:/data/esd/snapshot-1` writes
a new Parquet snapshot and needs the parquet extra; the destination must not exist.
On Linux/macOS use paths such as `/home/me/data/esd/responses` instead.
Check `complete` and `errors` before using a saved dataset; snapshots can contain
partial results.

The runner exits with `0` when all requested tasks succeed, `1` for a partial
download and `2` for invalid arguments or a failed requested snapshot write.
`--on-error raise` stops at the first failed task and reports its partial dataset;
the default `collect` continues. No files are written without an explicit cache
or output path.

## Individual clients

These folders contain source-specific examples. Importing a script makes no
requests. Running it directly calls `main()` and queries the provider. Source
blocks are reported with exit code `1`. Sofascore and FBref examples close their
clients on success, early return and source errors.

Live responses and available fields vary. Source blocks or maintenance can
prevent a script from fetching data.

| Provider | Examples |
| :--- | :--- |
| Sofascore | [Matches, standings, players, lineups and shots](sofascore/) |
| FBref | [Schedules, match reports and player statistics](fbref/) |
| Promiedos | [Matches, tournaments, events and lineups](promiedos/) |
| Goaloo | [League metadata and standings](goaloo/league.py) |
| 365Scores | [Matches, details, standings and search](scores365/) |
| Understat | [Matches, player metrics and shots](understat/) |
| Transfermarkt | [Profiles, valuations and transfers](transfermarkt/) |
| ESPN | [Scoreboards, summaries and standings](espn/) |
| BeSoccer | [Matches and standings](besoccer/) |

For configurable providers, scope, error handling and matching rules, read the
[dataset guide](../guides/datasets.md).

## Live provider checks

Run small dataset queries for the nine providers separately from the offline tests:

```sh
python scripts/check_sources.py --output ./my-data/live-checks.json
python scripts/check_sources.py --source espn promiedos --date 2026-11-07
python scripts/check_sources.py --source espn scores365 --check-parquet --output ./my-data/quality-checks.json
python scripts/check_sources.py --snapshot-dir ./my-data/source-samples-1 --output ./my-data/source-samples-1/report.json
```

The default checks select one day, standings table, season response or club.
They do not traverse fixture calendars or fetch individual shot lists. Each provider
runs in its own process, with a default limit of 45 seconds and three HTTP attempts.
`--timeout` and `--max-requests` change those limits. No browser is launched.

The report includes the selection, UTC check times, HTTP statuses, row counts
and source errors. Download `status` remains separate from `validation` and
`storage`. `ok` means the query completed and returned records; `empty` means it
completed without records. Blocks, missing resources, source errors and timeouts
have separate download statuses.

Each returned dataset is checked with `esd.validate_dataset()`. The `validation`
section contains contextual `errors` and `warnings`, with status `passed`,
`warnings`, `failed` or `error` if validation itself raised. A source block can
produce an empty partial dataset with coverage warnings while the download still
reports `blocked`. Missing native IDs are warnings; invalid types, naive kickoffs
and duplicate keys are errors. Native status codes are not interpreted.

`--check-parquet` enables save/open checks and requires the Parquet extra.
The `storage` section compares all record tables, metadata, source errors and
`complete`, including empty and partial results. Each source uses a new snapshot
directory. Temporary snapshots are removed after the run, including when a worker
times out. Their report has `retained=false` and no remaining file path.

`--snapshot-dir` also enables these checks and preserves snapshots under
`<directory>/<source>/`. The supplied root must not exist; no source is queried
if it already exists or PyArrow is unavailable. Successful snapshots remain
available even if other checks fail. Use `esd.open_dataset(path)` to inspect them
without source requests or pandas. A failed storage check does not replace the
download or validation result. Without either flag, storage is `not_requested`.

Exit code `0` requires every download to complete, no validation errors and every
requested storage check to pass. Warnings alone do not change that exit code.
Exit code `1` indicates a download, validation or storage failure. Invalid arguments,
missing PyArrow, an existing snapshot root or a report write failure return `2`.
A successful sample does not establish that every method or historical date works.

The dated FBref sample uses `Europe/London`; Promiedos uses
`America/Argentina/Buenos_Aires`. These are the timezone assumptions of these
queries. On systems without IANA timezone data, install `tzdata` before running
them. pandas is not required. Base checks require no PyArrow; snapshot checks
need `python -m pip install -e ".[parquet]"` or `".[full]"`. A JSON report is
written only with `--output`. The checks do not run as part of ordinary CI.
