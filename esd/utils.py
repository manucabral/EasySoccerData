"""
This module contains utility functions that are used in the project.
"""

import json
import re
import time
from datetime import datetime

import httpx
from lxml import html
from playwright.sync_api import Page


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


def get_json(page: Page, url: str) -> dict:
    """
    Get the JSON response from the given URL.
    Only works with the Sofascore API.

    Args:
        page (Page): The Playwright page object.
        url (str): The URL to get the JSON response.

    Returns:
        dict: The JSON response.
    """

    try:
        if page is None:
            with httpx.Client() as client:
                response = client.get(url)
                response.raise_for_status()
                return response.json()
        page.goto(url, wait_until="networkidle")
        content = page.content()
        doc = html.fromstring(content)
        pre_text_list = doc.xpath("//pre/text()")
        if pre_text_list:
            json_string = pre_text_list[0].strip()
            try:
                data = json.loads(json_string)
                if "error" in data and "code" in data["error"]:
                    code = data["error"]["code"]
                    if code == 403:
                        print(
                            "Access denied. Please use a proxt, VPN or renew your ip address."
                        )
                    if code == 404:
                        print("No found.")
                    return {}
                return data
            except json.JSONDecodeError as e:
                print("Could not decode JSON:", e)
                return {}
        return {}
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
