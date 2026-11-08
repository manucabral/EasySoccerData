"""Request rate limiting for FBref."""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from functools import wraps

from .exceptions import RateLimitExceeded


def rate_limit(calls: int = 8, period: int = 60) -> callable:
    """
    Limit attempts in a shared rolling window using a monotonic clock.

    Admission is atomic across threads. The protected function runs outside the
    admission lock; this does not make a browser backend safe across threads.
    Failed attempts consume their slot. All instances share the decorated limit.

    Args:
        calls (int): The number of allowed calls.
        period (int): The time period in seconds.

    Returns:
        callable: The decorator.
    """

    if type(calls) is not int or calls < 1:
        raise ValueError("calls must be a positive integer")
    if type(period) not in (int, float) or not math.isfinite(period) or period <= 0:
        raise ValueError("period must be finite and positive")

    def decorator(func: callable) -> callable:
        timestamps = deque(maxlen=calls)
        lock = threading.Lock()

        @wraps(func)
        def wrapper(*args, **kwargs) -> any:
            with lock:
                current_time = time.monotonic()
                if len(timestamps) == calls:
                    elapsed = current_time - timestamps[0]
                    if elapsed < period:
                        raise RateLimitExceeded(f"FBref request limit reached. Retry in {period - elapsed:.2f} seconds.")
                timestamps.append(current_time)
            return func(*args, **kwargs)

        return wrapper

    return decorator
