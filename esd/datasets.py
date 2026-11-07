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
    NormalizedMarketValue,
    NormalizedMatch,
    NormalizedMatchStats,
    NormalizedPlayer,
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
    """A failed calendar lookup, day or standings request."""

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
    """Query context and coverage of the source calendar snapshot."""

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


@dataclass(frozen=True)
class SoccerDataset:
    """In-memory records. DataFrame properties import pandas only on access.

    complete means every task for the received calendar succeeded, not that the
    provider calendar is exhaustive or that the season has finished. Standings
    are a source snapshot for that season, not historical standings per matchday.
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

    @property
    def complete(self) -> bool:
        meta = self.metadata
        if meta.expected_tasks:
            return not self.errors and set(meta.expected_tasks) == set(meta.successful_tasks)
        matches_ok = "matches" not in meta.tables or (
            meta.calendar_loaded and set(meta.calendar_dates) == set(meta.successful_dates)
        )
        standings_ok = "standings" not in meta.tables or meta.standings_loaded
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
        """Teams with known IDs observed in downloaded matches."""
        return self._dataframe(self.team_records, "teams")

    @property
    def standings(self):
        """Standings snapshot, available only when explicitly requested."""
        return self._dataframe(self.standing_records, "standings")

    @property
    def match_stats(self):
        return self._dataframe(self.match_stat_records, "match_stats")

    @property
    def player_stats(self):
        return self._dataframe(self.player_stat_records, "player_stats")

    @property
    def shots(self):
        return self._dataframe(self.shot_records, "shots")

    @property
    def players(self):
        return self._dataframe(self.player_records, "players")

    @property
    def market_values(self):
        return self._dataframe(self.market_value_records, "market_values")

    @property
    def transfers(self):
        return self._dataframe(self.transfer_records, "transfers")

    def save(self, path: str | PathLike, *, format: str = "parquet") -> Path:
        """Write a snapshot to a new directory with EasySoccerData[parquet].

        Tables are Parquet files alongside a versioned JSON manifest containing
        metadata, errors, row counts and checksums. Existing paths are never
        intentionally overwritten. A failed write is cleaned up before publishing
        the directory. Returns the absolute saved directory.
        """
        from ._dataset_storage import save_dataset

        return save_dataset(self, path, format=format)


class DatasetFormatError(ESDException):
    """A saved dataset is invalid, damaged or uses an unsupported schema."""


def open_dataset(path: str | PathLike) -> SoccerDataset:
    """Read a saved Parquet snapshot without network access.

    Requires EasySoccerData[parquet]. Validates the manifest, versions, table
    schemas, row counts and checksums. Partial coverage and errors are preserved.
    """
    from ._dataset_storage import read_dataset

    return read_dataset(path)


class DatasetLoadError(ESDException):
    """A dataset task failed. dataset contains records and coverage so far."""

    def __init__(self, dataset: SoccerDataset):
        self.dataset = dataset
        issue = dataset.errors[-1]
        super().__init__(f"Dataset {issue.step} failed for {issue.target}: {issue.message}")


def load_dataset(
    *,
    source: str,
    league: str,
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
) -> SoccerDataset:
    """Download normalized tables with a provider-specific selection contract.

    All nine sources have dataset plans. See
    get_dataset_capabilities() for supported tables. season is a four-digit
    year label, not a native season ID. Sofascore requires season_id and fetches
    past/upcoming pages; max_pages limits each direction. 365Scores requires
    explicit UTC start_date/end_date for matches and native season_id for
    standings. Its season year is a caller label. Understat offers optional
    match_stats, player_stats and shots; match_ids restricts shot downloads to
    completed matches in the selected league season. Naive Understat kickoffs
    require source_timezone. No browser is launched by these loaders.

    FBref, Promiedos and BeSoccer matches require explicit date bounds. FBref
    preserves sequential rate limits. Goaloo requires source_season (for example
    '2024-2025'), validated against native metadata. Naive dates require
    source_timezone. BeSoccer filters adjacent-page fixtures by UTC date, or by
    source_timezone when supplied. Transfermarkt uses explicit club_ids and/or
    player_ids with teams, players, market_values and transfers tables. Profiles
    are current and histories span all native seasons. Its league/year are
    caller context, not a historical roster selection. Club competition IDs
    are validated; player histories are not filtered by league or year.

    ESPN discovers calendar dates (July 1 by default, or anchor_date) and
    validates the source season year. Teams derive from downloaded matches.

    Repeated match IDs retain the newest response observation. A day's parsed
    records are committed together, so a parsing failure marks the whole day as
    failed. A daily response at the requested event limit is treated as a failure
    because it may be truncated. Underlying HTTP retries are reused.

    on_error='raise' stops with DatasetLoadError.dataset holding partial results.
    'collect' continues and returns errors with complete=False. Progress callback
    exceptions propagate directly. With cache_dir, validated source responses
    are saved as JSON and reused while fresh. Repeating the query resumes an
    interrupted download; new calendar days and stale/failed responses are fetched.
    refresh=True bypasses caches and replaces entries after successful validation.
    Cache storage needs neither pandas nor Arrow. Without cache_dir, the loader
    writes no files. pandas is needed only for DataFrame access.
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
    if "teams" in tables and "matches" not in tables and source not in ("goaloo", "transfermarkt"):
        raise ValueError("teams requires matches; teams are derived from downloaded matches")
    selected = tuple(dict.fromkeys([*tables, *(["teams"] if "matches" in tables else [])]))
    if on_error not in ("raise", "collect"):
        raise ValueError("on_error must be 'raise' or 'collect'")
    if not math.isfinite(request_delay) or request_delay < 0:
        raise ValueError("request_delay must be a finite nonnegative number")
    if cache_policy is not None and not isinstance(cache_policy, CachePolicy):
        raise ValueError("cache_policy must be a CachePolicy")
    if cache_policy is not None and cache_dir is None:
        raise ValueError("cache_policy requires cache_dir")
    if type(refresh) is not bool:
        raise ValueError("refresh must be a boolean")
    if any(table not in get_dataset_capabilities(source).tables for table in selected):
        raise ValueError(f"Unsupported dataset table for {source}")
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
