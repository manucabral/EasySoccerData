"""Resource ownership on failure, using doubles instead of browsers or HTTP."""

import threading
from unittest.mock import Mock

import pytest

from esd import utils


@pytest.mark.parametrize("stop_fails", [False, True])
def test_browser_launch_failure_stops_driver_and_preserves_launch_error(monkeypatch, stop_fails):
    from playwright import sync_api

    driver = Mock()
    original = RuntimeError("launch failed")
    driver.chromium.launch.side_effect = original
    if stop_fails:
        driver.stop.side_effect = RuntimeError("driver stop failed")
    factory = Mock()
    factory.return_value.start.return_value = driver
    monkeypatch.setattr(sync_api, "sync_playwright", factory)
    session = utils.BrowserSession()
    with pytest.raises(RuntimeError) as caught:
        session.new_page()
    assert caught.value is original
    driver.stop.assert_called_once()
    assert session._playwright is None and session._browser is None


@pytest.mark.parametrize("browser_close_fails", [False, True])
def test_repeated_session_cleanup_stops_driver_and_is_idempotent(browser_close_fails):
    for _ in range(10):
        session = utils.BrowserSession()
        browser, driver = Mock(), Mock()
        session._browser, session._playwright = browser, driver
        if browser_close_fails:
            browser.close.side_effect = RuntimeError("browser close failed")
        session.close()
        session.close()
        browser.close.assert_called_once()
        driver.stop.assert_called_once()
        assert session._browser is None and session._playwright is None


@pytest.mark.parametrize("fail", [False, True])
def test_fetch_many_closes_worker_sessions_after_success_or_error(monkeypatch, fail):
    created, lock = [], threading.Lock()

    def factory(**kwargs):
        session = Mock()
        with lock:
            created.append(session)
        return session

    monkeypatch.setattr(utils.requests, "Session", factory)

    def task():
        session = utils._get_session()
        assert utils._get_session() is session
        if fail:
            raise RuntimeError("worker failed")
        return "ok"

    if fail:
        with pytest.raises(RuntimeError, match="worker failed"):
            utils.fetch_many([task] * 8, max_workers=2)
    else:
        assert utils.fetch_many([task] * 8, max_workers=2) == ["ok"] * 8
    assert created
    for session in created:
        session.close.assert_called_once()


def test_thread_cleanup_closes_other_profiles_when_one_close_fails(monkeypatch):
    first, second = Mock(), Mock()
    first.close.side_effect = RuntimeError("close failed")
    monkeypatch.setattr(utils._local, "sessions", {"first": first, "second": second}, raising=False)
    utils._close_thread_sessions()
    first.close.assert_called_once()
    second.close.assert_called_once()
    assert utils._local.sessions == {}
