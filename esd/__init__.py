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

from .fbref import FBrefClient
from .fbref import types as FBrefTypes
from .promiedos import PromiedosClient
from .promiedos import types as PromiedosTypes
from .sofascore import SofascoreClient
from .sofascore import types as SofascoreTypes

try:
    __version__ = _version(__package__ or "EasySoccerData")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "SofascoreClient",
    "SofascoreTypes",
    "PromiedosClient",
    "PromiedosTypes",
    "FBrefClient",
    "FBrefTypes",
]
