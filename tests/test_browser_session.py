"""Resource cleanup tests using a browser double, without launching Chrome."""

from unittest.mock import Mock

import pytest

from esd.utils import BrowserSession


@pytest.fixture
def session():
    browser_session = BrowserSession()
    browser_session._browser = Mock()
    yield browser_session
    browser_session.close()


@pytest.mark.parametrize("close_fails", [False, True])
def test_page_setup_failure_closes_page_and_preserves_error(session, close_fails):
    page = session._browser.new_page.return_value
    error = RuntimeError("setup failed")
    page.add_init_script.side_effect = error
    if close_fails:
        page.close.side_effect = RuntimeError("close failed")
    with pytest.raises(RuntimeError) as caught, session.page():
        pytest.fail("Page with failed setup must not be yielded")
    assert caught.value is error
    page.close.assert_called_once_with()


@pytest.mark.parametrize("body_fails", [False, True])
def test_page_context_closes_page(session, body_fails):
    page = session._browser.new_page.return_value
    if body_fails:
        with pytest.raises(ValueError, match="body failed"), session.page():
            raise ValueError("body failed")
    else:
        with session.page() as opened:
            assert opened is page
    page.close.assert_called_once_with()
