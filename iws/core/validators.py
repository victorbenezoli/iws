"""
Date and parameter validation utilities.
"""

from typing import Tuple

import pandas as pd

from ..common.types import DateType


def validate_date_range(
    start_date: DateType, end_date: DateType
) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """
    Validates and converts date range to pandas Timestamps.

    Parameters
    ----------
    start_date : DateType
        The start date for the data range.
    end_date : DateType
        The end date for the data range.

    Returns
    -------
    Tuple[pd.Timestamp, pd.Timestamp]
        Validated start and end dates as Timestamps.

    Raises
    ------
    ValueError
        If dates are outside valid range or start_date > end_date.
    """
    try:
        dt_start_date = pd.Timestamp(start_date)
        dt_end_date = pd.Timestamp(end_date)
    except ValueError as e:
        msg = f"Invalid date format: {e}"
        raise ValueError(msg) from e

    if dt_start_date.year < 2000 or dt_end_date.year > pd.Timestamp.now().year:
        msg = "Data is only available from the year 2000 to the current year."
        raise ValueError(msg)

    if dt_start_date > dt_end_date:
        msg = "Start date must be earlier than or equal to end date."
        raise ValueError(msg)

    return dt_start_date, dt_end_date
