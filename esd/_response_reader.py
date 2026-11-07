"""Validated response reuse and pacing shared by dataset providers."""

from __future__ import annotations

import math
import time

from .cache import CachedResponse, ResponseInfo
from .exceptions import SourceError
from .utils import TTLCache


class ResponseReader:
    def __init__(self, fetch, *, cache=None, refresh=False, request_delay=0.0):
        if not math.isfinite(request_delay) or request_delay < 0:
            raise ValueError("request_delay must be finite and nonnegative")
        self.fetch = fetch
        self.cache = cache
        self.refresh = refresh
        self.request_delay = request_delay
        self.last_response = None
        self._memory = TTLCache(ttl=30.0)
        self._last_fetch_finished = None

    def read(self, url, *, ttl=30.0, validate=None):
        self.last_response = None
        cached = None
        if not self.refresh:
            if self.cache is not None:
                cached = self.cache.get(url, ttl=ttl)
            else:
                cached = self._memory.get(url)
                if cached is not None:
                    max_age = ttl(cached.data) if callable(ttl) else ttl
                    if time.time() - cached.fetched_at >= max_age:
                        cached = None
        if cached is not None:
            try:
                if validate is not None:
                    validate(cached.data)
            except (SourceError, KeyError, TypeError, ValueError, AttributeError):
                if self.cache is not None:
                    self.cache.invalidate(url)
            else:
                self.last_response = ResponseInfo(True, cached.fetched_at)
                return cached.data
        if self._last_fetch_finished is not None:
            remaining = self.request_delay - (time.monotonic() - self._last_fetch_finished)
            if remaining > 0:
                time.sleep(remaining)
        try:
            data = self.fetch(url)
        finally:
            self._last_fetch_finished = time.monotonic()
        fetched_at = time.time()
        if validate is not None:
            validate(data)
        if self.cache is not None:
            if isinstance(data, dict) and data:
                self.cache.set(url, data, fetched_at=fetched_at)
        else:
            self._memory.set(url, CachedResponse(data, fetched_at))
        self.last_response = ResponseInfo(False, fetched_at)
        return data
