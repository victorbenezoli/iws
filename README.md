<<<<<<< HEAD
<<<<<<< HEAD
# iws
Python package for processing and analyzing data from INMET weather stations.
=======
=======
>>>>>>> 5d87b83 (chore: update project metadata and dependencies)
<p align="center">
  <img src="logo-horizontal.png" alt="IWS Logo" width="400"/>
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
from iws import InmetStations

stations = InmetStations()

# List available stations
print(stations.list())

# Retrieve data from a specific station
data = stations.get("A001")
print(data.head())
```

---

## 🌦️ Features

- 📊 Download and process historical data from INMET
- 🌍 Support for multiple weather stations
- ⚡ Optimized functions for analysis with pandas and numpy
- 📈 Ready for integration with notebooks and dashboards

---

## 📚 Documentation

Full documentation is available at the [Project Wiki](https://github.com/your-username/iws/wiki).

---

## 🤝 Contributing

Contributions are welcome!
1. Fork the repository
2. Create a branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Open a Pull Request

---

## 📜 License

Distributed under the MIT License.
See the `LICENSE` file for more information.
<<<<<<< HEAD
>>>>>>> 83b2502 (chore: update project metadata and dependencies)
=======
>>>>>>> 5d87b83 (chore: update project metadata and dependencies)
