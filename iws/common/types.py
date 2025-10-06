"""
Type definitions for the INMET stations package.
"""

from typing import Annotated, Literal, Union

import pandas as pd

# DistanceUnit can be "cm", "m", "km", or "mi"
DistanceUnit = Annotated[str, Literal["cm", "m", "km", "mi"]]

# TimeAggregation can be "hourly", "daily", or "monthly"
TimeAggregation = Annotated[str, Literal["hourly", "daily", "monthly"]]

# DateType can be a string or a pandas Timestamp
DateType = Union[str, pd.Timestamp]
