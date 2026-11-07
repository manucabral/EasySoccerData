"""Optional JSON response cache and freshness policy. No pandas or Arrow required."""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .exceptions import ESDException


class CacheError(ESDException):
    """A persistent response cache could not be read or written."""


@dataclass(frozen=True)
class CachePolicy:
    """Freshness in seconds. Zero forces a new request; defaults are conservative.

    Historical TTL applies only to empty days or events explicitly completed,
    older than recent_days. Pending/unknown events in the past use live_ttl.
    """

    calendar_ttl: float = 300.0
    live_ttl: float = 30.0
    upcoming_ttl: float = 300.0
    recent_ttl: float = 3600.0
    historical_ttl: float = 604800.0
    standings_ttl: float = 300.0
    recent_days: int = 7

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{field.name} must be finite and nonnegative")
        if type(self.recent_days) is not int:
            raise ValueError("recent_days must be an integer")

    def scoreboard_ttl(self, date: str, data: dict) -> float:
        """Calculate freshness using the query date and the cached event states."""
        day = datetime.strptime(date.replace("-", ""), "%Y%m%d").date()
        today = datetime.now(timezone.utc).date()
        if day > today:
            return self.upcoming_ttl
        if day == today:
            return self.live_ttl
        events = data.get("events")
        if not isinstance(events, list):
            return 0.0
        for event in events:
            status = event.get("status") if isinstance(event, dict) else None
            kind = status.get("type") if isinstance(status, dict) else None
            if not isinstance(kind, dict) or kind.get("completed") is not True:
                return self.live_ttl
        if day >= today - timedelta(days=self.recent_days):
            return self.recent_ttl
        return self.historical_ttl


@dataclass(frozen=True)
class CachedResponse:
    """Response payload with its original fetch timestamp."""

    data: dict
    fetched_at: float


@dataclass(frozen=True)
class ResponseInfo:
    """Provenance of the most recent single-response client operation."""

    cached: bool
    fetched_at: float


def _payload_hash(data):
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ResponseCache:
    """Persistent response entries published with atomic file replacement.

    Each URL has a hashed filename under responses-v1 in the supplied directory.
    Broken, incompatible or expired entries are misses and are replaced only
    after a successful fetch. Permission and other I/O failures raise CacheError.
    URL keys and proxy credentials are not written into the entry.
    """

    def __init__(self, directory):
        base = Path(directory).expanduser().absolute()
        if base.exists() and not base.is_dir():
            raise CacheError(f"Cache path is not a directory: {base}")
        self.directory = base / "responses-v1"
        if self.directory.exists() and not self.directory.is_dir():
            raise CacheError(f"Cache path is not a directory: {self.directory}")

    def _path(self, key):
        name = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.directory / f"{name}.json"

    def get(
        self, key: str, *, ttl: float | Callable[[dict], float]
    ) -> CachedResponse | None:
        try:
            entry = json.loads(self._path(key).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise CacheError(f"Cannot read response cache: {exc}") from exc
        except (ValueError, UnicodeError):
            return None
        try:
            data = entry["data"]
            fetched_at = entry["fetched_at"]
            if type(entry["version"]) is not int or entry["version"] != 1 or not isinstance(data, dict):
                return None
            if type(fetched_at) not in (int, float) or not math.isfinite(fetched_at):
                return None
            if _payload_hash(data) != entry["sha256"]:
                return None
            max_age = ttl(data) if callable(ttl) else ttl
            age = time.time() - fetched_at
            if not math.isfinite(max_age) or max_age <= 0 or not 0 <= age < max_age:
                return None
            return CachedResponse(data, fetched_at)
        except (KeyError, TypeError, ValueError, AttributeError):
            return None

    def set(self, key: str, data: dict, *, fetched_at: float | None = None):
        """Publish a JSON response. A failed write preserves the previous entry."""
        entry = {"version": 1, "fetched_at": time.time() if fetched_at is None else fetched_at,
                 "data": data, "sha256": _payload_hash(data)}
        temporary = None
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.directory,
                                             prefix=".response-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(entry, stream, ensure_ascii=False, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self._path(key))
        except OSError as exc:
            raise CacheError(f"Cannot write response cache: {exc}") from exc
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    def invalidate(self, key: str):
        """Remove one response that failed validation."""
        try:
            self._path(key).unlink(missing_ok=True)
        except OSError as exc:
            raise CacheError(f"Cannot invalidate response cache: {exc}") from exc

    def clear(self) -> int:
        """Delete owned response files in this cache namespace, returning their count."""
        removed = 0
        try:
            for path in self.directory.glob("*.json"):
                if len(path.stem) == 64 and all(char in "0123456789abcdef" for char in path.stem) and path.is_file():
                    path.unlink()
                    removed += 1
        except OSError as exc:
            raise CacheError(f"Cannot clear response cache: {exc}") from exc
        return removed
