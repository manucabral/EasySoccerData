"""HTTP behavior tests for both transports, without external requests."""

from unittest.mock import Mock

import httpx
import pytest

from esd import utils
from esd.exceptions import SourceBlocked, SourceError

URL = "https://example.test/data"


def response(status=200, text='{"ok": true}'):
    return httpx.Response(status, text=text, request=httpx.Request("GET", URL))


@pytest.fixture(params=["httpx", "curl"])
def transport(request, monkeypatch):
    client = Mock()
    factory = Mock(return_value=client)
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    if request.param == "httpx":
        monkeypatch.setattr(utils.httpx, "Client", factory)
        kwargs = {}
    else:
        monkeypatch.setattr(utils, "_get_session", factory)
        kwargs = {"impersonate": "chrome"}
    sleep = Mock()
    monkeypatch.setattr(utils.time, "sleep", sleep)
    monkeypatch.setattr(utils.random, "uniform", lambda *_: 0.0)
    return client, factory, kwargs, sleep


def test_json_forwards_request_options(transport):
    client, factory, kwargs, _ = transport
    client.get.return_value = response(text='\ufeff{"ok": true}')
    headers = {"X-Test": "value"}
    proxies = {"https": "http://proxy.test:8080"}
    assert utils.get_json(URL, headers=headers, proxies=proxies, timeout=7, **kwargs) == {
        "ok": True,
    }
    if kwargs:
        factory.assert_called_once_with("chrome")
        client.get.assert_called_once_with(URL, headers=headers, proxies=proxies, timeout=7)
    else:
        factory.assert_called_once_with(proxy=proxies["https"], timeout=7, headers=headers)
        client.get.assert_called_once_with(URL)
        client.__exit__.assert_called_once()


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_permanent_status_is_not_retried(transport, status):
    client, _, kwargs, sleep = transport
    client.get.return_value = response(status)
    if status == 404:
        # Preserve the existing empty-result contract until strict errors are introduced.
        assert utils.get_json(URL, **kwargs) == {}
    else:
        error = SourceBlocked if status == 403 else SourceError
        with pytest.raises(error):
            utils.get_json(URL, **kwargs)
    assert client.get.call_count == 1
    sleep.assert_not_called()


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_transient_status_recovers_with_backoff(transport, status):
    client, _, kwargs, sleep = transport
    client.get.side_effect = [response(status), response(status), response()]
    assert utils.get_json(URL, **kwargs) == {"ok": True}
    assert client.get.call_count == 3
    assert [call.args[0] for call in sleep.call_args_list] == [1.0, 2.0]


def test_transient_status_stops_after_three_attempts(transport):
    client, _, kwargs, sleep = transport
    client.get.return_value = response(503)
    with pytest.raises(SourceError, match="HTTP 503"):
        utils.get_json(URL, **kwargs)
    assert client.get.call_count == 3
    assert sleep.call_count == 2


@pytest.mark.parametrize("recover", [False, True])
def test_transport_failure_retries_and_preserves_final_error(transport, recover):
    client, _, kwargs, sleep = transport
    error = (
        utils.requests.exceptions.RequestException("connection failed")
        if kwargs else httpx.ReadTimeout("read timed out")
    )
    client.get.side_effect = [error, response()] if recover else [error] * 3
    if recover:
        assert utils.get_json(URL, **kwargs) == {"ok": True}
        assert client.get.call_count == 2
        assert sleep.call_count == 1
    else:
        with pytest.raises(type(error)) as caught:
            utils.get_json(URL, **kwargs)
        assert caught.value is error
        assert client.get.call_count == 3
        assert sleep.call_count == 2
    if not kwargs:
        assert client.__exit__.call_count == client.get.call_count


def test_invalid_json_is_not_retried(transport):
    client, _, kwargs, sleep = transport
    client.get.return_value = response(text="<html>Unavailable</html>")
    with pytest.raises(SourceError, match="Non-JSON"):
        utils.get_json(URL, **kwargs)
    client.get.assert_called_once()
    sleep.assert_not_called()


@pytest.mark.parametrize("code", [403, 404])
def test_error_payload_matches_http_status_behavior(transport, code):
    client, _, kwargs, sleep = transport
    client.get.return_value = response(text=f'{{"error": {{"code": {code}}}}}')
    if code == 403:
        with pytest.raises(SourceBlocked):
            utils.get_json(URL, **kwargs)
    else:
        assert utils.get_json(URL, **kwargs) == {}
    client.get.assert_called_once()
    sleep.assert_not_called()
