"""
Example usage of the reorganized INMET stations package.
"""

import logging
from typing import Optional

from iws import GeoCoordinates, InmetStations, get_climate_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def find_and_display_stations(
    coordinates: GeoCoordinates,
    n_stations: int = 3,
) -> list:
    """Find and display nearest weather stations."""
    try:
        stations = InmetStations(update=True)
        nearest_stations = stations.find_nearest(
            coordinates,
            n_nearest=n_stations,
            only_automatic=True,
        )

        logger.info(f"Found {len(nearest_stations)} nearest stations")
        print("Nearest weather stations:")
        for i, station in enumerate(nearest_stations, 1):
            distance = station.distance_to(coordinates)
            print(f"{i}. {station.name} ({station.station_code})")
            print(f"   Distance: {distance:.2f} km\n")

        return nearest_stations

    except Exception as e:
        logger.error(f"Error finding stations: {e}")
        return []


def get_and_display_climate_data(
    station,
    start_date: str,
    end_date: str,
) -> Optional[object]:
    """Retrieve and display climate data for a station."""
    try:
        logger.info(f"Retrieving climate data for {station.name}...")

        climate_data = get_climate_data(
            station=station,
            start_date=start_date,
            end_date=end_date,
            update_data_list=False,
        )

        # Display data summary
        non_empty_data = climate_data.dropna(axis=0, how="all")
        print(
            f"Retrieved {len(climate_data)} total records ({len(non_empty_data)} non-empty)"
        )
        print(f"Date range: {start_date} to {end_date}")
        print(f"Available columns: {', '.join(climate_data.columns)}")

        # Display units if available
        units = climate_data.attrs.get("units", {})
        if units:
            print(f"Units: {units}")

        # Show sample data
        print("\nSample data (first 10 non-empty rows):")
        print(non_empty_data.head(10))

        return climate_data

    except Exception as e:
        logger.error(f"Error retrieving climate data: {e}")
        return None


def main():
    """Main function demonstrating the INMET weather data workflow."""
    # Configuration
    SAO_PAULO_COORDS = GeoCoordinates(-23.5505, -46.6333)
    START_DATE = "2023-01-01"
    END_DATE = "2023-01-31"
    N_STATIONS = 3

    logger.info("Starting INMET weather data example")

    # Find nearest stations
    nearest_stations = find_and_display_stations(SAO_PAULO_COORDS, N_STATIONS)

    if not nearest_stations:
        logger.warning("No weather stations found. Exiting.")
        return

    # Get climate data for the nearest station
    selected_station = nearest_stations[0]
    logger.info(f"Selected station: {selected_station.name}")

    climate_data = get_and_display_climate_data(selected_station, START_DATE, END_DATE)

    if climate_data is not None:
        logger.info("Climate data retrieved successfully")
    else:
        logger.warning("Failed to retrieve climate data")


if __name__ == "__main__":
    main()
