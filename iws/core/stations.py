"""
INMET weather stations management and search functionality.
"""

import concurrent.futures
import logging
import pickle
from pathlib import Path
from typing import List

import numpy as np
from tqdm import tqdm

from ..api import InmetAPIClient
from ..models import Distance, GeoCoordinates, InmetStation


class InmetStations:
    """
    A class to find INMET weather stations based on geographical coordinates.

    Parameters
    ----------
    update : bool, optional
        Whether to update the weather station data from the API. Default is
        True.

    Attributes
    ----------
    weather_stations : List[InmetStation]
        A list of InmetStation objects representing the weather stations.
    """

    def __init__(self, update: bool = True) -> None:
        """
        Initializes the InmetStations object and retrieves weather station data.

        Parameters
        ----------
        update : bool, optional
            Whether to update the weather station data from the API. Default
            is True.
        """
        self.weather_stations = self._build_weather_station_list(update)

    def _build_weather_station_list(self, update: bool) -> List[InmetStation]:
        """
        Builds the list of weather stations.

        Parameters
        ----------
        update : bool
            Whether to update the station data.

        Returns
        -------
        List[InmetStation]
            List of weather stations.
        """
        tempfile = Path("/tmp/weather_stations.obj")
        if not tempfile.exists():
            tempfile.touch()

        if update or (not tempfile.exists()):
            auto_weather_stations = InmetAPIClient.get_stations_data("T")
            manual_weather_stations = InmetAPIClient.get_stations_data("M")
            raw_weather_stations = auto_weather_stations + manual_weather_stations
            weather_stations = []

            print("Looking for all INMET stations. Please wait...")

            def create_station(station: dict) -> InmetStation:
                """
                Create an InmetStation object from a dictionary of station data.

                Parameters
                ----------
                station : dict
                    A dictionary containing the station data.

                Returns
                -------
                InmetStation
                    An InmetStation object created from the provided station
                    data.
                """
                args = {
                    "coordinates": GeoCoordinates(
                        float(station.get("VL_LATITUDE", np.nan)),
                        float(station.get("VL_LONGITUDE", np.nan)),
                    ),
                    "altitude": float(station.get("VL_ALTITUDE", np.nan)),
                    "name": station.get("DC_NOME"),
                    "station_code": station.get("CD_ESTACAO"),
                    "is_operating": station.get("CD_SITUACAO") == "Operante",
                    "operate_since": station.get("DT_INICIO_OPERACAO"),
                    "operated_until": station.get("DT_FIM_OPERACAO"),
                    "type_of_operation": "Traditional"
                    if station.get("TP_ESTACAO") == "Convencional"
                    else "Automatic",
                }
                return InmetStation(**args)

            with concurrent.futures.ThreadPoolExecutor() as executor:
                weather_stations = list(
                    tqdm(
                        executor.map(create_station, raw_weather_stations),
                        total=len(raw_weather_stations),
                        desc="Criando estações",
                    )
                )

            with open(tempfile, "wb") as f:
                pickle.dump(weather_stations, f, pickle.HIGHEST_PROTOCOL)

        else:
            with open(tempfile, "rb") as f:
                weather_stations = pickle.load(f)

        return weather_stations

    def __getitem__(self, station_code: str) -> InmetStation:
        """
        Gets a weather station by its station code.

        Parameters
        ----------
        station_code : str
            The station code of the weather station to retrieve.

        Returns
        -------
        InmetStation
            The InmetStation object with the specified station code.

        Raises
        ------
        KeyError
            If no station with the specified code is found.

        """
        for station in self.weather_stations:
            if station.station_code == station_code:
                return station
        msg = f"Station with code {station_code} not found."
        raise KeyError(msg)

    def list(self) -> List[InmetStation]:
        """
        Lists all weather stations.

        Returns
        -------
        List[InmetStation]
            A list of all InmetStation objects.

        """
        return self.weather_stations

    def find_nearest(
        self,
        location: GeoCoordinates,
        n_nearest: int = 1,
        only_operating: bool = True,
        only_automatic: bool = False,
    ) -> List[InmetStation]:
        """
        Finds the nearest weather stations to a specific geographical location.

        Parameters
        ----------
        location : GeoCoordinates
            The geographical location to search for weather stations.
        n_nearest : int, optional
            The number of nearest weather stations to return. Default is 1.
        only_operating : bool, optional
            Whether to only include operating weather stations. Default is True.
        only_automatic : bool, optional
            Whether to only include automatic weather stations. Default is False.

        Returns
        -------
        List[InmetStation]
            A list of InmetStation objects representing the nearest weather
            stations.
        """
        if only_operating:
            list_of_weather_stations = list(
                filter(lambda station: station.is_operating, self.weather_stations)
            )
        else:
            list_of_weather_stations = self.weather_stations

        if only_automatic:
            list_of_weather_stations = list(
                filter(
                    lambda station: station.type_of_operation == "Automatic",
                    list_of_weather_stations,
                )
            )

        distances = [
            (station, location.distance_to(station.coordinates).distance)
            for station in list_of_weather_stations
        ]
        distances.sort(key=lambda x: x[1])

        return [station for station, _ in distances[:n_nearest]]

    def find_around(
        self,
        location: GeoCoordinates,
        maximum_distance: Distance = Distance(100.0, "km"),
        only_operating: bool = True,
    ) -> List[InmetStation]:
        """
        Finds weather stations around a specific geographical location within a
        given maximum distance.

        Parameters
        ----------
        location : GeoCoordinates
            The geographical location to search for weather stations.
        maximum_distance : Distance, optional
            The maximum distance from the location to search for weather
            stations. Default is Distance(100.0, "km").
        only_operating : bool, optional
            Whether to only include operating weather stations. Default is True.

        Returns
        -------
        List[InmetStation]
            A list of InmetStation objects representing the found weather
            stations.
        """
        # returns a list of stations that are currently operating
        if only_operating:
            operating_stations = list(
                filter(lambda station: station.is_operating, self.weather_stations)
            )
        else:
            operating_stations = self.weather_stations

        operating_stations = [
            (station, location.distance_to(station.coordinates))
            for station in operating_stations
            if location.distance_to(station.coordinates) <= maximum_distance
        ]

        print(
            *[
                f"{station.name}: {distance}"
                for station, distance in operating_stations
            ],
            sep="\n",
        )

        # List of weather stations that are located at the location provided.
        if not operating_stations:
            msg = "No weather station could be located at the location provided."
            logging.warning(msg)

        return [station for station, _ in operating_stations]
