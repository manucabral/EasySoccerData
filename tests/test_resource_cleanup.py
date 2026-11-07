"""Worker HTTP pools and partially launched browsers release owned resources."""

from unittest.mock import Mock

import pytest

import esd.utils as utils


@pytest.mark.parametrize("fails", [False, True])
def test_fetch_workers_close_all_sessions_even_when_task_or_close_fails(monkeypatch, fails):
    sessions = []

    def create(**kwargs):
        session = Mock()
        sessions.append(session)
        if kwargs["impersonate"] == "chrome":
            session.close.side_effect = RuntimeError("Close failed")
        return session

    monkeypatch.setattr(utils.requests, "Session", create)

    def task():
        utils._get_session("chrome")
        utils._get_session("safari17_0")
        if fails:
            raise ValueError("Task failed")
        return 42

    if fails:
        with pytest.raises(ValueError, match="Task failed"):
            utils.fetch_many([task], max_workers=1)
    else:
        assert utils.fetch_many([task], max_workers=1) == [42]
    assert len(sessions) == 2
    for session in sessions:
        session.close.assert_called_once_with()


def test_browser_launch_failure_stops_started_driver(monkeypatch):
    import playwright.sync_api

    driver = Mock()
    driver.chromium.launch.side_effect = RuntimeError("Launch failed")
    start = Mock()
    start.return_value.start.return_value = driver
    monkeypatch.setattr(playwright.sync_api, "sync_playwright", start)
    with utils.BrowserSession() as session:
        with pytest.raises(RuntimeError, match="Launch failed"):
            session.new_page()
        assert session._playwright is None and session._browser is None
    driver.stop.assert_called_once_with()


def test_browser_close_failure_still_stops_driver_and_is_idempotent():
    session = utils.BrowserSession()
    browser, driver = Mock(), Mock()
    browser.close.side_effect = RuntimeError("Browser exited")
    session._browser, session._playwright = browser, driver
    session._warmed_urls.add("example")
    session.close()
    session.close()
    browser.close.assert_called_once_with()
    driver.stop.assert_called_once_with()
    assert not session._warmed_urls
