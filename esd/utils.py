"""
This module contains utility functions that are used in the project.
"""

import re
import time
from datetime import datetime

import httpx
from curl_cffi import requests
from lxml import html


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


def get_json(url: str, impersonate: str | None = None, headers: dict | None = None) -> dict:
    """
    Get the JSON response from the given URL.

    Args:
        url (str): The URL to get the JSON response.
        impersonate (str | None): Browser impersonation for curl_cffi.
            Use "chrome" for Sofascore/Promiedos APIs. Defaults to None (uses httpx).
        headers (dict | None): Extra headers to include in the request.

    Returns:
        dict: The JSON response.
    """

    try:
        if impersonate:
            response = requests.get(url, impersonate=impersonate, headers=headers)
            response.raise_for_status()
            data = response.json()
            if "error" in data and "code" in data["error"]:
                code = data["error"]["code"]
                if code == 403:
                    print(
                        "Access denied. Please use a proxy, VPN or renew your ip address."
                    )
                if code == 404:
                    print("No found.")
                return {}
            return data
        with httpx.Client() as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return {}
        raise exc


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
        with httpx.Client(proxy=proxies) as client:
            response = client.get(url)
            response.raise_for_status()
            return html.fromstring(response.content)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return html.fromstring("")
        raise exc


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
    if date_pattern.match(date):
        datetime.strptime(date, "%d-%m-%Y")
    else:
        raise ValueError("Invalid date.") from None


def get_api_json(url: str, headers: dict | None = None) -> dict:
    """
    Get JSON from an API endpoint using Chrome impersonation via curl_cffi.

    Args:
        url (str): The API URL.
        headers (dict | None): Extra headers for the request.

    Returns:
        dict: The JSON response.
    """
    return get_json(url, impersonate="chrome", headers=headers)
