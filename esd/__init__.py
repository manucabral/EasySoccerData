"""
# EasySoccerData

A Python easy-to-use library for fetching live
football/soccer stats from multiple online sources/APIs.

Note! This package is not affiliated with
any of the sources used to extract data.

.. include:: ../READMEdoc.md
   :start-line: 17
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

from .besoccer import BeSoccerClient
from .besoccer import types as BeSoccerTypes
from .cache import CacheError, CachePolicy, ResponseCache
from .compatibility import (
    DatasetCompatibility,
    EntityAlias,
    IdentityMap,
    MatchLink,
    MatchLinkResult,
    check_dataset_compatibility,
    link_dataset_matches,
)
from .dataset_capabilities import DatasetCapabilities, get_dataset_capabilities
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
from .espn import ESPNClient
from .espn import types as ESPNTypes
from .exceptions import ESDException, SourceBlocked, SourceError, SourceNotFound
from .fbref import FBrefClient
from .fbref import types as FBrefTypes
from .goaloo import GoalooClient
from .goaloo import types as GoalooTypes
from .logger import disable_logging, enable_logging
from .normalized import (
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
    normalize_match_stats,
    normalize_player_stats,
    normalize_shot,
    normalize_standings,
    normalize_team,
    normalized_to_dataframe,
)
from .promiedos import PromiedosClient
from .promiedos import types as PromiedosTypes
from .scores365 import Scores365Client
from .scores365 import types as Scores365Types
from .sofascore import SofascoreClient
from .sofascore import types as SofascoreTypes
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
    "DatasetCompatibility", "EntityAlias", "IdentityMap", "MatchLink", "MatchLinkResult",
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
