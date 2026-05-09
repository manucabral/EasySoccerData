"""
FBref service module.
"""

from __future__ import annotations

import time
from collections import deque
from functools import wraps

from .exceptions import RateLimitExceeded


def rate_limit(calls: int = 8, period: int = 60) -> callable:
    """
    A decorator to rate limit the number of calls to a function.

    Args:
        calls (int): The number of allowed calls.
        period (int): The time period in seconds.

    Returns:
        callable: The decorator.
    """

    def decorator(func: callable) -> callable:
        timestamps = deque(maxlen=calls)

        @wraps(func)
        def wrapper(*args, **kwargs) -> any:
            current_time = time.time()
            if len(timestamps) == calls:
                oldest = timestamps[0]
                elapsed = current_time - oldest
                if elapsed < period:
                    sleep_time = period - elapsed
                    raise RateLimitExceeded(
                        f"Please wait {sleep_time:.2f} seconds before retrying. "
                        "Attempting to bypass? Use proxies."
                    )

            timestamps.append(time.time())
            return func(*args, **kwargs)

        return wrapper

    return decorator
