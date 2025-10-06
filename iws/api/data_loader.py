"""
Data loading utilities for INMET data.
"""

import csv as pycsv
import logging
import pickle
from collections import defaultdict
from io import BytesIO
from pathlib import Path
from typing import List
from zipfile import ZipFile

import httpx
import pandas as pd
from remotezip import RemoteZip


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
        year : int
            The year to get column names for.

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


def load_inmet_data_list(update: bool = False) -> InmetDataList:
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


def filter_station_files(
    data_list: InmetDataList, station_code: str, years: range
) -> List[str]:
    """
    Filters files for a specific station matching the requested years.

    Parameters
    ----------
    data_list : InmetDataList
        The data list object containing station information.
    station_code : str
        The station code to filter files for.
    years : range
        Range of years to match.

    Returns
    -------
    List[str]
        List of filtered file names.
    """
    return [
        fname
        for fname in data_list[station_code]
        if any(str(year) in fname for year in years)
    ]
