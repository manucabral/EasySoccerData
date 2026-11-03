# Changelog

## [0.1.0] - 2026-11-03

### Added

- **Goaloo module** (`esd.goaloo`): leagues, matches, standings and seasons.
- Goaloo head-to-head history and recent form (`get_h2h`, `get_last_matches`).
- Goaloo odds distributions: Asian handicap and over/under (`get_asian_handicap`, `get_over_under`).
- Goaloo home/away standings and goal timings (`get_home_standings`, `get_away_standings`, `get_goal_timings`).
- Goaloo live match score, live odds and match events (`get_match_score`, `get_live_odds`, `get_match_events`).
- Shared typed source exceptions (`esd.exceptions`: `SourceBlocked`, `SourceNotFound`, `SourceError`).
- Optional `proxies` argument across clients.

### Changed

- **HTTP layer**: unified timeout, proxy and typed error handling across `httpx` and `curl_cffi` paths.
- FBref: headful Playwright fallback on system Chrome to pass Cloudflare, with a refreshed impersonation target.
- Sofascore: `SourceBlocked` raised on 403 instead of a silent empty dict.

### Fixed

- Promiedos `MatchStats` fields defaulted to the class instead of an instance.
- FBref `MatchDetails` and `TableDetails` dataclass `default_factory` bugs and unguarded table parsers.
- `is_available_date` date-format mismatch.
- Sofascore search with `EntityType.ALL` parsed events with the wrong parser.
- Sofascore `get_match_shots` inconsistent return type.
- Missing `beautifulsoup4` dependency declared.

### Removed

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
