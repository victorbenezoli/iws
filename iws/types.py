"""
Type definitions for the INMET stations package.
"""

from typing import Annotated, Literal, Union

import pandas as pd

DistanceUnit = Annotated[str, Literal["cm", "m", "km", "mi"]]
TimeAggregation = Annotated[str, Literal["hourly", "daily", "monthly"]]
DateType = Union[str, pd.Timestamp]
