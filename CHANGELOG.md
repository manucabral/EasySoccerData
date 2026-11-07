# Changelog

## [Unreleased]

## [0.2.0] - 2026-11-06

### Fixed

- Package metadata now declares MIT, matching the repository license.
- Unknown or null event status data uses short cache freshness instead of raising during TTL evaluation.
- Parquet snapshots reopen UTC timestamps without pandas, pytz or a timezone database on Windows.
- FBref: preserve native match/team/competition context and parse match scores separately from penalty shootout numbers.
- Promiedos normalization: use raw source dates with an explicit timezone instead of the host-dependent parsed timestamp, preserving native status codes.
- BeSoccer datasets: filter adjacent-day fixtures and detect mismatched canonical date pages.
- 365Scores: filter games locally when the source ignores the requested competition ID.
- ESPN: assign match statistics and rosters by team ID or home/away metadata before falling back to list order, preserving away-first payloads.
- Browser sessions: close pages when initialization fails and preserve the original error if cleanup also fails.

### Changed

- ESPN request delays apply only to source fetches. Duplicate match and team observations prefer the original response fetch timestamp, preserving newer results across cached downloads.

### Added

- Installed-wheel checks for base, pandas, parquet and full environments across Python 3.9–3.13 on Linux and Windows in CI.
- Dataset plans for FBref, Goaloo, Promiedos, BeSoccer and Transfermarkt, bringing explicit dataset contracts to all nine providers.
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
- Optional DataFrame flattening, nullable type inference, explicit column types and UTC date conversion in `to_dataframe`, with the original defaults preserved.
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
- FBref: headful Playwright fallback on system Chrome to pass Cloudflare, with a refreshed impersonation target.
- Sofascore: `SourceBlocked` raised on 403 instead of a silent empty dict.
- Enforce Ruff `FA102` (`flake8-future-annotations`) to guarantee PEP 604 type union compatibility on Python 3.9.
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
- AI-style punctuation (em dashes and semicolons) from code and docstrings.

## [0.0.9] - 2026-05-09

### Changed

- **Build system**: migrated from `setup.py` to `pyproject.toml` (PEP 621).
- **Version management**: `esd/__version__` now reads from package metadata via `importlib.metadata` instead of being hardcoded.
- **HTTP layer**: replaced Playwright (Chromium headless) with `curl-cffi` for Sofascore and Promiedos APIs. Removes ~300 MB browser dependency and bypasses TLS fingerprinting via `impersonate="chrome"`.
- **Dependencies**: `playwright>=1.58.0` replaced by `curl-cffi>=0.7`. Missing deps `lxml` and `httpx` now properly declared.
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
