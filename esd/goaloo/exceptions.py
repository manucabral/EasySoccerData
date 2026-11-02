"""
Exceptions for the Goaloo submodule.
"""


class GoalooException(Exception):
    """
    Base class for Goaloo exceptions.
    """


class LeagueNotFound(GoalooException):
    """
    Exception raised when a league/competition has no data on Goaloo.
    """

    def __init__(self, league_id: int = None) -> None:
        message = "League not found on Goaloo."
        if league_id is not None:
            message = f"League not found on Goaloo (league_id={league_id})."
        super().__init__(message)
