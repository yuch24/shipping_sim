from typing import Optional
from dataclasses import dataclass, field
import threading

from app.services.navigation import (
    check_segment_crosses_land,
    great_circle_interpolate,
    haversine,
)


@dataclass
class SailingSegment:
    ship_id: str
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    start_time: float
    end_time: float
    waypoints: list[tuple[float, float]] = field(default_factory=list)


class VisualizationSync:
    def __init__(self):
        self._segments: dict[str, list[SailingSegment]] = {}
        self._current_segment: dict[str, SailingSegment] = {}

    def register_sailing(
        self,
        ship_id: str,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        start_time: float,
        end_time: float,
        waypoints: list[tuple[float, float]] = None,
    ) -> None:
        if waypoints is None:
            waypoints = []
            if check_segment_crosses_land(start_lat, start_lon, end_lat, end_lon):
                waypoints = self._find_safe_waypoints(
                    start_lat, start_lon, end_lat, end_lon
                )

        segment = SailingSegment(
            ship_id=ship_id,
            start_lat=start_lat,
            start_lon=start_lon,
            end_lat=end_lat,
            end_lon=end_lon,
            start_time=start_time,
            end_time=end_time,
            waypoints=waypoints,
        )
        if ship_id not in self._segments:
            self._segments[ship_id] = []
        self._segments[ship_id].append(segment)
        self._current_segment[ship_id] = segment

    def _find_safe_waypoints(
        self, start_lat: float, start_lon: float, end_lat: float, end_lon: float
    ) -> list[tuple[float, float]]:
        waypoints = []

        mid_lat = (start_lat + end_lat) / 2
        mid_lon = (start_lon + end_lon) / 2

        if mid_lon > 0:
            detour_lon = mid_lon + 25
        else:
            detour_lon = mid_lon - 25

        test_lat = mid_lat + 10 if mid_lat > 20 else mid_lat - 10

        if not check_segment_crosses_land(start_lat, start_lon, test_lat, detour_lon):
            waypoints.append((test_lat, detour_lon))
            step_lat = (test_lat + end_lat) / 2
            step_lon = (detour_lon + end_lon) / 2
            if not check_segment_crosses_land(test_lat, detour_lon, step_lat, step_lon):
                waypoints.append((step_lat, step_lon))
                if not check_segment_crosses_land(step_lat, step_lon, end_lat, end_lon):
                    waypoints.append((end_lat, end_lon))
        else:
            if mid_lat > 0:
                test_lat = mid_lat - 10
            else:
                test_lat = mid_lat + 10
            if not check_segment_crosses_land(
                start_lat, start_lon, test_lat, detour_lon
            ):
                waypoints.append((test_lat, detour_lon))
                step_lat = (test_lat + end_lat) / 2
                step_lon = (detour_lon + end_lon) / 2
                if not check_segment_crosses_land(
                    test_lat, detour_lon, step_lat, step_lon
                ):
                    waypoints.append((step_lat, step_lon))
                    if not check_segment_crosses_land(
                        step_lat, step_lon, end_lat, end_lon
                    ):
                        waypoints.append((end_lat, end_lon))

        return waypoints

    def get_interpolated_position(
        self, ship_id: str, current_time: float
    ) -> tuple[Optional[float], Optional[float], Optional[str]]:
        segment = self._current_segment.get(ship_id)
        if segment is None:
            return None, None, None

        if current_time <= segment.start_time:
            return segment.start_lat, segment.start_lon, "START"
        if current_time >= segment.end_time:
            return segment.end_lat, segment.end_lon, "END"

        if not segment.waypoints:
            ratio = (current_time - segment.start_time) / (
                segment.end_time - segment.start_time
            )
            lat, lon = great_circle_interpolate(
                segment.start_lat,
                segment.start_lon,
                segment.end_lat,
                segment.end_lon,
                ratio,
            )
            return lat, lon, "SAILING"

        all_points = (
            [(segment.start_lat, segment.start_lon)]
            + segment.waypoints
            + [(segment.end_lat, segment.end_lon)]
        )
        segment_distances = []
        total_distance = 0.0
        for i in range(len(all_points) - 1):
            p1_lat, p1_lon = all_points[i]
            p2_lat, p2_lon = all_points[i + 1]
            d = haversine(p1_lat, p1_lon, p2_lat, p2_lon)
            segment_distances.append(d)
            total_distance += d

        elapsed = current_time - segment.start_time
        total_time = segment.end_time - segment.start_time
        distance_traveled = (elapsed / total_time) * total_distance

        accumulated_distance = 0.0
        for i, d in enumerate(segment_distances):
            if accumulated_distance + d >= distance_traveled:
                segment_start = all_points[i]
                segment_end = all_points[i + 1]
                segment_ratio = (distance_traveled - accumulated_distance) / d
                lat, lon = great_circle_interpolate(
                    segment_start[0],
                    segment_start[1],
                    segment_end[0],
                    segment_end[1],
                    segment_ratio,
                )
                return lat, lon, "SAILING"
            accumulated_distance += d

        return segment.end_lat, segment.end_lon, "END"

    def get_all_positions(self, current_time: float) -> dict[str, dict]:
        positions = {}
        for ship_id, segment in self._current_segment.items():
            lat, lon, status = self.get_interpolated_position(ship_id, current_time)
            if lat is not None:
                positions[ship_id] = {
                    "lat": lat,
                    "lon": lon,
                    "status": status,
                    "progress": self._calculate_progress(segment, current_time),
                }
        return positions

    def _calculate_progress(
        self, segment: SailingSegment, current_time: float
    ) -> float:
        if current_time <= segment.start_time:
            return 0.0
        if current_time >= segment.end_time:
            return 1.0
        return (current_time - segment.start_time) / (
            segment.end_time - segment.start_time
        )

    def clear(self) -> None:
        self._segments.clear()
        self._current_segment.clear()

    def get_ship_segments(self, ship_id: str) -> list[SailingSegment]:
        return self._segments.get(ship_id, [])


_viz_sync_lock: threading.Lock = threading.Lock()
_viz_sync: Optional[VisualizationSync] = None


def get_visualization_sync() -> VisualizationSync:
    global _viz_sync
    if _viz_sync is None:
        with _viz_sync_lock:
            if _viz_sync is None:
                _viz_sync = VisualizationSync()
    return _viz_sync
