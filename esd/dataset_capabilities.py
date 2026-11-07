"""Implemented dataset contracts, separate from individual client methods."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DatasetCapabilities:
    """Implemented tables, selection kind and source-specific constraints.

    tables lists normalized tables accepted by load_dataset(). selection names
    the provider's query scope (season_year, native_season_id, source_season,
    date_range or entities). notes describes required inputs and limitations.
    This contract does not assert current network availability.
    """
    source: str
    tables: tuple[str, ...]
    selection: str
    notes: tuple[str, ...] = ()


_CAPABILITIES = {
    "espn": DatasetCapabilities("espn", ("matches", "teams", "standings"), "season_year"),
    "scores365": DatasetCapabilities("scores365", ("matches", "teams", "standings"), "date_range", (
        "Explicit start_date/end_date for matches; season is a caller label.",
        "Native season_id required for standings; responses are locally filtered by competition.",
    )),
    "sofascore": DatasetCapabilities("sofascore", ("matches", "teams", "standings"), "native_season_id", (
        "Explicit native season_id; past and upcoming pages must reach an explicit end.",
        "Source can block requests; dataset loader does not launch a browser.",
    )),
    "understat": DatasetCapabilities("understat", ("matches", "teams", "match_stats", "player_stats", "shots"), "season_year", (
        "Naive kickoff times require caller-supplied source_timezone.",
        "Shot coordinates retain Understat's native convention; shots are opt-in.",
    )),
    "fbref": DatasetCapabilities("fbref", ("matches", "teams", "match_stats"), "date_range", (
        "Explicit dates and numeric competition ID; minimum 60/9 seconds between requests.",
        "Naive kickoff times need source_timezone. Unidentified fixtures fail explicitly.",
    )),
    "goaloo": DatasetCapabilities("goaloo", ("matches", "teams", "standings"), "source_season", (
        "Explicit source_season (e.g. 2024-2025) checked against LeagueInfo.",
        "Naive dates need source_timezone; scores do not establish final status.",
    )),
    "promiedos": DatasetCapabilities("promiedos", ("matches", "teams"), "date_range", (
        "Explicit dates and league ID; source_timezone required for naive dates.",
        "Year is a caller label, not historical season selection.",
    )),
    "besoccer": DatasetCapabilities("besoccer", ("matches", "teams", "standings"), "date_range", (
        "Competition slug and explicit dates for matches; year selects standings.",
        "Source pages can be blocked or omit the expected structure.",
    )),
    "transfermarkt": DatasetCapabilities("transfermarkt", ("teams", "players", "market_values", "transfers"), "entities", (
        "Explicit club_ids for teams, player_ids for profiles/history; no match table.",
        "Current profiles and full native histories, not season-filtered rosters.",
        "League and year are caller context; clubs are checked against native competition IDs.",
    )),
}


def get_dataset_capabilities(source: str | None = None) -> DatasetCapabilities | dict[str, DatasetCapabilities]:
    """Get one immutable source contract, or a copy of all nine contracts.

    source=None returns a new mapping keyed by source name. Unknown source names
    raise ValueError. No network request, optional import or file write occurs.
    """
    if source is None:
        return dict(_CAPABILITIES)
    if source not in _CAPABILITIES:
        raise ValueError(f"Unknown source: {source}")
    return _CAPABILITIES[source]
