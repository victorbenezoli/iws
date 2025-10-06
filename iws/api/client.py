"""
INMET API client for downloading data.
"""

from typing import Dict

import httpx


class InmetAPIClient:
    """
    Client for interacting with INMET API and data sources.
    """

    BASE_URL = "https://portal.inmet.gov.br/uploads/dadoshistoricos/"
    STATIONS_URL = "https://apitempo.inmet.gov.br/estacoes/"

    @classmethod
    def build_download_urls(cls, years: range) -> Dict[int, httpx.URL]:
        """
        Builds download URLs for the specified years.

        Parameters
        ----------
        years : range
            Range of years to build URLs for.

        Returns
        -------
        Dict[int, httpx.URL]
            Dictionary mapping years to their download URLs.
        """
        default_url = httpx.URL(cls.BASE_URL)
        return {year: default_url.join(f"{year}.zip") for year in years}

    @classmethod
    def get_stations_data(cls, station_type: str = "T") -> list[dict]:
        """
        Fetches station data from INMET API.

        Parameters
        ----------
        station_type : str
            Type of stations to fetch. "T" for automatic, "M" for manual.

        Returns
        -------
        list[dict]
            List of station data dictionaries.
        """
        base_url = httpx.URL(cls.STATIONS_URL)
        response = httpx.get(base_url.join(station_type))
        return response.json()
