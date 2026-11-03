"""
This module contains utility functions that are used in the project.
"""

import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import wraps

import httpx
from curl_cffi import requests
from lxml import html

from .exceptions import SourceBlocked, SourceError
from .logger import get_logger

_logger = get_logger("utils")

_local = threading.local()

_MAX_RETRIES = 3
_BASE_DELAY = 1.0

_TRANSIENT_ERRORS = (
    SourceBlocked,
    SourceError,
    requests.exceptions.RequestException,
    httpx.HTTPError,
)


def _get_session() -> requests.Session:
    """
    Return a per-thread browser-impersonating session.

    Each thread keeps its own session so concurrent requests are safe, while
    sequential requests in the same thread reuse the connection pool.
    """
    session = getattr(_local, "session", None)
    if session is None:
        session = requests.Session(impersonate="chrome")
        _local.session = session
    return session


def _retry(func):
    """
    Retry a fetch on transient failures with exponential backoff and jitter.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(_MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except _TRANSIENT_ERRORS as exc:
                last_error = exc
                if attempt == _MAX_RETRIES - 1:
                    raise
                delay = _BASE_DELAY * (2 ** attempt) + random.uniform(0, 0.5)
                _logger.debug(
                    "retrying %s in %.2fs after %s",
                    func.__name__, delay, type(exc).__name__,
                )
                time.sleep(delay)
        raise last_error

    return wrapper


def fetch_many(callables: list, max_workers: int = 8) -> list:
    """
    Run a list of zero-argument callables concurrently and return their results.

    Useful for fetching multiple leagues or matches in parallel. Bind arguments
    with ``functools.partial``.

    Example:
        from functools import partial
        from esd import GoalooClient
        from esd.utils import fetch_many

        client = GoalooClient()
        standings = fetch_many(
            [partial(client.get_standings, league) for league in (36, 31, 34)]
        )
    """
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(lambda fn: fn(), callables))


def to_dataframe(objects: list):
    """
    Convert a list of dataclass instances to a pandas DataFrame.

    pandas is imported lazily, so it is only required when this function is
    called. Nested dataclasses are flattened one level via ``dataclasses.asdict``.

    Example:
        from esd import GoalooClient
        from esd.utils import to_dataframe

        client = GoalooClient()
        df = to_dataframe(client.get_standings(36))
    """
    from dataclasses import asdict

    import pandas as pd

    return pd.DataFrame([asdict(obj) for obj in objects])


def get_json_playwright(
    url: str,
    chrome_path: str = None,
    proxies: dict = None,
    timeout: int = 30000,
    start_url: str = "https://www.sofascore.com/",
    headless: bool = False,
) -> dict:
    """
    Fetch JSON from a URL using a real browser (Playwright + system Chrome).

    Used as a fallback for sources that block curl_cffi with a JavaScript
    challenge (e.g. Sofascore). The browser first opens ``start_url`` so the
    source's challenge and cookies resolve, then navigates to ``url`` and
    returns the parsed JSON from the body.

    Args:
        headless: Run Chrome headless (silent). Some challenges detect
            headless, so headful is the default.

    Returns ``{}`` when the fetch fails or the challenge does not resolve.
    """
    import json as _json

    from playwright.sync_api import sync_playwright

    launch_options = {"headless": headless}
    if chrome_path:
        launch_options["executable_path"] = chrome_path
    else:
        launch_options["channel"] = "chrome"
    if proxies:
        launch_options["proxy"] = proxies

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_options)
            try:
                page = browser.new_page()
                _logger.debug("playwright: opening %s", start_url)
                page.goto(start_url, wait_until="load", timeout=timeout)
                page.wait_for_timeout(3000)
                _logger.debug("playwright: fetching JSON %s", url)
                page.goto(url, wait_until="load", timeout=timeout)
                page.wait_for_timeout(1000)
                text = page.evaluate("() => document.body.innerText")
                _logger.debug("playwright response (%d chars): %s", len(text), text[:200])
                return _json.loads(text)
            finally:
                browser.close()
    except Exception as exc:
        _logger.warning("playwright JSON fetch failed for %s: %s", url, exc)
        return {}


def get_today() -> str:
    """
    Get the current date in the format "YYYY-MM-DD".

    Returns:
        str: The current date in the format "YYYY-MM-DD".
    """
    return time.strftime("%Y-%m-%d")


def current_year(shift: int = 0) -> int:
    """
    Get the current year.

    Args:
        shift (int): The shift to the current year.

    Returns:
        int: The current year.
    """
    return datetime.now().year + shift


def camel_to_snake(name: str) -> str:
    """
    Convert a camel case string to a snake case string.

    Args:
        name (str): The camel case string.

    Returns:
        str: The snake case string.
    """
    return re.sub(
        r"([a-z0-9])([A-Z])", r"\1_\2", re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    ).lower()


@_retry
def get_json(
    url: str,
    impersonate: str | None = None,
    headers: dict | None = None,
    proxies: dict | None = None,
    timeout: float = 30.0,
) -> dict:
    """
    Get the JSON response from the given URL.

    Args:
        url (str): The URL to get the JSON response.
        impersonate (str | None): Browser impersonation for curl_cffi.
            Use "chrome" for Sofascore/Promiedos APIs. Defaults to None (uses httpx).
        headers (dict | None): Extra headers to include in the request.
        proxies (dict | None): Optional proxy dict (e.g. ``{"https": "http://..."}``).
        timeout (float): Request timeout in seconds (default 30).

    Returns:
        dict: The JSON response.

    Raises:
        SourceBlocked: If the source blocks the request (HTTP 403 / anti-bot).
        SourceError: If the source returns any other unexpected HTTP status
            or a non-JSON body.
    """
    if impersonate:
        _logger.debug(
            "fetching JSON via curl_cffi (impersonate=%s): %s", impersonate, url
        )
        if impersonate == "chrome":
            response = _get_session().get(
                url, headers=headers, proxies=proxies, timeout=timeout
            )
        else:
            response = requests.get(
                url,
                impersonate=impersonate,
                headers=headers,
                proxies=proxies,
                timeout=timeout,
            )
    else:
        _logger.debug("fetching JSON via httpx: %s", url)
        with httpx.Client(proxies=proxies, timeout=timeout, headers=headers) as client:
            response = client.get(url)

    status = response.status_code
    if status == 403:
        raise SourceBlocked(
            "Access denied (403). The source is blocking this IP. "
            "Retry from a residential connection or pass a proxy to the client."
        )
    if status == 404:
        return {}
    if status >= 400:
        raise SourceError(f"HTTP {status} from {url}")

    try:
        data = response.json()
    except ValueError as exc:
        raise SourceError(f"Non-JSON response from {url}") from exc

    if "error" in data and "code" in data["error"]:
        code = data["error"]["code"]
        if code == 403:
            raise SourceBlocked(
                "Access denied (403). The source is blocking this IP. "
                "Retry from a residential connection or pass a proxy to the client."
            )
        if code == 404:
            return {}
    return data


def get_document(proxies: dict = None, url: str = None) -> html.HtmlElement:
    """
    Get the HTML document from the given URL.

    Args:
        proxies (dict): The proxy settings.
        url (str): The URL to get the HTML document.

    Returns:
        html.HtmlElement: The HTML document.
    """
    try:
        _logger.debug("fetching document via httpx: %s", url)
        with httpx.Client(proxies=proxies, timeout=30.0) as client:
            response = client.get(url)
            response.raise_for_status()
            return html.fromstring(response.content)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return html.fromstring("")
        raise exc


def get_document_playwright(
    url: str,
    chrome_path: str = None,
    proxies: dict = None,
    timeout: int = 30000,
    wait_until: str = "load",
    headless: bool = False,
) -> html.HtmlElement:
    """
    Get the HTML document using Playwright with an existing Chrome installation.

    Unlike get_document() which uses httpx, this uses Playwright to launch
    a real browser. It requires no 'playwright install' step. It uses your
    system's Google Chrome (or a custom path you provide).

    Args:
        url (str): The URL to fetch.
        chrome_path (str | None): Path to Chrome executable, e.g.
            'C:\\\\Program Files\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe'.
            If None, Playwright auto-detects Chrome via channel='chrome'.
        proxies (dict | None): Proxy settings as {'server': 'http://proxy:port'}.
        timeout (int): Page navigation timeout in milliseconds (default 30000).
        wait_until (str): Navigation wait condition.
            Use "load" for Cloudflare-protected sites (default "load").
        headless (bool): Whether to run headless. Default False. Headful is
            required to pass Cloudflare's browser challenge. Headless is
            faster but frequently detected.

    Returns:
        html.HtmlElement: The parsed HTML document.
    """

    from playwright.sync_api import sync_playwright

    launch_options = {
        "headless": headless,
        "args": ["--disable-blink-features=AutomationControlled"],
        "ignore_default_args": ["--enable-automation"],
    }
    if chrome_path:
        launch_options["executable_path"] = chrome_path
    else:
        launch_options["channel"] = "chrome"
    if proxies:
        launch_options["proxy"] = proxies

    _logger.debug("launching browser with options: %s", launch_options)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_options)
            try:
                page = browser.new_page()
                # Hide the automation markers that Cloudflare checks.
                page.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )
                _logger.debug("navigating to %s", url)
                page.goto(url, wait_until=wait_until, timeout=timeout)
                # Poll until Cloudflare clears and the JS shell renders its content.
                content = page.content()
                for _ in range(40):
                    has_challenge = (
                        "Just a moment" in content
                        or "challenges.cloudflare.com" in content
                    )
                    try:
                        body_len = page.evaluate(
                            "() => document.body.innerText.length"
                        )
                    except Exception:
                        body_len = 0
                    if not has_challenge and body_len > 200:
                        break
                    page.wait_for_timeout(1000)
                    content = page.content()
                _logger.debug("received %d bytes from %s", len(content), url)

                if "Just a moment" in content or "challenges.cloudflare.com" in content:
                    _logger.warning("Cloudflare challenge still active for %s", url)
                    return None

                return html.fromstring(content)
            finally:
                browser.close()
    except Exception as exc:
        _logger.warning("playwright failed for %s: %s", url, exc)
        return None


def is_available_date(date: str, pattern: str) -> None:
    """
    Check if the given date is available.

    Args:
        date (str): The date to check.
        pattern (str): The pattern of the date.

    Raises:
        ValueError: If the date is invalid
    """
    date_pattern = re.compile(pattern)
    if not date_pattern.fullmatch(date):
        raise ValueError("Invalid date.") from None
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("Invalid date.") from exc


def get_api_json(url: str, headers: dict | None = None, proxies: dict | None = None) -> dict:
    """
    Get JSON from an API endpoint using Chrome impersonation via curl_cffi.

    Args:
        url (str): The API URL.
        headers (dict | None): Extra headers for the request.
        proxies (dict | None): Optional proxy dict.

    Returns:
        dict: The JSON response.
    """
    return get_json(url, impersonate="chrome", headers=headers, proxies=proxies)


@_retry
def get_text(
    url: str,
    proxies: dict | None = None,
    timeout: float = 30.0,
) -> str:
    """
    Get the raw text (HTML) response from a URL via curl_cffi.

    Used for pages that embed data in inline scripts, such as Goaloo's H2H page.

    Args:
        url (str): The URL to fetch.
        proxies (dict | None): Optional proxy dict.
        timeout (float): Request timeout in seconds (default 30).

    Returns:
        str: The raw response text.

    Raises:
        SourceBlocked: If the source blocks the request (HTTP 403).
        SourceError: If the source returns any other unexpected HTTP status.
    """
    _logger.debug("fetching text via curl_cffi: %s", url)
    response = _get_session().get(url, proxies=proxies, timeout=timeout)
    status = response.status_code
    if status == 403:
        raise SourceBlocked(
            "Access denied (403). The source is blocking this IP. "
            "Retry from a residential connection or pass a proxy to the client."
        )
    if status >= 400:
        raise SourceError(f"HTTP {status} from {url}")
    return response.text


def get_document_impersonate(
    proxies: dict = None,
    url: str = None,
    impersonate: str = "chrome",
    delay: float = 3.0,
    timeout: float = 30.0,
) -> html.HtmlElement:
    """
    Get the HTML document from a URL using curl_cffi with browser impersonation.

    This bypasses Cloudflare anti-bot protection that blocks httpx.
    Intended for sites like fbref.com. Requests are sequential-only
    (never parallelize because temporary bans are likely).

    Returns None if Cloudflare challenge is detected (caller should fall back).

    Args:
        proxies: Optional proxy dict passed to curl_cffi.
        url: The URL to fetch.
        impersonate: Browser fingerprint to impersonate (default "chrome").
        delay: Minimum seconds to sleep before the request (default 3.0).

    Returns:
        html.HtmlElement: The parsed HTML document, or None if blocked.
    """
    try:
        _logger.debug(
            "fetching document via curl_cffi (impersonate=%s, delay=%.1fs): %s",
            impersonate, delay, url,
        )
        time.sleep(delay)
        headers = {"Referer": "https://fbref.com/"}
        if impersonate == "chrome":
            response = _get_session().get(
                url, proxies=proxies, timeout=timeout, headers=headers
            )
        else:
            response = requests.get(
                url,
                impersonate=impersonate,
                proxies=proxies,
                timeout=timeout,
                headers=headers,
            )
        response.raise_for_status()
        content = response.text if hasattr(response, "text") else response.content
        if isinstance(content, str):
            if "Just a moment" in content or "challenges.cloudflare.com" in content:
                _logger.warning("Cloudflare challenge detected in curl_cffi response")
                return None
        if isinstance(content, bytes):
            return html.fromstring(content)
        return html.fromstring(content.encode("utf-8"))
    except Exception as exc:
        if hasattr(exc, "response") and getattr(exc.response, "status_code", 0) in (404, 403):
            _logger.warning(
                "curl_cffi got %d for %s",
                exc.response.status_code if hasattr(exc, "response") else 0,
                url,
            )
            return None
        raise exc
