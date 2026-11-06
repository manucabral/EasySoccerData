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

from .exceptions import ESDException, SourceBlocked, SourceError, SourceNotFound
from .fbref import FBrefClient
from .fbref import types as FBrefTypes
from .goaloo import GoalooClient
from .goaloo import types as GoalooTypes
from .logger import disable_logging, enable_logging
from .promiedos import PromiedosClient
from .promiedos import types as PromiedosTypes
from .sofascore import SofascoreClient
from .sofascore import types as SofascoreTypes
from .utils import fetch_many, to_dataframe

try:
    __version__ = _version("EasySoccerData")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "SofascoreClient",
    "SofascoreTypes",
    "PromiedosClient",
    "PromiedosTypes",
    "FBrefClient",
    "FBrefTypes",
    "GoalooClient",
    "GoalooTypes",
    "ESDException",
    "SourceBlocked",
    "SourceError",
    "SourceNotFound",
    "enable_logging",
    "disable_logging",
    "fetch_many",
    "to_dataframe",
]
