"""Provider datasets with explicit query coverage and partial download results."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from os import PathLike
from pathlib import Path

from .cache import CachePolicy, ResponseCache, ResponseInfo
from .espn import ESPNClient
from .exceptions import ESDException
from .normalized import (
    SCHEMA_VERSION,
    NormalizedLineup,
    NormalizedMarketValue,
    NormalizedMatch,
    NormalizedMatchEvent,
    NormalizedMatchStats,
    NormalizedPlayer,
    NormalizedPlayerMatchStats,
    NormalizedPlayerStats,
    NormalizedShot,
    NormalizedStanding,
    NormalizedTeam,
    NormalizedTransfer,
    normalize_match,
    normalize_standings,
    normalize_team,
    normalized_to_dataframe,
)


@dataclass(frozen=True)
class DatasetIssue:
    """A failed source request or parsing task, including entity/history queries."""

    step: str
    target: str
    error_type: str
    message: str


@dataclass(frozen=True)
class DatasetProgress:
    """One completed task. Total grows as discovery finds pages or matches."""

    completed: int
    total: int
    step: str
    target: str
    success: bool
    match_count: int
    cached: bool = False


@dataclass(frozen=True)
class DatasetMetadata:
    """Selection, download coverage and original response timestamps.

    source/league identify the queried provider and its native competition.
    season is a caller year label; source_season_id and source_season preserve
    provider selection separately. coverage_scope is season, date_range,
    match_ids or entities. Transfermarkt profiles are current and histories span seasons.

    ESPN reports calendar_dates/successful_dates and calendar_loaded. Other
    loaders report expected_tasks/successful_tasks. Progress totals may grow
    as pages or shot requests are discovered. Neither form proves that the
    source lists every fixture. response_fetched_at pairs task keys with their
    original UTC ISO timestamps; cached_tasks identifies reused responses.
    started_at/finished_at describe this loader invocation, including cache hits.
    """

    source: str
    league: str
    season: int
    tables: tuple[str, ...]
    started_at: datetime
    finished_at: datetime
    calendar_dates: tuple[str, ...] = ()
    successful_dates: tuple[str, ...] = ()
    calendar_loaded: bool = False
    standings_loaded: bool = False
    calendar_name: str | None = None
    calendar_type: str | None = None
    season_start: str | None = None
    season_end: str | None = None
    anchor_date: str | None = None
    schema_version: str = SCHEMA_VERSION
    response_fetched_at: tuple[tuple[str, str], ...] = ()
    cached_tasks: tuple[str, ...] = ()
    expected_tasks: tuple[str, ...] = ()
    successful_tasks: tuple[str, ...] = ()
    coverage_scope: str = "season"
    source_season_id: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    source_timezone: str | None = None
    requested_match_ids: tuple[str, ...] = ()
    source_season: str | None = None
    requested_club_ids: tuple[str, ...] = ()
    requested_player_ids: tuple[str, ...] = ()
    original_tables: tuple[str, ...] = ()
    snapshot_match_ids: tuple[str, ...] | None = None


@dataclass(frozen=True)
class SoccerDataset:
    """In-memory records. DataFrame properties import pandas only on access.

    complete reports whether every requested task succeeded. The provider may
    list an unfinished season or omit fixtures. Standings reflect the source
    table at download time; they are not reconstructed for each matchday.
    """

    metadata: DatasetMetadata
    match_records: tuple[NormalizedMatch, ...] = ()
    team_records: tuple[NormalizedTeam, ...] = ()
    standing_records: tuple[NormalizedStanding, ...] = ()
    errors: tuple[DatasetIssue, ...] = ()
    match_stat_records: tuple[NormalizedMatchStats, ...] = ()
    player_stat_records: tuple[NormalizedPlayerStats, ...] = ()
    shot_records: tuple[NormalizedShot, ...] = ()
    player_records: tuple[NormalizedPlayer, ...] = ()
    market_value_records: tuple[NormalizedMarketValue, ...] = ()
    transfer_records: tuple[NormalizedTransfer, ...] = ()
    lineup_records: tuple[NormalizedLineup, ...] = ()
    player_match_stat_records: tuple[NormalizedPlayerMatchStats, ...] = ()
    match_event_records: tuple[NormalizedMatchEvent, ...] = ()

    @property
    def complete(self) -> bool:
        """True when every requested download task succeeded."""
        meta = self.metadata
        if meta.expected_tasks:
            return not self.errors and set(meta.expected_tasks) == set(meta.successful_tasks)
        coverage_tables = meta.original_tables or meta.tables
        matches_ok = "matches" not in coverage_tables or (
            meta.calendar_loaded and set(meta.calendar_dates) == set(meta.successful_dates)
        )
        standings_ok = "standings" not in coverage_tables or meta.standings_loaded
        return not self.errors and matches_ok and standings_ok

    def _dataframe(self, records, table):
        if table not in self.metadata.tables:
            raise ValueError(f"Table {table!r} was not requested")
        return normalized_to_dataframe(list(records), table=table)

    @property
    def matches(self):
        """Normalized matches as a DataFrame, including an empty typed schema."""
        return self._dataframe(self.match_records, "matches")

    @property
    def teams(self):
        """Teams with source IDs from matches, Goaloo metadata or selected Transfermarkt clubs."""
        return self._dataframe(self.team_records, "teams")

    @property
    def standings(self):
        """Standings snapshot, available only when explicitly requested."""
        return self._dataframe(self.standing_records, "standings")

    @property
    def match_stats(self):
        """Source match totals and optional xG/forecast values with nullable columns."""
        return self._dataframe(self.match_stat_records, "match_stats")

    @property
    def match_events(self):
        """Native match events with nullable clocks, participants and shootout flags."""
        return self._dataframe(self.match_event_records, "match_events")

    @property
    def lineups(self):
        """Listed players, native positions and nullable starter/confirmation flags."""
        return self._dataframe(self.lineup_records, "lineups")

    @property
    def player_match_stats(self):
        """Observed player/team/match metrics, separate from season player_stats."""
        return self._dataframe(self.player_match_stat_records, "player_match_stats")

    @property
    def player_stats(self):
        """Understat player-season aggregations, including native club-name strings."""
        return self._dataframe(self.player_stat_records, "player_stats")

    @property
    def shots(self):
        """Source attempts with native coordinates/models where observed."""
        return self._dataframe(self.shot_records, "shots")

    @property
    def players(self):
        """Transfermarkt profiles as reported at download time, across the selected players."""
        return self._dataframe(self.player_records, "players")

    @property
    def market_values(self):
        """Full valuation histories, retaining native dates and currencies."""
        return self._dataframe(self.market_value_records, "market_values")

    @property
    def transfers(self):
        """Full transfer histories; fee currency is not inferred from display text."""
        return self._dataframe(self.transfer_records, "transfers")

    def save(self, path: str | PathLike, *, format: str = "parquet") -> Path:
        """Write a dataset snapshot to a new directory.

        Requires ``EasySoccerData[parquet]``. Each requested table is written as
        a Parquet file alongside a versioned JSON manifest with metadata,
        errors, row counts, and SHA-256 checksums. Existing paths are never
        overwritten.

        Args:
            path: Target directory path (must not already exist).
            format: Snapshot format; currently only ``"parquet"`` is supported.

        Returns:
            Path: The resolved ``Path`` of the saved snapshot directory.

        Raises:
            ImportError: If ``pyarrow`` is not installed.
            ValueError: If ``format`` is unsupported or records fail schema checks.
            FileExistsError: If ``path`` already exists.
            DatasetFormatError: If an I/O failure prevents publishing the snapshot.
        """
        from ._dataset_storage import save_dataset

        return save_dataset(self, path, format=format)


class DatasetFormatError(ESDException):
    """A saved dataset is invalid, damaged or uses an unsupported schema."""


def open_dataset(
    path: str | PathLike, *, tables: Sequence[str] | None = None,
    match_ids: Sequence[str] | None = None,
) -> SoccerDataset:
    """Read a saved Parquet dataset snapshot without network access.

    Requires ``EasySoccerData[parquet]``. Validates the manifest, versions,
    table schemas, row counts, and SHA-256 checksums for every stored file,
    including omitted tables. Selected rows are decoded without importing
    ``pandas``.

    Args:
        path: Directory containing a saved dataset snapshot.
        tables: Optional non-empty subset of stored table names to load.
        match_ids: Optional sequence of native match IDs used to filter tables
            that carry a ``match_id`` column. Tables without ``match_id``
            remain unchanged.

    Returns:
        SoccerDataset: A dataset with original coverage metadata preserved
            (``metadata.original_tables`` and ``metadata.snapshot_match_ids``
            record any local filter).

    Raises:
        ImportError: If ``pyarrow`` is not installed.
        ValueError: If ``tables`` or ``match_ids`` are invalid or request
            tables that were not stored in the snapshot.
        DatasetFormatError: If the snapshot is missing, corrupted, or uses an
            unsupported schema version.
    """
    from ._dataset_storage import read_dataset

    return read_dataset(path, tables=tables, match_ids=match_ids)


class DatasetLoadError(ESDException):
    """A dataset task failed. dataset contains records and coverage so far."""

    def __init__(self, dataset: SoccerDataset):
        self.dataset = dataset
        issue = dataset.errors[-1]
        super().__init__(f"Dataset {issue.step} failed for {issue.target}: {issue.message}")


def load_dataset(
    *,
    source: str,
    league: str | int,
    season: int | str,
    tables: Sequence[str] = ("matches",),
    proxies: dict | None = None,
    anchor_date: str | None = None,
    on_error: str = "raise",
    progress: Callable[[DatasetProgress], None] | None = None,
    request_delay: float = 0.25,
    cache_dir: str | PathLike | None = None,
    cache_policy: CachePolicy | None = None,
    refresh: bool = False,
    season_id: int | str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    source_timezone: str | None = None,
    match_ids: Sequence[int | str] | None = None,
    max_pages: int = 100,
    source_season: str | None = None,
    club_ids: Sequence[int | str] | None = None,
    player_ids: Sequence[int | str] | None = None,
    max_match_requests: int = 20,
) -> SoccerDataset:
    """Download normalized tables from a single provider.

    Each provider defines its own supported tables and required selection
    arguments; inspect them programmatically with
    ``get_dataset_capabilities(source)`` or build pre-validated arguments from
    the catalog via ``get_catalog().dataset_options(...)``.

    Args:
        source: Provider identifier (``"espn"``, ``"sofascore"``, ``"scores365"``,
            ``"understat"``, ``"fbref"``, ``"goaloo"``, ``"promiedos"``,
            ``"besoccer"``, or ``"transfermarkt"``).
        league: Native competition code or ID for the chosen provider.
        season: Four-digit caller season year label (for example ``2024``).
        tables: Non-empty sequence of normalized table names to download.
        proxies: Optional HTTP/HTTPS proxy mapping passed to the provider client.
        anchor_date: Optional ``YYYY-MM-DD`` or ``YYYYMMDD`` date used by ESPN
            to discover the season calendar window.
        on_error: Error handling mode: ``"raise"`` raises ``DatasetLoadError``
            on the first failed task (attaching partial results on
            ``exc.dataset``), while ``"collect"`` records failures in
            ``dataset.errors`` and returns with ``dataset.complete == False``.
        progress: Optional callback invoked with a ``DatasetProgress`` record
            after each download task completes.
        request_delay: Minimum delay in seconds between sequential requests.
        cache_dir: Optional directory for persistent JSON response caching.
        cache_policy: Optional ``CachePolicy`` overriding default TTLs; requires
            ``cache_dir``.
        refresh: When ``True``, bypasses cached responses and overwrites cache
            entries after successful validation.
        season_id: Native numeric season ID required by ``sofascore`` and by
            ``scores365`` standings or match-detail queries.
        start_date: Inclusive ``YYYY-MM-DD`` start date required by date-range
            loaders (``scores365``, ``fbref``, ``promiedos``, ``besoccer``).
        end_date: Inclusive ``YYYY-MM-DD`` end date required by date-range
            loaders.
        source_timezone: IANA timezone name (such as ``"UTC"`` or
            ``"Europe/London"``) required when normalizing naive provider
            kickoffs (``understat``, ``goaloo``) or local date bounds.
        match_ids: Explicit sequence of native match IDs required for
            match-detail tables (``match_stats``, ``lineups``,
            ``player_match_stats``, ``match_events``, ``shots`` on
            ``espn``/``sofascore``/``scores365``, and ``shots`` on ``understat``).
        max_pages: Maximum pagination pages per direction for ``sofascore``
            season match lists.
        source_season: Native season string required by ``goaloo`` (for example
            ``"2024-2025"``).
        club_ids: Explicit Transfermarkt club IDs when loading club rosters or
            metadata.
        player_ids: Explicit Transfermarkt player IDs when loading player
            profiles, market value histories, or transfer histories.
        max_match_requests: Upper bound on underlying endpoint requests for
            explicit match-detail downloads on ``espn``, ``sofascore``, and
            ``scores365``.

    Returns:
        SoccerDataset: Normalized record tuples, lazy DataFrame properties,
            task coverage metadata, and any collected ``DatasetIssue`` entries.

    Raises:
        ValueError: If provider selection arguments or table combinations are
            invalid.
        DatasetLoadError: If a download or normalization task fails while
            ``on_error="raise"``.
        CacheError: If ``cache_dir`` cannot be read or written.
    """
    from .dataset_capabilities import get_dataset_capabilities
    from .normalized.schema import TABLE_MODELS

    get_dataset_capabilities(source)
    if source != "espn" and type(league) is int:
        league = str(league)
    if not isinstance(league, str) or not league.strip() or league == "all":
        raise ValueError("A single league code or native competition ID is required")
    if isinstance(season, bool) or not str(season).isdigit() or len(str(season)) != 4:
        raise ValueError("season must be a four-digit season year")
    year = int(season)
    if year < 1000:
        raise ValueError("season must be a four-digit season year")
    if isinstance(tables, str) or not tables or any(
        table not in TABLE_MODELS for table in tables
    ):
        raise ValueError("tables must be a nonempty sequence of supported table names")
    players = bool(set(tables) & {"lineups", "player_match_stats"})
    events = "match_events" in tables
    shots = "shots" in tables
    details = source in ("espn", "scores365", "sofascore") and bool(set(tables) & {"match_stats", "lineups", "player_match_stats", "match_events", "shots"})
    if type(max_match_requests) is not int or max_match_requests < 1:
        raise ValueError("max_match_requests must be a positive integer")
    if not details and max_match_requests != 20:
        raise ValueError("max_match_requests applies only to explicit match-detail selections")
    if "teams" in tables and "matches" not in tables and not details and source not in ("goaloo", "transfermarkt"):
        raise ValueError("teams requires matches; teams are derived from downloaded matches")
    selected = tuple(dict.fromkeys([*tables, *(["lineups"] if players else []),
                                   *(["matches", "teams"] if details else ["teams"] if "matches" in tables else [])]))
    if on_error not in ("raise", "collect"):
        raise ValueError("on_error must be 'raise' or 'collect'")
    if type(request_delay) not in (int, float) or not math.isfinite(request_delay) or request_delay < 0:
        raise ValueError("request_delay must be a finite nonnegative number")
    if cache_policy is not None and not isinstance(cache_policy, CachePolicy):
        raise ValueError("cache_policy must be a CachePolicy")
    if cache_policy is not None and cache_dir is None:
        raise ValueError("cache_policy requires cache_dir")
    if type(refresh) is not bool:
        raise ValueError("refresh must be a boolean")
    if any(table not in get_dataset_capabilities(source).tables for table in selected):
        raise ValueError(f"Unsupported dataset table for {source}")
    if details:
        from ._match_players import load_match_players
        from ._match_statistics import load_match_statistics

        return (load_match_players if players or events or shots else load_match_statistics)(
            source=source, league=league, season=year, tables=selected, proxies=proxies,
            cache_dir=cache_dir, cache_policy=cache_policy, refresh=refresh,
            request_delay=request_delay, on_error=on_error, progress=progress,
            season_id=season_id, start_date=start_date, end_date=end_date,
            source_timezone=source_timezone, match_ids=match_ids, max_pages=max_pages,
            anchor_date=anchor_date, source_season=source_season, club_ids=club_ids,
            player_ids=player_ids, max_match_requests=max_match_requests,
        )
    if source != "espn":
        from ._provider_datasets import load_provider_dataset

        return load_provider_dataset(
            source=source, league=league, season=year, tables=selected, proxies=proxies,
            cache_dir=cache_dir, cache_policy=cache_policy, refresh=refresh,
            request_delay=request_delay, on_error=on_error, progress=progress,
            season_id=season_id, start_date=start_date, end_date=end_date,
            source_timezone=source_timezone, match_ids=match_ids, max_pages=max_pages,
            anchor_date=anchor_date,
            source_season=source_season, club_ids=club_ids, player_ids=player_ids,
        )
    if any(value is not None for value in (season_id, start_date, end_date, source_timezone, match_ids, source_season, club_ids, player_ids)) or max_pages != 100:
        raise ValueError("Provider-specific options are not supported for ESPN")
    cache = ResponseCache(cache_dir) if cache_dir is not None else None
    client = ESPNClient(proxies=proxies, response_cache=cache, cache_policy=cache_policy,
                        refresh=refresh, request_delay=request_delay)
    started_at = datetime.now(timezone.utc)
    calendar = None
    dates: tuple[str, ...] = ()
    successful_dates: list[str] = []
    matches: dict[str, NormalizedMatch] = {}
    observations: dict[str, float] = {}
    teams: dict[str, NormalizedTeam] = {}
    team_observations: dict[str, float] = {}
    standings: list[NormalizedStanding] = []
    errors: list[DatasetIssue] = []
    response_times: dict[str, str] = {}
    cached_tasks: list[str] = []
    standings_loaded = False
    completed = 0
    total = int("matches" in selected) + int("standings" in selected)

    def snapshot():
        return SoccerDataset(
            metadata=DatasetMetadata(
                source=source, league=league, season=year, tables=selected,
                started_at=started_at, finished_at=datetime.now(timezone.utc),
                calendar_dates=dates, successful_dates=tuple(successful_dates),
                calendar_loaded=calendar is not None, standings_loaded=standings_loaded,
                calendar_name=calendar.name if calendar else None,
                calendar_type=calendar.calendar_type if calendar else None,
                season_start=calendar.start_date if calendar else None,
                season_end=calendar.end_date if calendar else None, anchor_date=anchor_date,
                response_fetched_at=tuple(response_times.items()), cached_tasks=tuple(cached_tasks),
            ),
            match_records=tuple(matches.values()), team_records=tuple(teams.values()),
            standing_records=tuple(standings), errors=tuple(errors),
        )

    def report(step, target, error=None):
        nonlocal completed
        completed += 1
        if error is not None:
            errors.append(DatasetIssue(step, target, type(error).__name__, str(error)))
        info = client.last_response
        cached = info.cached if isinstance(info, ResponseInfo) else False
        if error is None and isinstance(info, ResponseInfo):
            key = f"{step}:{target}"
            response_times[key] = datetime.fromtimestamp(info.fetched_at, timezone.utc).isoformat()
            if cached:
                cached_tasks.append(key)
        if progress is not None:
            progress(DatasetProgress(completed, total, step, target, error is None, len(matches), cached))
        if error is not None and on_error == "raise":
            raise DatasetLoadError(snapshot()) from error

    if "matches" in selected:
        error = None
        try:
            calendar = client.get_season_calendar(league, year, anchor_date=anchor_date)
            dates = calendar.dates
            total += len(dates)
        except Exception as exc:
            error = exc
        report("calendar", str(year), error)
        for date in dates:
            error = None
            try:
                events = client.get_scoreboard(league, date, expected_season=year)
                batch = [normalize_match(event, competition_id=league, season=year) for event in events]
                if any(not match.match_id for match in batch):
                    raise ValueError("A match is missing its source ID")
                batch_teams = [normalize_team(team) for event in events
                               for team in (event.home_team, event.away_team)]
                info = client.last_response
                observed_at = info.fetched_at if isinstance(info, ResponseInfo) else datetime.now(timezone.utc).timestamp()
                for match in batch:
                    if observed_at >= observations.get(match.match_id, float("-inf")):
                        matches[match.match_id] = match
                        observations[match.match_id] = observed_at
                for team in batch_teams:
                    if team.team_id is not None and observed_at >= team_observations.get(team.team_id, float("-inf")):
                        teams[team.team_id] = team
                        team_observations[team.team_id] = observed_at
                successful_dates.append(date)
            except Exception as exc:
                error = exc
            report("matches", date, error)
    if "standings" in selected:
        error = None
        try:
            raw = client.get_standings(league, year, strict=True)
            standings = [row for table in raw for row in normalize_standings(
                table, competition_id=league, season=year,
            )]
            standings_loaded = True
        except Exception as exc:
            error = exc
        report("standings", str(year), error)
    return snapshot()
