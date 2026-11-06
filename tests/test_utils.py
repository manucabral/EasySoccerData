"""Tests for esd.utils."""

import time

import pytest

from esd.utils import TTLCache, camel_to_snake, fetch_many, is_available_date


def test_ttl_cache_eviction_and_Order():
    cache = TTLCache(ttl=10.0, maxsize=2)
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("a") == 1
    cache.set("c", 3)
    assert cache.get("b") is None
    assert cache.get("a") == 1
    assert cache.get("c") == 3


def test_ttl_cache_expiration():
    cache = TTLCache(ttl=0.05, maxsize=10)
    cache.set("key", "value")
    assert cache.get("key") == "value"
    time.sleep(0.08)
    assert cache.get("key") is None


def test_camel_to_snake():
    assert camel_to_snake("ballPossession") == "ball_possession"
    assert camel_to_snake("HTTPResponseCode") == "http_response_code"


def test_is_available_date():
    is_available_date("2026-11-06", r"\d{4}-\d{2}-\d{2}")
    with pytest.raises(ValueError):
        is_available_date("2026-02-30", r"\d{4}-\d{2}-\d{2}")
    with pytest.raises(ValueError):
        is_available_date("06-11-2026", r"\d{4}-\d{2}-\d{2}")


def test_fetch_many():
    results = fetch_many([lambda i=i: i * 2 for i in range(5)], max_workers=2)
    assert results == [0, 2, 4, 6, 8]
