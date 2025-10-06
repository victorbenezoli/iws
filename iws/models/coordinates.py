"""
Geographical coordinates and distance models.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import get_args

import numpy as np
from shapely.geometry import Point

from ..common.exceptions import (
    InvalidLatitudeError,
    InvalidLongitudeError,
    InvalidUnitError,
)
from ..common.types import DistanceUnit


class Latitude(float):
    """
    A class representing a latitude coordinate.

    Attributes
    ----------
    value : float
        The latitude value in degrees.

    Raises
    ------
    ValueError
        If the latitude value is not between -90 and 90 degrees.
    """

    def __new__(cls, value: float) -> Latitude:
        if not -90 <= value <= 90:
            msg = (
                f"Invalid latitude value: {value}. "
                f"Latitude must be between -90 and 90 degrees."
            )
            raise InvalidLatitudeError(msg)
        return float.__new__(cls, value)


class Longitude(float):
    """
    A class representing a longitude coordinate.

    Attributes
    ----------
    value : float
        The longitude value in degrees.

    Raises
    ------
    ValueError
        If the longitude value is not between -180 and 180 degrees.
    """

    def __new__(cls, value: float) -> Longitude:
        if not -180 <= value <= 180:
            msg = (
                f"Invalid longitude value: {value}. "
                f"Longitude must be between -180 and 180 degrees."
            )
            raise InvalidLongitudeError(msg)
        return float.__new__(cls, value)


@dataclass(order=True)
class Distance:
    """
    A class representing a distance with a specific unit.

    Attributes
    ----------
    distance : float
        The distance value.
    unit : Literal["cm", "m", "km", "mi"]
        The unit of the distance. Valid units are 'cm', 'm', 'km', and 'mi'.

    Raises
    ------
    InvalidUnitError
        If an invalid unit is provided.

    Methods
    -------
    transform_to(unit: str) -> Distance
        Transforms the distance to the specified unit and returns a new
        Distance object.
    """

    distance: float
    unit: DistanceUnit

    def __repr__(self) -> str:
        return f"Distance({self.distance:.2f} {self.unit})"

    def transform_to(self, unit: DistanceUnit) -> Distance:
        """
        Transforms the distance to the specified unit and returns a new
        Distance object.

        Parameters
        ----------
        unit : str
            The unit to which the distance should be transformed. Valid units
            are 'cm', 'm', 'km', and 'mi'.

        Returns
        -------
        Distance
            A new Distance object with the distance converted to the specified
            unit.

        Raises
        ------
        InvalidUnitError
            If an invalid unit is provided.
        """
        valid_units = get_args(get_args(DistanceUnit)[0])

        CONVERSION_FACTOR: dict[DistanceUnit, float] = {
            "m": 1,
            "cm": 100,
            "km": 0.001,
            "mi": 0.000621371,
        }

        if unit not in valid_units:
            msg = f"Invalid unit: {unit}. Valid units are {valid_units}."
            raise InvalidUnitError(msg)

        conversion_factor = CONVERSION_FACTOR[unit] / CONVERSION_FACTOR[self.unit]
        new_distance = self.distance * conversion_factor
        return Distance(new_distance, unit)


class GeoCoordinates:
    """
    A class representing geographical coordinates.

    Attributes
    ----------
    latitude : Latitude
        The latitude coordinate.
    longitude : Longitude
        The longitude coordinate.
    """

    def __init__(self, latitude: float, longitude: float) -> None:
        self.latitude = Latitude(latitude)
        self.longitude = Longitude(longitude)

    def __repr__(self) -> str:
        return (
            f"GeoCoordinates(latitude={round(self.latitude, 2)}˚, "
            f"longitude={round(self.longitude, 2)}˚)"
        )

    def __str__(self) -> str:
        degrees = int(self.latitude), int(self.longitude)
        minutes = (
            abs(self.latitude - degrees[0]) * 60,
            abs(self.longitude - degrees[1]) * 60,
        )
        seconds = (
            abs(minutes[0] - int(minutes[0])) * 60,
            abs(minutes[1] - int(minutes[1])) * 60,
        )
        return (
            f"({int(degrees[0])}˚{int(minutes[0])}'{int(seconds[0])}\","
            f"{int(degrees[1])}˚{int(minutes[1])}'{int(seconds[1])}\")"
        )

    def distance_to(self, other: GeoCoordinates) -> Distance:
        """
        Calculates the distance between two geographical coordinates using the
        Haversine formula.

        Parameters
        ----------
        other : GeoCoordinates
            The other geographical coordinates to calculate the distance to.

        Returns
        -------
        Distance
            The distance between the two geographical coordinates in kilometers.
        """
        # Haversine formula
        R = 6371  # Radius of the Earth in kilometers
        lat_rad = np.radians(np.array([other.latitude, self.latitude]))
        lon_rad = np.radians(np.array([other.longitude, self.longitude]))

        delta_lat = np.subtract(*lat_rad)
        delta_lon = np.subtract(*lon_rad)

        a = (
            np.sin(delta_lat / 2) ** 2
            + np.cos(lat_rad[0]) * np.cos(lat_rad[1]) * np.sin(delta_lon / 2) ** 2
        )
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

        return Distance(R * c, "km")

    def to_point(self) -> Point:
        """
        Converts the geographical coordinates to a Shapely Point object.

        Returns
        -------
        Point
            A Shapely Point object representing the geographical coordinates.
        """
        return Point(self.longitude, self.latitude)
