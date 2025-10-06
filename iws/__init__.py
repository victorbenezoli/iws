"""
INMET Weather Stations Package

A Python package for accessing and analyzing data from INMET (Instituto Nacional de
Meteorologia) weather stations in Brazil.
"""

from .common import exceptions, types
from .core import InmetStations, get_climate_data
from .models import Distance, GeoCoordinates, InmetStation

__version__ = "1.0.0"
__all__ = [
    "InmetStation",
    "GeoCoordinates",
    "Distance",
    "InmetStations",
    "get_climate_data",
    "exceptions",
    "types",
]
