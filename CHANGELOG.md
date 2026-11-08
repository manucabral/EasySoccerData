# Changelog

## [Unreleased]

### Added

- Sofascore match-event datasets with shared match context, bounded incident/lineup/statistic reads, nullable annulment flags and native incident details. Schema 5 reads schema 1–4 snapshots, leaving unobserved event flags null. Examples cover all three event providers and explicit Champions League selections.
- Normalized ESPN/365Scores match events with native clocks, participant references, nullable IDs and separate shootout counters. Event downloads share selected lineup/player responses, respect request budgets and support cached/offline examples. Schema 4 reads existing schema 1–3 snapshots without fabricating event tables.
- Versioned competition/team catalog with reviewed ESPN/365Scores IDs for Champions League, Premier League and LaLiga, source evidence/dates, explicit native season selections, identity-map integration and caller-owned JSON extensions. Examples cover three competitions across two artificial seasons, cache reuse and snapshots.
- Normalized lineups and player-match statistics for explicit ESPN, 365Scores and Sofascore match IDs, with shared response budgets, nullable roles/metrics, native member/athlete IDs and live/offline examples. Team match totals can be requested alongside them.
- Read-only match-statistics comparisons with explicit identities, absolute metric tolerances, missing/period/model diagnostics, original source provenance and optional DataFrame export. Examples cover offline records and Champions League snapshot pairs.
- Optional native-ID match statistics datasets for ESPN, 365Scores and Sofascore, with bounded endpoint reads, source identity checks, nullable metrics, cache provenance and live/offline examples.
- Transfermarkt competition search pages and native season selectors, BeSoccer standings year discovery, source URLs and a 365Scores discovery/download/validation workflow with optional verified Parquet snapshots.
- Native competition/season discovery for ESPN, 365Scores, Sofascore, Goaloo and dated Promiedos listings, with explicit support for all nine providers, immutable results, source scope and optional response caching.
- Read-only `validate_dataset()` reports for normalized records and coverage across all nine providers, with contextual errors/warnings and no optional dependencies.
- Live source checks now report dataset validation separately from download status, with opt-in Parquet round trips, temporary cleanup and caller-selected snapshot directories.
- Champions League date-range example using the base installation, with UTC bounds, nullable scores and partial-result reporting.
- Persistent response cache and forced refresh flags in the Champions League example, with cached-day counts and failed-day recovery.
- Champions League Parquet export and offline read flags, preserving empty tables, partial coverage and errors without pandas.
- Offline pandas analysis of Champions League snapshots, with UTC fixtures, team-ID summaries and explicit exclusions for unfinished or incomplete results.
- Champions League comparison across 365Scores and ESPN, with explicit sample identities, bounded UTC queries, score/time differences, source timestamps and offline snapshot pairs without pandas.
- Live dataset check command with per-provider time and request limits, structured results and explicit report paths.
- Dataset guide, example index and offline examples of partial results, cache reuse, refresh, nullable analysis and ambiguous match linkage.
- Configurable provider example CLI with selection overrides, record previews, optional snapshot output and explicit exit codes.
- Automated offline example checks across installation extras, with HTTP and browser access blocked.

### Changed

- Normalized schema version 3 includes whole-match team counts, percentage-point possession, source period labels, lineups and player-match statistics with nullable boolean flags. Version 1/2 snapshots remain readable, retaining their original selected tables, values and timestamps.

### Fixed

- 365Scores match-statistics datasets request UTC like calendar queries, avoiding a source-local detail timestamp that prevented otherwise valid cross-source links.
- Installed-example checks can exclude the checkout from imports and require `site-packages`, preventing source files from masking missing wheel modules in CI.
- Transfermarkt search now reads competition grid cells and cup links (`pokalwettbewerb`), which were omitted by the previous link parser.
- Include example identity maps in source distributions so saved-provider comparisons can run from the source archive.
- Promiedos: convert ISO query dates to the source's `DD-MM-YYYY` URL format in clients and dataset loaders.
- BeSoccer: raise `SourceBlocked` when a browser challenge persists and keep that response out of the cache.
- Live examples: defer queries until execution, handle empty selections and unavailable statistics, select named entities by native ID and close Sofascore/FBref clients on errors and early returns.
- Replace predicted live example output with descriptions of the requested data and correct incomplete API descriptions.
- Documentation generation targets local sources and treats warnings as errors, preventing missing README includes from silently passing.
- API documentation clarifies task coverage, source timestamps, entity scopes and compatibility preconditions.

## [0.2.0] - unreleased

### Fixed

- Package metadata now declares MIT, matching the repository license.
- Unknown or null event status data uses short cache freshness instead of raising during TTL evaluation.
- Parquet snapshots reopen UTC timestamps without pandas, pytz or a timezone database on Windows.
- FBref: preserve native match/team/competition context and parse match scores separately from penalty shootout numbers.
- Promiedos normalization: use raw source dates with an explicit timezone instead of the host-dependent parsed timestamp, preserving native status codes.
- BeSoccer datasets: filter adjacent-day fixtures and detect mismatched canonical date pages.
- 365Scores: filter games locally when the source ignores the requested competition ID.
- ESPN: assign match statistics and rosters by team ID or home/away metadata before falling back to list order, handling away-first payloads.
- Browser sessions: close pages when initialization fails and preserve the original error if cleanup also fails.

### Changed

- ESPN request delays apply only to source fetches. Duplicate match and team observations prefer the original response fetch timestamp, preserving newer results across cached downloads.

### Added

- Installed-wheel checks for base, pandas, parquet and full environments across Python 3.9–3.13 on Linux and Windows in CI.
- Dataset plans for FBref, Goaloo, Promiedos, BeSoccer and Transfermarkt, covering all nine providers.
- Transfermarkt current profiles, full valuation/transfer histories and caller-selected entities, with optional DataFrames and Parquet snapshots.
- Explicit identity maps, compatibility inspection and one-to-one cross-source match linkage with unmatched/ambiguous results, without pandas or automatic name matching.
- Dataset loaders for 365Scores UTC date ranges, Sofascore native-season pagination and Understat season matches, xG, player statistics and opt-in shots.
- Source capability discovery, explicit task coverage and provider selection metadata, preserved through cache reuse and Parquet snapshots.
- Sofascore and Understat normalized adapters, nullable metric schemas and offline provider-contract regression tests.
- Caller-selected persistent JSON response caches with atomic replacement, corruption checks and cache cleanup, requiring no optional dependencies.
- ESPN download resume and incremental updates with configurable calendar/live/upcoming/recent/historical/standings freshness, forced refresh and cache-aware progress.
- Parquet snapshot save/open with versioned manifests, preserved metadata and partial errors, fixed schemas, checksums and staged writes to new directories.
- Independent parquet extra for PyArrow, offline round-trip examples and tests confirming file storage works without pandas.
- Full extra combining all optional runtime features, with pandas and PyArrow kept out of the base installation.
- ESPN season datasets with daily and stage calendar discovery, sequential downloads, deduplication, progress callbacks, normalized records and explicit partial-result errors.
- Strict ESPN season validation for dataset scoreboards and standings, calendar coverage metadata and lazy DataFrame tables.
- Common match, team and standings records with opt-in ESPN and 365Scores adapters, source-local identifiers, UTC kickoffs and preserved table/stage/group context.
- Normalized DataFrame export with versioned columns and fixed nullable types for populated and empty tables, plus offline examples and adapter tests.
- Optional DataFrame flattening, nullable type inference, explicit column types and UTC date conversion in `to_dataframe`, with unchanged defaults.
- Offline pandas examples for matches, standings and team ID joins, plus DataFrame tests and CI installation of the pandas extra.
- Offline regression tests for ESPN team assignment and browser page cleanup.
- HTTP transport tests for request options, permanent errors, transient retries, retry exhaustion, invalid JSON and error payloads across httpx and curl_cffi.

## [0.1.0] - 2026-11-06

### Added

- **Goaloo module** (`esd.goaloo`): leagues, matches, standings, seasons, head-to-head history, recent form, Asian handicap and over/under odds, home/away standings, goal timings, live match score, live odds and match events.
- **365Scores module** (`esd.scores365`): daily and live games, match details with events and lineups, team statistics, competition standings and entity search.
- **Understat module** (`esd.understat`): league and team matches with Expected Goals (xG) and win forecasts, player xG/xA statistics, team match-by-match xPTS histories and pitch shotmaps with coordinates.
- **Transfermarkt module** (`esd.transfermarkt`): player profiles, current and historical market value progressions, complete transfer histories, club squad valuations and entity search.
- **ESPN module** (`esd.espn`): live scoreboards across international leagues, full match summaries (boxscore stats, rosters, timeline events and commentary), league standings and club lists.
- **BeSoccer module** (`esd.besoccer`): daily livescore matches and competition standings tables.
- Top-level exports in `esd`: `Scores365Client`, `UnderstatClient`, `TransfermarktClient`, `ESPNClient`, `BeSoccerClient`, `fetch_many` and `to_dataframe`.
- Shared typed source exceptions (`esd.exceptions`: `SourceBlocked`, `SourceNotFound`, `SourceError`).
- Optional `proxies` argument across clients.
- Automated unit test suite under `tests/` executed in CI across Python 3.9 to 3.13.
- Usage examples in `examples/` for Goaloo, 365Scores, Understat, Transfermarkt, ESPN and BeSoccer.

### Changed

- **HTTP layer**: unified timeout, proxy and typed error handling across `httpx` and `curl_cffi` paths.
- FBref: optional Playwright fallback using installed Chrome, with a refreshed HTTP impersonation target.
- Sofascore: `SourceBlocked` raised on 403 instead of a silent empty dict.
- Enable Ruff `FA102` to require postponed annotations for PEP 604 unions on Python 3.9.
- `esd.utils.get_text` now accepts custom `impersonate` targets.

### Fixed

- Added `from __future__ import annotations` across all modules using PEP 604 union syntax for Python 3.9 compatibility.
- `esd.utils._get_httpx_client`: pass `proxy` keyword argument compatible with `httpx>=0.28`.
- Promiedos: `MatchStats` default factory fix, avoid mutating cached events in `get_events` and guard missing `start_time` against Windows epoch `OSError`.
- FBref: `MatchDetails` and `TableDetails` dataclass `default_factory` fixes, table parsers, HTML comment XPath lookup and unified rate limiting.
- `is_available_date` date-format mismatch.
- Sofascore: fix `EntityType.ALL` event parser, `get_match_shots` return type, mutable default arguments, URL-encode search queries and guard empty payloads and null timestamps.
- Goaloo: strip UTF-8 BOM in JSON responses and allow empty standings.
- BeSoccer: prioritize live match clock/status in `time_display` before falling back to marker text.

### Performance

- Persistent HTTP session reuse across requests (connection pooling).
- Bounded `TTLCache` with LRU eviction (`maxsize=256`).
- `fetch_many` helper to fetch multiple entities in parallel.
- Retry with exponential backoff and jitter on transient failures.
- Sofascore: parallelize composite fetches in `get_match_stats` and `get_top_tournament_players`.
- Goaloo: cache parsed team map and reuse H2H page across calls.
- Skip redundant browser warmup in `BrowserSession` when the target domain is already warmed.

### Removed

- Unused `beautifulsoup4` dependency.

## [0.0.9] - 2026-05-09

### Changed

- **Build system**: migrated from `setup.py` to `pyproject.toml` (PEP 621).
- **Version management**: `esd/__version__` now reads from package metadata via `importlib.metadata` instead of being hardcoded.
- **HTTP layer**: replaced Playwright (Chromium headless) with `curl-cffi` for Sofascore and Promiedos APIs. Uses `impersonate="chrome"` for the HTTP browser fingerprint.
- **Dependencies**: `playwright>=1.58.0` replaced by `curl-cffi>=0.7`. Declare `lxml` and `httpx` as dependencies.
- **CI/CD**: workflows updated to use `pyproject.toml`-based builds (`python -m build`) and `ruff` instead of `pylint`.
- **Type safety**: all string fields in `Team` dataclass default to `""` instead of `None`, preventing `TypeError` on `len()`.
- **Public API**: `SofascoreClient()` no longer requires `browser_path` param; `close()` removed.

### Added

- `esd.utils.get_api_json(url, headers)`: shared helper for curl_cffi API calls.
- `esd.sofascore.*`, `esd.fbref.*`, `esd.promiedos.*` now re-export all types directly (e.g. `esd.sofascore.EntityType`).
- `[project.optional-dependencies] dev` with `pytest`, `ruff`, `build`.
- `tests/` directory placeholder.
- `[tool.ruff]` and `[tool.pytest.ini_options]` in `pyproject.toml`.
- Development section in `README.md`.

### Fixed

- `setup.py` had typo `clasisfiers=` → `classifiers` (never applied to PyPI).
- `setup.py` had `License :: OSI Approved :: MIT` but package declared GPL-3.0 → corrected.
- `esd/__init__.py` docstring had `"for for fetching"` → `"for fetching"`.
- `typing.Dict` and `typing.Union` replaced with modern `dict` and `|` syntax.
- 37+ files: import ordering standardized with `ruff --fix`.

### Removed

- `setup.py` (replaced by `pyproject.toml`).
- Module-level `__author__`, `__title__`, `__license__`, `__description__` from `esd/__init__.py`.
- Playwright initialization, browser management, and cleanup from `esd/sofascore/service.py` (~170 lines).
