"""
Climate data processing and retrieval functionality.
"""

import re
from typing import Dict

import pandas as pd
from remotezip import RemoteZip

from ..api import InmetAPIClient, filter_station_files, load_inmet_data_list
from ..common.types import DateType
from ..models import InmetStation
from .validators import validate_date_range


class ClimateDataProcessor:
    """
    Processes climate data from INMET sources.
    """

    COLUMN_NAMES = [
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

    @classmethod
    def read_csv_data(cls, file_obj) -> pd.DataFrame:
        """
        Reads and processes CSV data from a file object.

        Parameters
        ----------
        file_obj
            File object to read from.

        Returns
        -------
        pd.DataFrame
            Processed DataFrame with standardized columns.
        """
        return (
            pd.read_csv(
                file_obj,
                sep=";",
                encoding="latin1",
                skiprows=8,
                decimal=",",
                na_values="-9999",
            )
            .dropna(axis=1, how="all")
            .set_axis(cls.COLUMN_NAMES, axis=1)
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

    @classmethod
    def extract_units(cls, data_list, station_code: str, year: int) -> Dict[str, str]:
        """
        Extracts units information from column names.

        Parameters
        ----------
        data_list
            The data list object.
        station_code : str
            The station code.
        year : int
            The year to extract units for.

        Returns
        -------
        Dict[str, str]
            Dictionary mapping column names to their units.
        """
        units_pattern = re.compile(r"\(([^()]+)\)$")
        original_columns = data_list.get_column_names(station_code, year)

        # Create units dictionary mapping column names to their units
        units_dict = {}
        for original_col, mapped_col in zip(original_columns, cls.COLUMN_NAMES):
            match = units_pattern.search(original_col)
            if match:
                units_dict[mapped_col] = match.group(1)

        return units_dict


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
    start_date : DateType
        The start date for the data.
    end_date : DateType
        The end date for the data.
    update_data_list : bool, optional
        Whether to update the data list from the INMET website.

    Returns
    -------
    pd.DataFrame
        A pandas DataFrame containing the weather data.

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

    if station.type_of_operation != "Automatic":
        msg = (
            f"Downloading data is only supported for automatic stations. "
            f"Station '{station.station_code}' is of type '{station.type_of_operation}'."
        )
        raise ValueError(msg)

    # Validação de datas
    dt_start_date, dt_end_date = validate_date_range(start_date, end_date)

    # Configurar URLs e anos
    years = range(dt_start_date.year, dt_end_date.year + 1)
    urls = InmetAPIClient.build_download_urls(years)

    # Filtrar arquivos da estação
    file_names = filter_station_files(data_list, station.station_code, years)

    # Processar dados de cada ano
    df_list = []
    processor = ClimateDataProcessor()

    for year, file_name in zip(years, file_names):
        with RemoteZip(str(urls[year])) as rz:
            with rz.open(file_name) as f:
                df = processor.read_csv_data(f)
                df_list.append(df)

    # Concatenar e alinhar com série temporal completa
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

    # Adicionar informações de unidades
    units = processor.extract_units(data_list, station.station_code, years[0])
    df.attrs["units"] = units

    return df
