"""
Custom exceptions for the INMET stations package.
"""


class InvalidUnitError(ValueError):
    """
    Custom exception class that is raised when an invalid unit is provided.

    Parameters
    ----------
    message : str
        The error message.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidLatitudeError(ValueError):
    """
    Custom exception class that is raised when an invalid latitude value is
    provided.

    Parameters
    ----------
    message : str
        The error message.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidLongitudeError(ValueError):
    """
    Custom exception class that is raised when an invalid longitude value is
    provided.

    Parameters
    ----------
    message : str
        The error message.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
