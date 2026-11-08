"""
# EasySoccerData

A Python library for football fixtures, live scores, standings and player
statistics from nine providers.

EasySoccerData is independent of the data providers.

.. include:: ../READMEdoc.md
   :start-line: 14
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

from .besoccer import BeSoccerClient
from .besoccer import types as BeSoccerTypes
from .cache import CacheError, CachePolicy, ResponseCache
from .catalog import (
    CatalogCompetition,
    CatalogReference,
    CatalogTeam,
    FootballCatalog,
    get_catalog,
    open_catalog,
)
from .compatibility import (
    DatasetCompatibility,
    EntityAlias,
    IdentityMap,
    IdentityResolution,
    MatchLink,
    MatchLinkResult,
    check_dataset_compatibility,
    link_dataset_matches,
)
from .dataset_capabilities import DatasetCapabilities, get_dataset_capabilities
from .dataset_coverage import (
    DatasetCoverageReport,
    DatasetFieldCoverage,
    DatasetTableCoverage,
    DatasetTaskCoverage,
    inspect_dataset_coverage,
)
from .dataset_fields import DatasetFieldCapability, get_dataset_field_capabilities
from .dataset_validation import (
    DatasetValidationIssue,
    DatasetValidationReport,
    validate_dataset,
)
from .datasets import (
    DatasetFormatError,
    DatasetIssue,
    DatasetLoadError,
    DatasetMetadata,
    DatasetProgress,
    SoccerDataset,
    load_dataset,
    open_dataset,
)
from .discovery import (
    CompetitionInfo,
    DiscoveryCapabilities,
    DiscoveryNotSupported,
    DiscoveryResult,
    SeasonInfo,
    get_discovery_capabilities,
    list_competitions,
    list_seasons,
)
from .espn import ESPNClient
from .espn import types as ESPNTypes
from .event_comparison import (
    MatchEventComparison,
    MatchEventCoverage,
    MatchEventsReport,
    compare_match_events,
)
from .exceptions import ESDException, SourceBlocked, SourceError, SourceNotFound
from .fbref import FBrefClient
from .fbref import types as FBrefTypes
from .goaloo import GoalooClient
from .goaloo import types as GoalooTypes
from .logger import disable_logging, enable_logging
from .normalized import (
    MatchPlayerRecords,
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
    normalize_match_events,
    normalize_match_players,
    normalize_match_shots,
    normalize_match_stats,
    normalize_player_stats,
    normalize_shot,
    normalize_standings,
    normalize_team,
    normalized_to_dataframe,
)
from .player_comparison import (
    MatchPlayerComparison,
    MatchPlayerCoverage,
    MatchPlayersReport,
    PlayerMatchStatisticComparison,
    compare_match_players,
)
from .promiedos import PromiedosClient
from .promiedos import types as PromiedosTypes
from .scores365 import Scores365Client
from .scores365 import types as Scores365Types
from .sofascore import SofascoreClient
from .sofascore import types as SofascoreTypes
from .statistics_comparison import (
    MatchStatisticComparison,
    MatchStatisticsReport,
    compare_match_statistics,
)
from .transfermarkt import TransfermarktClient
from .transfermarkt import types as TransfermarktTypes
from .understat import UnderstatClient
from .understat import types as UnderstatTypes
from .utils import fetch_many, to_dataframe

try:
    __version__ = _version("EasySoccerData")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "DatasetFieldCapability", "get_dataset_field_capabilities", "DatasetCoverageReport",
    "DatasetFieldCoverage", "DatasetTableCoverage", "DatasetTaskCoverage", "inspect_dataset_coverage",
    "MatchPlayerComparison", "MatchPlayerCoverage", "MatchPlayersReport",
    "PlayerMatchStatisticComparison", "compare_match_players",
    "MatchEventComparison", "MatchEventCoverage", "MatchEventsReport", "compare_match_events",
    "NormalizedMatchEvent", "normalize_match_events", "normalize_match_shots",
    "CatalogCompetition", "CatalogReference", "CatalogTeam", "FootballCatalog", "get_catalog", "open_catalog",
    "MatchPlayerRecords", "normalize_match_players",
    "NormalizedLineup", "NormalizedPlayerMatchStats",
    "MatchStatisticComparison", "MatchStatisticsReport", "compare_match_statistics",
    "CompetitionInfo", "SeasonInfo", "DiscoveryCapabilities", "DiscoveryResult",
    "DiscoveryNotSupported", "get_discovery_capabilities", "list_competitions", "list_seasons",
    "DatasetValidationIssue", "DatasetValidationReport", "validate_dataset",
    "DatasetCompatibility", "EntityAlias", "IdentityMap", "MatchLink", "MatchLinkResult",
    "IdentityResolution",
    "check_dataset_compatibility", "link_dataset_matches",
    "NormalizedPlayer", "NormalizedMarketValue", "NormalizedTransfer",
    "SofascoreClient",
    "SofascoreTypes",
    "PromiedosClient",
    "PromiedosTypes",
    "FBrefClient",
    "FBrefTypes",
    "GoalooClient",
    "GoalooTypes",
    "Scores365Client",
    "Scores365Types",
    "UnderstatClient",
    "UnderstatTypes",
    "TransfermarktClient",
    "TransfermarktTypes",
    "ESPNClient",
    "ESPNTypes",
    "BeSoccerClient",
    "BeSoccerTypes",
    "ESDException",
    "SourceBlocked",
    "SourceError",
    "SourceNotFound",
    "enable_logging",
    "disable_logging",
    "fetch_many",
    "to_dataframe",
    "NormalizedMatch",
    "NormalizedStanding",
    "NormalizedTeam",
    "normalize_match",
    "normalize_standings",
    "normalize_team",
    "normalized_to_dataframe",
    "DatasetIssue",
    "DatasetLoadError",
    "DatasetMetadata",
    "DatasetProgress",
    "SoccerDataset",
    "load_dataset",
    "open_dataset",
    "DatasetFormatError",
    "CacheError",
    "CachePolicy",
    "ResponseCache",
    "DatasetCapabilities",
    "get_dataset_capabilities",
    "NormalizedMatchStats",
    "NormalizedPlayerStats",
    "NormalizedShot",
    "normalize_match_stats",
    "normalize_player_stats",
    "normalize_shot",
]
