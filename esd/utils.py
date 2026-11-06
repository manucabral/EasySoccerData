"""
This module contains utility functions that are used in the project.
"""

import json
import random
import re
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
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
    requests.exceptions.RequestException,
    httpx.HTTPError,
)

_CAMEL_RE_1 = re.compile(r"(.)([A-Z][a-z]+)")
_CAMEL_RE_2 = re.compile(r"([a-z0-9])([A-Z])")


class TTLCache:
    """
    Thread-safe bounded dictionary with time-to-live expiration.
    """

    def __init__(self, ttl: float = 30.0, maxsize: int = 256) -> None:
        self.ttl = ttl
        self.maxsize = maxsize
        self._data: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key):
        now = time.monotonic()
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            ts, value = entry
            if now - ts >= self.ttl:
                del self._data[key]
                return None
            self._data.move_to_end(key)
            return value

    def set(self, key, value) -> None:
        now = time.monotonic()
        with self._lock:
            if key in self._data:
                del self._data[key]
            self._data[key] = (now, value)
            while len(self._data) > self.maxsize:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


def _get_session(impersonate: str = "chrome") -> requests.Session:
    """
    Return a per-thread browser-impersonating session.

    Each thread keeps its own session so concurrent requests are safe, while
    sequential requests in the same thread reuse the connection pool.
    """
    sessions = getattr(_local, "sessions", None)
    if sessions is None:
        sessions = {}
        _local.sessions = sessions
    session = sessions.get(impersonate)
    if session is None:
        session = requests.Session(impersonate=impersonate)
        sessions[impersonate] = session
    return session


def _close_thread_sessions() -> None:
    """Close any curl_cffi sessions attached to the current thread."""
    sessions = getattr(_local, "sessions", None)
    if sessions:
        for session in sessions.values():
            try:
                session.close()
            except Exception:
                pass
        sessions.clear()


def _is_retryable_source_error(exc: SourceError) -> bool:
    msg = str(exc)
    return any(
        code in msg
        for code in ("HTTP 429", "HTTP 500", "HTTP 502", "HTTP 503", "HTTP 504")
    )


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
            except SourceError as exc:
                if not _is_retryable_source_error(exc) or attempt == _MAX_RETRIES - 1:
                    raise
                last_error = exc
            except _TRANSIENT_ERRORS as exc:
                last_error = exc
                if attempt == _MAX_RETRIES - 1:
                    raise
            delay = _BASE_DELAY * (2**attempt) + random.uniform(0, 0.5)
            _logger.debug(
                "retrying %s in %.2fs after %s",
                func.__name__,
                delay,
                type(last_error).__name__,
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

    def _run(fn):
        try:
            return fn()
        finally:
            _close_thread_sessions()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(_run, callables))


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


class BrowserSession:
    """
    A persistent Playwright browser, reused across requests.

    Launching Chrome and passing the source's challenge is expensive, so one
    browser is shared across requests in the same thread. Call ``close()`` to
    release the browser and its Chrome process.
    """

    def __init__(
        self,
        chrome_path: str = None,
        proxies: dict = None,
        headless: bool = False,
    ) -> None:
        self.chrome_path = chrome_path
        self.proxies = proxies
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._lock = threading.Lock()
        self._warmed_urls: set[str] = set()

    def __enter__(self) -> "BrowserSession":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _launch(self) -> None:
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        launch_options = {
            "headless": self.headless,
            "args": ["--disable-blink-features=AutomationControlled"],
            "ignore_default_args": ["--enable-automation"],
        }
        if self.chrome_path:
            launch_options["executable_path"] = self.chrome_path
        else:
            launch_options["channel"] = "chrome"
        if self.proxies:
            launch_options["proxy"] = self.proxies
        try:
            self._browser = self._playwright.chromium.launch(**launch_options)
        except Exception:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
            raise

    def new_page(self):
        """Return a new page in the shared browser, with stealth applied."""
        if self._browser is not None and not self._browser.is_connected():
            self.close()
        if self._browser is None:
            self._launch()
        page = self._browser.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return page

    @contextmanager
    def page(self):
        """
        Yield a page in the shared browser.

        The lock serializes access because Playwright's sync API is not
        thread-safe. The page is always closed when the context exits.
        """
        with self._lock:
            page = self.new_page()
            try:
                yield page
            finally:
                try:
                    page.close()
                except Exception:
                    pass

    def close(self) -> None:
        """Close the browser and release the Playwright driver."""
        self._warmed_urls.clear()
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    def __del__(self) -> None:
        self.close()


def _fetch_json_via_page(
    page,
    url: str,
    timeout: int,
    start_url: str,
    session: BrowserSession = None,
) -> dict:
    import json as _json

    need_warmup = session is None or start_url not in session._warmed_urls
    if need_warmup:
        _logger.debug("playwright: opening %s", start_url)
        page.goto(start_url, wait_until="load", timeout=timeout)
        page.wait_for_timeout(3000)
        if session is not None:
            session._warmed_urls.add(start_url)

    _logger.debug("playwright: fetching JSON %s", url)
    page.goto(url, wait_until="load", timeout=timeout)
    text = page.evaluate("() => document.body ? document.body.innerText : ''")
    _logger.debug("playwright response (%d chars): %s", len(text), text[:200])
    try:
        return _json.loads(text)
    except ValueError:
        if not need_warmup and session is not None:
            session._warmed_urls.discard(start_url)
            _logger.debug("playwright: retrying with warm-up via %s", start_url)
            page.goto(start_url, wait_until="load", timeout=timeout)
            page.wait_for_timeout(3000)
            session._warmed_urls.add(start_url)
            page.goto(url, wait_until="load", timeout=timeout)
            text = page.evaluate("() => document.body ? document.body.innerText : ''")
            return _json.loads(text)
        raise


def get_json_playwright(
    url: str,
    chrome_path: str = None,
    proxies: dict = None,
    timeout: int = 30000,
    start_url: str = "https://www.sofascore.com/",
    headless: bool = False,
    session: BrowserSession = None,
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
        session: Optional :class:`BrowserSession` to reuse an existing browser.

    Returns ``{}`` when the fetch fails or the challenge does not resolve.
    """
    if session is not None:
        try:
            with session.page() as page:
                return _fetch_json_via_page(page, url, timeout, start_url, session)
        except Exception as exc:
            _logger.warning("playwright JSON fetch failed for %s: %s", url, exc)
            return {}

    local = BrowserSession(chrome_path, proxies, headless)
    try:
        page = local.new_page()
        return _fetch_json_via_page(page, url, timeout, start_url, local)
    except Exception as exc:
        _logger.warning("playwright JSON fetch failed for %s: %s", url, exc)
        return {}
    finally:
        local.close()


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
    return _CAMEL_RE_2.sub(r"\1_\2", _CAMEL_RE_1.sub(r"\1_\2", name)).lower()


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
        response = _get_session(impersonate).get(
            url, headers=headers, proxies=proxies, timeout=timeout
        )
    else:
        _logger.debug("fetching JSON via httpx: %s", url)
        proxy = (
            (proxies.get("https") or proxies.get("http"))
            if isinstance(proxies, dict)
            else proxies
        )
        with httpx.Client(proxy=proxy, timeout=timeout, headers=headers) as client:
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
        data = json.loads(response.text.lstrip("\ufeff"))
    except ValueError as exc:
        raise SourceError(f"Non-JSON response from {url}") from exc

    if isinstance(data, dict) and "error" in data and isinstance(data["error"], dict):
        code = data["error"].get("code")
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
        proxy = (
            (proxies.get("https") or proxies.get("http"))
            if isinstance(proxies, dict)
            else proxies
        )
        with httpx.Client(proxy=proxy, timeout=30.0) as client:
            response = client.get(url)
            response.raise_for_status()
            return html.fromstring(response.content)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return html.fromstring("<html><body></body></html>")
        raise exc


def _fetch_document_via_page(page, url: str, timeout: int, wait_until: str):
    _logger.debug("navigating to %s", url)
    page.goto(url, wait_until=wait_until, timeout=timeout)
    content = ""
    prev_len = 0
    stable = 0
    saw_challenge = False
    for i in range(60):
        try:
            content = page.content()
        except Exception:
            # The page is mid-navigation (challenge redirect); wait and retry.
            page.wait_for_timeout(1000)
            continue
        has_challenge = (
            "Just a moment" in content or "challenges.cloudflare.com" in content
        )
        if has_challenge:
            saw_challenge = True
        cur_len = len(content)
        if not has_challenge and cur_len > 1000:
            if not saw_challenge and i == 0:
                break
            if cur_len == prev_len:
                stable += 1
                if stable >= 2:
                    break
            else:
                stable = 0
        else:
            stable = 0
        prev_len = cur_len
        page.wait_for_timeout(1000)
    _logger.debug("received %d bytes from %s", len(content), url)

    if "Just a moment" in content or "challenges.cloudflare.com" in content:
        _logger.warning("Cloudflare challenge still active for %s", url)
        return None

    return html.fromstring(content)


def get_document_playwright(
    url: str,
    chrome_path: str = None,
    proxies: dict = None,
    timeout: int = 30000,
    wait_until: str = "load",
    headless: bool = False,
    session: BrowserSession = None,
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
        session (BrowserSession | None): Optional persistent browser to reuse
            instead of launching a new Chrome per call.

    Returns:
        html.HtmlElement: The parsed HTML document.
    """
    if session is not None:
        try:
            with session.page() as page:
                return _fetch_document_via_page(page, url, timeout, wait_until)
        except Exception as exc:
            _logger.warning("playwright failed for %s: %s", url, exc)
            return None

    local = BrowserSession(chrome_path, proxies, headless)
    try:
        page = local.new_page()
        return _fetch_document_via_page(page, url, timeout, wait_until)
    except Exception as exc:
        _logger.warning("playwright failed for %s: %s", url, exc)
        return None
    finally:
        local.close()


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


def get_api_json(
    url: str, headers: dict | None = None, proxies: dict | None = None
) -> dict:
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
    impersonate: str = "chrome",
) -> str:
    """
    Get the raw text (HTML) response from a URL via curl_cffi.

    Used for pages that embed data in inline scripts, such as Goaloo's H2H page.

    Args:
        url (str): The URL to fetch.
        proxies (dict | None): Optional proxy dict.
        timeout (float): Request timeout in seconds (default 30).
        impersonate (str): Browser profile for curl_cffi (default "chrome").

    Returns:
        str: The raw response text.

    Raises:
        SourceBlocked: If the source blocks the request (HTTP 403).
        SourceError: If the source returns any other unexpected HTTP status.
    """
    _logger.debug("fetching text via curl_cffi: %s", url)
    response = _get_session(impersonate).get(url, proxies=proxies, timeout=timeout)
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
            impersonate,
            delay,
            url,
        )
        time.sleep(delay)
        headers = {"Referer": "https://fbref.com/"}
        response = _get_session(impersonate).get(
            url, proxies=proxies, timeout=timeout, headers=headers
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
        if hasattr(exc, "response") and getattr(exc.response, "status_code", 0) in (
            404,
            403,
        ):
            _logger.warning(
                "curl_cffi got %d for %s",
                exc.response.status_code if hasattr(exc, "response") else 0,
                url,
            )
            return None
        raise exc
