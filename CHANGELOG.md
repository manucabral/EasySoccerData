# Changelog

## [0.2.0] - 2026-11-08

### Added

- Row-level derived statistics (`derive_statistics`, `derived_statistics_to_dataframe`) retain formulas, observed inputs and null reasons for player per-90 rates, pass/shot accuracy and source-model xG per shot. JSON works in the base installation, with independent optional pandas frames and offline/snapshot examples. Original normalized rows and schema remain unchanged.
- Selective snapshot reads (`open_dataset(..., tables=..., match_ids=...)`) filter by table and native match ID with batched decoding, full file checksum verification and preserved download provenance (`original_tables`, `snapshot_match_ids`).
- Read-only field contracts (`get_dataset_field_capabilities`) for all nine dataset providers, with nullable types, unavailable columns and source-specific model/coordinate labels. Coverage inspection (`inspect_dataset_coverage`) separates normalized non-null/missing/zero/False counts from per-table task outcomes, retaining errors, cache dates and query scope without optional dependencies.
- Reviewed catalog `2026-11-08.1` (`get_catalog`, `open_catalog`) covers five competitions (Champions League, Premier League, LaLiga, Bundesliga and Serie A) and 96 team identities across ESPN, 365Scores and Sofascore, with source evidence/dates, explicit native season selection (`list_seasons`, `dataset_options`), `IdentityMap` integration and caller-owned JSON extensions.
- Scoped player aliases (`EntityAlias` with native `team_id`, `valid_from`, `valid_until`, `source_url`, `verified_at`) and `IdentityMap.lookup()` diagnostics (`resolved`, `unmapped`, `context_required`, `out_of_scope`) round-tripping through versioned JSON.
- Normalized Sofascore shots (`shotmap`) retain native player coordinates, body part, xG/xGOT and raw details, and ESPN recognized attempts (`keyEvents`/`commentary.play`) retain native field positions without inferred xG. Schema 6 reads schema 1-5 snapshots against their original schemas, preserving existing values and leaving new unobserved columns null.
- Integrated Champions League workflow (`examples/datasets/champions_workflow.py`) connecting explicit season discovery, shared-endpoint downloads of matches/teams/statistics/lineups/events, field and task coverage inspection, Parquet snapshot storage, selective reopening by table and match ID, derived statistics and pairwise provider comparisons.
- Provider limitations summary in `guides/datasets.md` documenting discovery support, available tables, unavailable columns and derived-metric status reasons across all nine sources.
- Read-only cross-source and same-source comparators for match statistics (`compare_match_statistics`), lineups and player-match metrics (`compare_match_players`), and match events (`compare_match_events`) across ESPN, 365Scores and Sofascore, including opt-in `allow_unknown_period` handling for unverified event periods.
- Normalized `match_events`, `lineups`, `player_match_stats` and native-ID `match_stats` detail loaders and raw adapters (`normalize_match_events`, `normalize_match_players`, `normalize_match_shots`) for ESPN, 365Scores and Sofascore with shared endpoint budgets and task-level cache timestamps.
- Competition and season discovery (`get_discovery_capabilities`, `list_competitions`, `list_seasons`) across ESPN, 365Scores, Sofascore, Goaloo, Promiedos, BeSoccer and Transfermarkt, with explicit `DiscoveryNotSupported` for unverified routes.
- Read-only `validate_dataset()` structural, referential and coverage validation across all nine providers without optional dependencies.
- Top-level `SCHEMA_VERSION` export on `esd` alongside `esd.normalized`.
- Dataset loaders (`load_dataset`, `get_dataset_capabilities`) for all nine providers: ESPN season calendars and details, 365Scores UTC date ranges and details, Sofascore native-season pagination and details, Understat season matches/xG/player statistics/shots, FBref dated schedules and match xG, Goaloo season fixtures and standings, Promiedos dated fixtures, BeSoccer dated fixtures and standings, and Transfermarkt club/player profiles, market values and transfers.
- Explicit `IdentityMap`, `check_dataset_compatibility` and one-to-one `link_dataset_matches` with unmatched and ambiguous diagnostics.
- Caller-selected persistent JSON `ResponseCache` and `CachePolicy` with atomic replacement, corruption recovery and incremental download resume across all nine loaders.
- Parquet snapshot `dataset.save()` and `open_dataset()` with versioned manifests, SHA-256 checksums and staged directory writes requiring only the independent `[parquet]` extra (`pyarrow`), plus `[pandas]` and `[full]` extras and CI wheel checks across Python 3.9-3.13 on Linux and Windows.
- Optional DataFrame flattening, nullable type inference, explicit column types and UTC date conversion in `to_dataframe()`, plus `normalized_to_dataframe()` with fixed nullable schemas.

### Changed

- Normalized dataset schema advanced through version `6` while keeping version `1`-`5` Parquet snapshots readable with original selected tables, values and timestamps preserved.
- ESPN request delays apply only to network fetches, and duplicate match/team observations retain the newest response fetch timestamp across cached downloads.

### Fixed

- 365Scores lineup and player-statistics normalization now skips anonymous entries in `game["members"]` without an `id` (such as localized disallowed-goal markers), matching event normalization and avoiding `SourceError` on live Champions League games.
- `validate_dataset()` checks `metadata.snapshot_match_ids` on selectively opened snapshots and reports `unrequested_match` when match-scoped records fall outside the snapshot filter.
- Standardized `ValueError` validation across `list_competitions`, `list_seasons`, `CachePolicy`, `load_dataset`, `normalize_match_players`, `check_dataset_compatibility`, `link_dataset_matches` and `compare_match_statistics` for invalid boolean or non-numeric tolerances, delays, TTLs and identity maps.
- Replaced non-UTF-8 bytes in `guides/datasets.md` and moved snapshot-selection and derived-statistics sections out of `# Contributing` in `README.md` and `READMEdoc.md`.
- FBref rate-limit admission is atomic across threads and uses a monotonic clock, preventing concurrent requests from exceeding a shared slot or wall-clock adjustments from resetting its window.
- In-memory response reuse rejects future timestamps and nonfinite lifetimes like the persistent cache.
- Match linkage accepts datasets containing `match_events` through the shared table registry.
- 365Scores match-statistics datasets request UTC like calendar queries, avoiding source-local detail timestamps during cross-source linkage.
- Installed-example checks (`scripts/check_examples.py --installed`) exclude the checkout from imports and require `site-packages`.
- Transfermarkt competition search parses both competition grid cells and cup links (`pokalwettbewerb`), and source distributions include example identity maps.
- Promiedos converts ISO query dates to `DD-MM-YYYY` in clients and dataset loaders and normalizes raw source dates with an explicit timezone.
- BeSoccer raises `SourceBlocked` when a browser challenge persists, keeps blocked responses out of the cache, filters adjacent-day fixtures and detects mismatched canonical date pages.
- FBref preserves native match/team/competition context and parses match scores separately from penalty shootouts.
- 365Scores filters games locally when the source ignores the requested competition ID.
- ESPN assigns match statistics and rosters by team ID or home/away metadata before falling back to list order.
- Parquet snapshots reopen UTC timestamps without pandas, pytz or a system timezone database on Windows.
- Unknown or null event status data uses short cache freshness instead of raising during TTL evaluation.
- Browser sessions close pages when initialization fails and preserve the original error if cleanup also fails.
- Package metadata declares the MIT license, matching `LICENSE`.

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
