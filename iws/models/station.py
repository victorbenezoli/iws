"""
INMET weather station model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Union

from .coordinates import Distance, GeoCoordinates


@dataclass(slots=True)
class InmetStation:
    """
    A class representing an INMET weather station.

    Attributes
    ----------
    name : str
        The name of the weather station.
    station_code : str
        The unique code of the weather station.
    coordinates : GeoCoordinates
        The geographical coordinates of the weather station as a GeoCoordinates
        object.
    altitude : float
        The altitude of the weather station in meters.
    is_operating : bool
        A boolean indicating whether the weather station is currently operating.
    operate_since : str
        The date when the weather station started operating.
    operated_until : str
        The date when the weather station stopped operating (if applicable).
    type_of_operation : Literal["Automatic", "Traditional"]
        The type of operation of the weather station, either "Automatic" or
        "Traditional".
    """

    name: str
    station_code: str
    coordinates: GeoCoordinates
    altitude: float
    is_operating: bool
    operate_since: str
    operated_until: str
    type_of_operation: Literal["Automatic", "Traditional"]

    def __repr__(self) -> str:
        return (
            f"InmetStation(name={self.name}, station_code={self.station_code}, "
            f"coordinates={self.coordinates.__str__()}"
        )

    def __str__(self) -> str:
        return f"{self.name} ({self.station_code}) - {self.coordinates.__str__()}"

    def distance_to(self, other: Union[InmetStation, GeoCoordinates]) -> Distance:
        """
        Calculates the distance from this weather station to another weather
        station or geographical coordinates.

        Parameters
        ----------
        other : InmetStation | GeoCoordinates
            The other weather station or geographical coordinates to calculate
            the distance to.

        Returns
        -------
        Distance
            A Distance object representing the distance between the two weather
            stations or coordinates.

        Raises
        ------
        TypeError
            If the 'other' parameter is not an InmetStation or GeoCoordinates
            object.
        """
        if isinstance(other, InmetStation):
            return self.coordinates.distance_to(other.coordinates)
        elif isinstance(other, GeoCoordinates):
            return self.coordinates.distance_to(other)
        else:
            msg = (
                f"Invalid type for 'other': {type(other)}. "
                f"Must be InmetStation or GeoCoordinates."
            )
            raise TypeError(msg)
