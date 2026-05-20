import csv
import os

_DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_route_waypoints() -> dict[str, list[tuple[float, float]]]:
    result: dict[str, list[tuple[float, float]]] = {}
    filepath = os.path.join(_DATA_DIR, "route_waypoints.csv")
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            from_port = row[1].strip()
            to_port = row[2].strip()
            lat = float(row[4])
            lon = float(row[5])
            key = f"{from_port}→{to_port}"
            if key not in result:
                result[key] = []
            result[key].append((lat, lon))
    return result


WAYPOINT_SEGMENTS: dict[str, list[tuple[float, float]]] = _load_route_waypoints()


def get_waypoints(from_port: str, to_port: str) -> list[tuple[float, float]]:
    key = f"{from_port}→{to_port}"
    if key in WAYPOINT_SEGMENTS:
        return WAYPOINT_SEGMENTS[key]
    reverse_key = f"{to_port}→{from_port}"
    if reverse_key in WAYPOINT_SEGMENTS:
        original = WAYPOINT_SEGMENTS[reverse_key]
        return list(reversed(original))
    return []
