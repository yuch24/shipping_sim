from math import radians, cos, sin, asin, sqrt, degrees, atan2, isclose


EARTH_RADIUS_NM = 3440.065


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))

    distance = EARTH_RADIUS_NM * c
    return distance


def great_circle_interpolate(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    ratio: float
) -> tuple[float, float]:
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    d = 2 * asin(sqrt(
        sin((lat2 - lat1) / 2) ** 2 +
        cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    ))

    if abs(d) < 1e-12:
        return degrees(lat1), degrees(lon1)

    a = sin((1 - ratio) * d) / sin(d)
    b = sin(ratio * d) / sin(d)

    x = a * cos(lat1) * cos(lon1) + b * cos(lat2) * cos(lon2)
    y = a * cos(lat1) * sin(lon1) + b * cos(lat2) * sin(lon2)
    z = a * sin(lat1) + b * sin(lat2)

    lat = degrees(atan2(z, sqrt(x * x + y * y)))
    lon = degrees(atan2(y, x))

    return lat, lon


def interpolate_position(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    start_time: float,
    end_time: float,
    current_time: float,
):
    if current_time <= start_time:
        return start_lat, start_lon
    if current_time >= end_time:
        return end_lat, end_lon

    ratio = (current_time - start_time) / (end_time - start_time)

    lat, lon = great_circle_interpolate(
        start_lat, start_lon,
        end_lat, end_lon,
        ratio
    )

    return lat, lon


def calculate_sailing_time(distance_nm: float, speed_knots: float) -> float:
    if speed_knots <= 0:
        return float('inf')
    return distance_nm / speed_knots


def _daily_fuel_at_speed(
    speed_knots: float,
    base_daily_consumption: float,
    design_speed: float = 22.0,
    low_speed_threshold: float = 0.5,
    low_speed_penalty: float = 1.3,
) -> float:
    speed_ratio = speed_knots / design_speed if design_speed > 0 else 1.0
    daily_fuel = base_daily_consumption * (speed_ratio ** 3)
    if speed_ratio < low_speed_threshold:
        daily_fuel *= low_speed_penalty
    return daily_fuel


def calculate_fuel_consumption(
    distance_nm: float,
    speed_knots: float,
    base_daily_consumption: float,
    design_speed: float = 22.0,
    low_speed_threshold: float = 0.5,
    low_speed_penalty: float = 1.3,
) -> float:
    if speed_knots <= 0:
        return 0.0
    daily_fuel = _daily_fuel_at_speed(
        speed_knots, base_daily_consumption,
        design_speed, low_speed_threshold, low_speed_penalty,
    )
    sailing_days = distance_nm / (speed_knots * 24)
    return daily_fuel * sailing_days


def calculate_hourly_fuel_consumption(
    speed_knots: float,
    base_daily_consumption: float,
    design_speed: float = 22.0,
    low_speed_threshold: float = 0.5,
    low_speed_penalty: float = 1.3,
) -> float:
    if speed_knots <= 0:
        return 0.0
    return _daily_fuel_at_speed(
        speed_knots, base_daily_consumption,
        design_speed, low_speed_threshold, low_speed_penalty,
    ) / 24.0


LAND_MASSES = [
    {"name": "Europe", "lat_min": 35, "lat_max": 71, "lon_min": -10, "lon_max": 40},
    {"name": "Africa", "lat_min": -35, "lat_max": 37, "lon_min": -18, "lon_max": 51},
    {"name": "Asia", "lat_min": 5, "lat_max": 77, "lon_min": 40, "lon_max": 180},
    {"name": "North_America", "lat_min": 7, "lat_max": 83, "lon_min": -170, "lon_max": -50},
    {"name": "South_America", "lat_min": -56, "lat_max": 13, "lon_min": -82, "lon_max": -34},
    {"name": "Australia", "lat_min": -47, "lat_max": -10, "lon_min": 112, "lon_max": 155},
    {"name": "India", "lat_min": 6, "lat_max": 35, "lon_min": 68, "lon_max": 97},
    {"name": "Japan", "lat_min": 24, "lat_max": 46, "lon_min": 123, "lon_max": 146},
    {"name": "Indonesia", "lat_min": -11, "lat_max": 6, "lon_min": 95, "lon_max": 141},
    {"name": "Middle_East", "lat_min": 12, "lat_max": 35, "lon_min": 35, "lon_max": 63},
    {"name": "Southeast_Asia", "lat_min": -10, "lat_max": 28, "lon_min": 90, "lon_max": 130},
]


def _lon_normalize(lon: float) -> float:
    while lon > 180:
        lon -= 360
    while lon < -180:
        lon += 360
    return lon


def is_point_on_land(lat: float, lon: float) -> bool:
    lon = _lon_normalize(lon)
    for mass in LAND_MASSES:
        if (mass["lat_min"] <= lat <= mass["lat_max"] and
            mass["lon_min"] <= lon <= mass["lon_max"]):
            return True
    return False


def check_segment_crosses_land(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    num_samples: int = 20
) -> bool:
    lon1 = _lon_normalize(lon1)
    lon2 = _lon_normalize(lon2)

    for i in range(num_samples + 1):
        ratio = i / num_samples
        lat, lon = great_circle_interpolate(lat1, lon1, lat2, lon2, ratio)
        lon = _lon_normalize(lon)
        if is_point_on_land(lat, lon):
            return True
    return False


def find_waypoints_avoiding_land(
    start_lat: float, start_lon: float,
    end_lat: float, end_lon: float
) -> list[tuple[float, float]]:
    waypoints = []

    if check_segment_crosses_land(start_lat, start_lon, end_lat, end_lon):
        mid_lat = (start_lat + end_lat) / 2
        mid_lon = (start_lon + end_lon) / 2

        if mid_lat > 0:
            detour_lat = mid_lat + 15
        else:
            detour_lat = mid_lat - 15

        waypoints.append((detour_lat, mid_lon))

        alt_end_lat = (detour_lat + end_lat) / 2
        alt_end_lon = mid_lon

        if not check_segment_crosses_land(detour_lat, mid_lon, alt_end_lat, alt_end_lon):
            waypoints.append((alt_end_lat, alt_end_lon))
        if not check_segment_crosses_land(alt_end_lat, alt_end_lon, end_lat, end_lon):
            waypoints.append((end_lat, end_lon))

    return waypoints


def calculate_route_with_waypoints(
    start_lat: float, start_lon: float,
    end_lat: float, end_lon: float
) -> tuple[list[tuple[float, float]], float]:
    waypoints = find_waypoints_avoiding_land(start_lat, start_lon, end_lat, end_lon)

    all_points = [(start_lat, start_lon)] + waypoints + [(end_lat, end_lon)]

    total_distance = 0.0
    for i in range(len(all_points) - 1):
        p1_lat, p1_lon = all_points[i]
        p2_lat, p2_lon = all_points[i + 1]
        total_distance += haversine(p1_lat, p1_lon, p2_lat, p2_lon)

    return all_points, total_distance
