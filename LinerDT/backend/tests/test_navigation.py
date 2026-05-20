import pytest
from app.services.navigation import haversine, interpolate_position, calculate_sailing_time


class TestHaversine:
    def test_shanghai_to_ningbo(self):
        shanghai = (31.2304, 121.4737)
        ningbo = (29.8683, 121.544)
        distance = haversine(*shanghai, *ningbo)
        assert 70 < distance < 90

    def test_same_location(self):
        location = (31.2304, 121.4737)
        distance = haversine(*location, *location)
        assert distance == 0.0

    def test_antipodal(self):
        point1 = (0.0, 0.0)
        point2 = (0.0, 180.0)
        distance = haversine(*point1, *point2)
        assert 10000 < distance < 12000


class TestInterpolatePosition:
    def test_start_position(self):
        lat, lon = interpolate_position(0.0, 0.0, 10.0, 10.0, 0.0, 100.0, 0.0)
        assert lat == 0.0
        assert lon == 0.0

    def test_end_position(self):
        lat, lon = interpolate_position(0.0, 0.0, 10.0, 10.0, 0.0, 100.0, 100.0)
        assert lat == 10.0
        assert lon == 10.0

    def test_middle_position(self):
        lat, lon = interpolate_position(0.0, 0.0, 10.0, 10.0, 0.0, 100.0, 50.0)
        assert abs(lat - 5.0) < 0.1
        assert abs(lon - 5.0) < 0.1

    def test_quarter_position(self):
        lat, lon = interpolate_position(0.0, 0.0, 10.0, 10.0, 0.0, 100.0, 25.0)
        assert abs(lat - 2.5) < 0.1
        assert abs(lon - 2.5) < 0.1


class TestSailingTime:
    def test_basic_calculation(self):
        time = calculate_sailing_time(360.0, 15.0)
        assert time == 24.0

    def test_zero_speed(self):
        time = calculate_sailing_time(100.0, 0.0)
        assert time == float('inf')

    def test_negative_speed(self):
        time = calculate_sailing_time(100.0, -5.0)
        assert time == float('inf')
