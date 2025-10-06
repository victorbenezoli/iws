"""
Example usage of the reorganized INMET stations package.
"""

from iws import GeoCoordinates, InmetStations, get_climate_data


def main():
    # Create coordinates for a location (example: São Paulo)
    sao_paulo = GeoCoordinates(-23.5505, -46.6333)

    # Find weather stations
    stations = InmetStations(update=True)  # Set to True to update from API

    # Find nearest stations
    nearest_stations = stations.find_nearest(
        sao_paulo,
        n_nearest=3,
        only_automatic=True,
    )

    print("Nearest stations to São Paulo:")
    for station in nearest_stations:
        print(f"  {station.name} - {station.station_code}")
        print(f"    Distance: {station.distance_to(sao_paulo)}")
        print()

    # Get climate data for the nearest station
    if nearest_stations:
        station = nearest_stations[0]
        print(f"Getting climate data for {station.name}...")

        try:
            climate_data = get_climate_data(
                station=station,
                start_date="2023-01-01",
                end_date="2023-01-31",
                update_data_list=False,
            )

            print(f"Retrieved {len(climate_data)} records")
            print("Columns:", list(climate_data.columns))
            print("Units:", climate_data.attrs.get("units", {}))
            print(climate_data.dropna(axis=0, how="all").head(50))

        except Exception as e:
            print(f"Error getting climate data: {e}")


if __name__ == "__main__":
    main()
