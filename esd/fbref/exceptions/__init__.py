"""
This module contains the exceptions that are raised by the fbref module.
"""


class FBrefException(Exception):
    """
    Base exception for the fbref module.
    """


class InvalidMatchId(FBrefException):
    """
    Exception raised when the match id is invalid.
    """

    def __init__(self, message: str = "Invalid match id.") -> None:
        super().__init__(message)


class RateLimitExceeded(FBrefException):
    """
    Exception raised when the rate limit is exceeded.
    """

    def __init__(self, message: str = "Rate limit exceeded.") -> None:
        super().__init__(message)


class CloudflareBlock(FBrefException):
    """
    Exception raised when Cloudflare blocks the request (challenge page).
    """

    def __init__(self, message: str = "Cloudflare challenge detected.") -> None:
        super().__init__(message)
