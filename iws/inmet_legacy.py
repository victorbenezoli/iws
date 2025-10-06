from __future__ import annotations

import concurrent.futures
import csv as pycsv
import logging
import pickle
import re
from collections import defaultdict
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Annotated, Literal, get_args
from zipfile import ZipFile

import httpx
import numpy as np
import pandas as pd
from remotezip import RemoteZip
from shapely.geometry import Point
from tqdm import tqdm

logging.basicConfig(
    level=logging.WARNING,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

DistanceUnit = Annotated[str, Literal["cm", "m", "km", "mi"]]
TimeAggregation = Annotated[str, Literal["hourly", "daily", "monthly"]]
DateType = Annotated[str, Literal["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"]]


def validate_date_format(date_string: str) -> np.datetime64:
    """
    Validates if the provided date string matches any of the accepted formats and
    converts it to a numpy datetime64 object.

    Parameters
    ----------
    date_string : str
        The date string to be validated and converted.

    Returns
    -------
    np.datetime64
        A numpy datetime64 object representing the validated date.

    Raises
    ------
    ValueError
        If the date string does not match any of the accepted formats.

    """
    valid_formats = get_args(get_args(DateType)[1])
    for fmt in valid_formats:
        try:
            return np.datetime64(pd.to_datetime(date_string, format=fmt))
        except ValueError:
            continue
    raise ValueError(f"Date '{date_string}' is not in a valid format.")


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


@dataclass(order=True, slots=True)
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
        float
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


class InmetDataList:
    """
    A class to fetch and organize INMET automatic weather station data files.
    """

    def __init__(self) -> None:
        stations = defaultdict(list)
        for year in range(2000, pd.Timestamp.now().year + 1):
            zipfile = self._fetch_zipfile(year)
            file_names = self._list_files_in_zip(zipfile)
            station_codes = self._extract_station_codes(file_names)
            for code in station_codes:
                stations[code].append(next(filter(lambda x: code in x, file_names)))
        self.__stations = stations

    def __repr__(self) -> str:
        return f"InmetDataList(num_stations={len(self.__stations)})"

    def __str__(self) -> str:
        return f"InmetDataList with {len(self.__stations)} stations."

    def _fetch_zipfile(self, year: int) -> BytesIO:
        """
        Fetch the zip file for a given year from the INMET website.

        Parameters
        ----------
        year : int
            The year for which to fetch the zip file.

        Returns
        -------
        BytesIO
            A BytesIO object containing the contents of the zip file.

        Raises
        ------
        ConnectionError
            If the request to fetch the zip file fails.

        """
        url = f"https://portal.inmet.gov.br/uploads/dadoshistoricos/{year}.zip"
        response = httpx.get(
            url,
            headers={
                "Range": f"bytes=-{2**20}",
                "User-Agent": "Mozilla/5.0",
            },
        )
        return BytesIO(response.content)

    def _list_files_in_zip(self, zipfile: BytesIO) -> list[str]:
        """
        Lists the files contained in a zip file.

        Parameters
        ----------
        zipfile : BytesIO
            A BytesIO object containing the zip file.

        Returns
        -------
        list[str]
            A list of file names contained in the zip file.

        """
        with ZipFile(zipfile) as z:
            return z.namelist()

    def _extract_station_codes(self, filenames: list[str]) -> list[str]:
        """
        Extracts station codes from a list of filenames.

        Parameters
        ----------
        filenames : list[str]
            A list of file names to extract station codes from.

        Returns
        -------
        list[str]
            A list of extracted station codes.

        """
        station_codes = list()
        for filename in filenames:
            if filename.endswith(".CSV"):
                parts = Path(filename).name.split("_")
                if len(parts) > 1:
                    station_codes.append(parts[3])
        return station_codes

    def __getitem__(self, station_code: str) -> list[str]:
        return self.__stations[station_code]

    def available_stations(self) -> list[str]:
        """
        Returns a list of available station codes.

        Returns
        -------
        list[str]
            A list of available station codes.
        """
        return list(self.__stations.keys())

    def available_date_range(
        self,
        station_code: str,
    ) -> tuple[pd.Timestamp, pd.Timestamp]:
        """
        Returns the available date range for a given station code.

        Parameters
        ----------
        station_code : str
            The station code to get the available date range for.

        Returns
        -------
        tuple[pd.Timestamp, pd.Timestamp]
            A tuple containing the minimum and maximum available dates for the
            station.

        Raises
        ------
        ValueError
            If the station code is not found in the available stations.

        """
        if station_code not in self.__stations:
            msg = f"Station code '{station_code}' not found in available stations."
            raise ValueError(msg)

        files = map(Path, self.__stations[station_code])
        dates_min = []
        dates_max = []

        for file in files:
            parts = file.stem.split("_")
            try:
                dates_min.append(pd.to_datetime(parts[5], dayfirst=True))
                dates_max.append(pd.to_datetime(parts[7], dayfirst=True))
            except (IndexError, ValueError) as e:
                logging.warning(
                    f"Could not parse dates from filename '{file.name}': {e}"
                )

        if not dates_min or not dates_max:
            raise ValueError(
                f"No valid date ranges found for station '{station_code}'."
            )

        return (min(dates_min), max(dates_max))

    def get_column_names(self, station_code: str, year: int) -> list[str]:
        """
        Returns the column names for a given station code.

        Parameters
        ----------
        station_code : str
            The station code to get the column names for.

        Returns
        -------
        list[str]
            A list of column names for the station.

        Raises
        ------
        ValueError
            If the station code is not found in the available stations.

        """
        if station_code not in self.__stations:
            msg = f"Station code '{station_code}' not found in available stations."
            raise ValueError(msg)

        files = map(Path, self.__stations[station_code])

        target_file = next(filter(lambda f: str(year) in f.name, files), None)
        if target_file is None:
            msg = f"No data file found for station '{station_code}' in year {year}."
            raise ValueError(msg)

        url = f"https://portal.inmet.gov.br/uploads/dadoshistoricos/{year}.zip"
        with RemoteZip(url) as rz:
            with rz.open(str(target_file)) as f:
                reader = pycsv.reader(
                    f.read().decode("latin1").splitlines(), delimiter=";"
                )
                for _ in range(8):
                    next(reader)  # Skip the first 8 rows
                return next(reader)  # Return the header row


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

    def distance_to(self, other: InmetStation | GeoCoordinates) -> Distance:
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


def load_inmet_data_list(update: bool) -> InmetDataList:
    """
    Loads the INMET data list from a temporary file or fetches it from the
    INMET website.

    Parameters
    ----------
    update : bool
        Whether to update the data list from the INMET website.

    Returns
    -------
    InmetDataList
        An InmetDataList object containing the data list.

    """
    temp_file = Path("/tmp/inmet_data.obj")
    if not temp_file.exists() or update:
        data_list = InmetDataList()
        with open(temp_file, "wb") as f:
            pickle.dump(data_list, f, pickle.HIGHEST_PROTOCOL)
    else:
        with open(temp_file, "rb") as f:
            data_list = pickle.load(f)
    return data_list


def get_climate_data(
    station: InmetStation,
    start_date: DateType,
    end_date: DateType,
    update_data_list: bool = False,
) -> pd.DataFrame:
    """
    Fetches climate data for a given INMET weather station and date range.

    Parameters
    ----------
    station : InmetStation
        The weather station for which to fetch the data.
    start_date : str
        The start date for the data in 'YYYY-MM-DD' format.
    end_date : str
        The end date for the data in 'YYYY-MM-DD' format.
    update_data_list : bool, optional
        Whether to update the data list from the INMET website. Default is
        False.

    Returns
    -------
    pd.DataFrame
        A pandas DataFrame containing the weather data for the specified date
        range.

    Notes
    -----
    - The output DataFrame has a units attribute that contains the units
      dictionary for each column and can be accessed via `df.attrs["units"]`.

    """
    try:
        data_list = load_inmet_data_list(update_data_list)
    except Exception as e:
        msg = f"Failed to load INMET data list: {e}"
        raise ConnectionError(msg) from e

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

    years = range(dt_start_date.year, dt_end_date.year + 1)

    default_url = httpx.URL("https://portal.inmet.gov.br/uploads/dadoshistoricos/")
    urls = {year: default_url.join(f"{year}.zip") for year in years}

    # Filter files for this station that match the requested years
    file_names = [
        fname
        for fname in data_list[station.station_code]
        if any(str(year) in fname for year in years)
    ]

    MAPPING_COLUMNS = [
        "date",
        "time",
        "precipitation",
        "pressure",
        "pressure_max",
        "pressure_min",
        "radiation",
        "air_temperature",
        "dew_point",
        "air_temperature_max",
        "air_temperature_min",
        "dew_point_max",
        "dew_point_min",
        "relative_humidity",
        "relative_humidity_max",
        "relative_humidity_min",
        "wind_direction",
        "wind_gust",
        "wind_speed",
    ]

    df_list = list()
    for year, file_name in zip(years, file_names):
        with RemoteZip(str(urls[year])) as rz:
            with rz.open(file_name) as f:
                df = (
                    pd.read_csv(
                        f,
                        sep=";",
                        encoding="latin1",
                        skiprows=8,
                        decimal=",",
                        na_values="-9999",
                    )
                    .dropna(axis=1, how="all")
                    .set_axis(MAPPING_COLUMNS, axis=1)
                    .assign(
                        datetime=lambda x: pd.to_datetime(
                            x["date"]
                            .add(" ")
                            .add(x["time"])
                            .str.zfill(4)
                            .str.split(" ")
                            .str[0],
                        ).sub(pd.Timedelta(hours=3)),
                    )
                    .drop(columns=["date", "time"])
                    .pipe(lambda df: df.reindex(columns=["datetime", *df.columns[:-1]]))
                )
        df_list.append(df)

    df = (
        pd.concat(df_list, ignore_index=True)
        .merge(
            pd.DataFrame(
                {"datetime": pd.date_range(dt_start_date, dt_end_date, freq="h")}
            ),
            on="datetime",
            how="right",
        )
        .set_index("datetime")
        .sort_index()
    )

    # Extract units from column names and store in df.units attribute
    units_pattern = re.compile(r"\(([^()]+)\)$")
    original_columns = data_list.get_column_names(station.station_code, years[0])

    # Create units dictionary mapping column names to their units
    units_dict = {}
    for original_col, mapped_col in zip(original_columns, MAPPING_COLUMNS):
        match = units_pattern.search(original_col)
        if match:
            units_dict[mapped_col] = match.group(1)

    df.attrs["units"] = units_dict

    return df


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
    weather_stations : list[InmetStation]
        A list of InmetStation objects representing the weather stations.

    """

    def __init__(self, update: bool = True) -> None:
        """
        Initializes the FindWeatherLocation object and retrieves weather
        station data from the API.

        Parameters
        ----------
        update : bool, optional
            Whether to update the weather station data from the API. Default
            is True.

        """
        self.weather_stations = self.__building_weather_station_list(update)

    def __building_weather_station_list(self, update) -> list[InmetStation]:
        """
        Retrieves weather station data from the API, creates InmetStation
        objects, and returns a list of these objects.
        """
        base_url = httpx.URL("https://apitempo.inmet.gov.br/estacoes/")
        tempfile = Path("/tmp/weather_stations.obj")
        if not tempfile.exists():
            tempfile.touch()
        if update | (not tempfile.exists()):
            auto_weather_stations = httpx.get(base_url.join("T")).json()
            manual_weather_stations = httpx.get(base_url.join("M")).json()
            raw_weather_stations = auto_weather_stations + manual_weather_stations
            weather_stations = []

            print("Looking for all INMET stations. Please wait...")

            # Add InmetStation to weather_stations list.
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
                    "type_of_operation": "Automatica"
                    if station.get("TP_ESTACAO") == "Automatic"
                    else "Traditional",
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

    def find_nearest(
        self,
        location: GeoCoordinates,
        n_nearest: int = 1,
        only_operating: bool = True,
    ) -> list[InmetStation]:
        """
        Finds the nearest weather stations to a specific geographical location.

        Parameters
        ----------
        location : InmetStation
            The geographical location to search for weather stations.
        n_nearest : int, optional
            The number of nearest weather stations to return. Default is 1.
        only_operating : bool, optional
            Whether to only include operating weather stations. Default is True.

        Returns
        -------
        list[InmetStation]
            A list of InmetStation objects representing the nearest weather
            stations.

        """
        if only_operating:
            list_of_weather_stations = list(
                filter(lambda station: station.is_operating, self.weather_stations)
            )
        else:
            list_of_weather_stations = self.weather_stations

        distances = [
            (station, location.distance_to(station.coordinates).distance)
            for station in list_of_weather_stations
        ]
        distances.sort(key=lambda x: x[1])

        return [station for station, _ in distances[:n_nearest]]

    def find_within_radius(
        self,
        location: GeoCoordinates,
        maximum_distance: Distance = Distance(100.0, "km"),
        only_operating: bool = True,
    ) -> list[InmetStation]:
        """
        Find weather stations within a specified maximum distance from a given
        location.

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
        list[InmetStation]
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
