from abc import ABC, abstractmethod
from math import radians, sin, cos, sqrt, atan2

class Coordinates(ABC):
    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon

    @abstractmethod
    def distance(self, other):
        pass

class HaversineCoordinates(Coordinates):
    def distance(self, other):
        # Convert latitude and longitude from degrees to radians
        lat1, lon1 = radians(self.lat), radians(self.lon)
        lat2, lon2 = radians(other.lat), radians(other.lon)

        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        r = 6371  # Radius of Earth in kilometers
        return r * c