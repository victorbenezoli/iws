<p align="center">
  <img src="https://raw.githubusercontent.com/victorbenezoli/iws/main/logo-horizontal.png" alt="IWS Logo" width="400"/>
</p>

<h1 align="center">IWS - Inmet Weather Stations</h1>

<p align="center">
  Python package for processing and analyzing data from INMET weather stations.
</p>

<p align="center">
  <!-- Inline badges -->
  <img src="https://img.shields.io/badge/python-3.12%2B-blue" alt="Python 3.12+"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License: MIT"/>
  <img src="https://img.shields.io/badge/status-active-success" alt="Status: Active"/>
  <img src="https://img.shields.io/badge/docs-available-blueviolet" alt="Docs: Available"/>
</p>

---

## 📦 Installation

Install the package using pip:

```bash
pip install iws
```

---

## 🚀 Basic Usage

```python
from iws import InmetStations, get_climate_data, GeoCoordinates, Distance

stations = InmetStations()

# List available stations
print(stations.list())

# Retrieve data from a specific station
station = stations["A001"]  # Replace "A001" with the desired station code
print(station)
data = get_climate_data(station=station, start_date="2023-01-01", end_date="2023-12-31")
print(data.head())

# Find the three nearest operating stations to given coordinates
coords = GeoCoordinates(latitude=-23.55052, longitude=-46.633308, n_nearest=3, only_operating=True)
nearest_stations = stations.find_nearest(coords)
print(nearest_stations)

# Find the stations around given coordinates within a 50 km radius
nearby_stations = stations.find_around(coords, maximum_distance=Distance(50, "km"))
print(nearby_stations)
```

---

## 🌦️ Features

- 📊 Download and process historical data from INMET
- 🌍 Support for multiple weather stations
- ⚡ Optimized functions for analysis with pandas and numpy
- 📈 Ready for integration with notebooks and dashboards

---

## 📚 Documentation

- **[API Reference](https://github.com/victorbenezoli/iws/wiki/API-Reference)** - Complete API documentation
- **[Project Wiki](https://github.com/victorbenezoli/iws/wiki)** - General information and guides

---

## 🤝 Contributing

Contributions are welcome!
1. Fork the repository
2. Create a branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Open a Pull Request

Please ensure the branch name follows the patterns:
- `feature/your-feature-name` for new features
- `bugfix/your-bugfix-name` for bug fixes
- `hotfix/your-hotfix-name` for urgent fixes
- `docs/your-docs-update` for documentation updates
- `improvement/your-improvement-name` for code improvements

---

## 📜 License

Distributed under the MIT License.
See the `LICENSE` file for more information.
