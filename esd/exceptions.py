"""
Shared exceptions raised by EasySoccerData sources.

HTTP helpers raise these exceptions for blocked, missing or failed responses.
Provider-specific exceptions, such as ``FBrefException`` and
``PromiedosException``, are defined in the provider submodules.
"""


class ESDException(Exception):
    """Base class for all EasySoccerData exceptions."""


class SourceBlocked(ESDException):
    """
    The source blocked the request (HTTP 403 / anti-bot).

    The response alone does not identify the reason for the block.
    """


class SourceNotFound(ESDException):
    """The requested resource does not exist on the source (HTTP 404)."""


class SourceError(ESDException):
    """Any other HTTP-level failure from the source."""
