"""
Shared exceptions raised by EasySoccerData sources.

These wrap HTTP-level failures from the underlying sources so callers
get a typed, actionable error instead of a bare ``KeyError`` or a silent
empty dict. Source-specific exceptions (``FBrefException``,
``PromiedosException``, ...) remain in their own submodules.
"""


class ESDException(Exception):
    """Base class for all EasySoccerData exceptions."""


class SourceBlocked(ESDException):
    """
    The source blocked the request (HTTP 403 / anti-bot).

    Usually means the IP is flagged as a datacenter/VPN. Retry from a
    residential connection or pass a proxy to the client.
    """


class SourceNotFound(ESDException):
    """The requested resource does not exist on the source (HTTP 404)."""


class SourceError(ESDException):
    """Any other HTTP-level failure from the source."""
