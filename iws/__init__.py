"""
INMET Stations Package

A Python package for accessing and analyzing data from INMET (Instituto Nacional de
Meteorologia) weather stations in Brazil.
"""

from .core import InmetStations, get_climate_data
from .exceptions import InvalidLatitudeError, InvalidLongitudeError, InvalidUnitError
from .models import Distance, GeoCoordinates, InmetStation
from .types import DateType, DistanceUnit, TimeAggregation

__version__ = "1.0.0"
__all__ = [
    "InmetStation",
    "GeoCoordinates",
    "Distance",
    "InmetStations",
    "get_climate_data",
    "DateType",
    "DistanceUnit",
    "TimeAggregation",
    "InvalidUnitError",
    "InvalidLatitudeError",
    "InvalidLongitudeError",
]
