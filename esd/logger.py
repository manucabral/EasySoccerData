"""
Logging setup for the EasySoccerData package.

By default, logging is **disabled** (no output). To enable it::

    from esd.logger import enable_logging
    enable_logging()

Or for full debug output::

    from esd.logger import enable_logging
    enable_logging(level="DEBUG")
"""

from __future__ import annotations

import logging
import sys

_ROOT_LOGGER_NAME = "esd"
_DEFAULT_FORMAT = "%(asctime)s %(levelname)-8s %(name)s %(message)s"

_handler: logging.Handler | None = None


def get_logger(name: str) -> logging.Logger:
    """
    Get a child logger under the 'esd' namespace.

    Args:
        name: Sub-logger name (e.g. 'fbref.service', 'sofascore.client').

    Returns:
        A ``logging.Logger`` instance.
    """
    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{name}")


def enable_logging(
    level: int | str = logging.INFO,
    stream=sys.stderr,
    fmt: str | None = None,
) -> None:
    """
    Enable logging output for the EasySoccerData package.

    Args:
        level: Log level (default ``INFO``). Accepts ``logging.DEBUG``,
            ``logging.INFO``, ``logging.WARNING``, ``logging.ERROR``,
            ``logging.CRITICAL``, or string equivalents like ``"DEBUG"``.
        stream: Where to write log messages (default ``sys.stderr``).
        fmt: Custom format string (defaults to timestamp-level-name-message).
    """
    global _handler
    disable_logging()
    _handler = logging.StreamHandler(stream)
    _handler.setFormatter(logging.Formatter(fmt or _DEFAULT_FORMAT))
    root = logging.getLogger(_ROOT_LOGGER_NAME)
    root.addHandler(_handler)
    root.setLevel(_resolve_level(level))
    if root.level == logging.DEBUG:
        root.debug("logging enabled (level=DEBUG)")


def disable_logging() -> None:
    """
    Disable logging output for the EasySoccerData package.
    """
    global _handler
    root = logging.getLogger(_ROOT_LOGGER_NAME)
    if _handler is not None:
        root.removeHandler(_handler)
        _handler.close()
        _handler = None
    root.setLevel(logging.NOTSET)


def _resolve_level(level: int | str) -> int:
    if isinstance(level, int):
        return level
    return getattr(logging, level.upper(), logging.INFO)


# ---- attach NullHandler so the library never complains about "no handlers" ----
_log_root = logging.getLogger(_ROOT_LOGGER_NAME)
_log_root.addHandler(logging.NullHandler())
_log_root.setLevel(logging.NOTSET)
