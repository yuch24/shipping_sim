"""
Timetable-driven simulation engine.

Core idea: ships follow a strict timetable (route_schedules.csv).
Positions are computed by distance-proportional time allocation along
pre-defined waypoint paths (route_waypoints.csv).

Each route cycles with period = cycle_days. Ships are launched weekly,
so route with N-week cycle has N ships, each offset by 168 hours.
"""

import csv
import math
import os
import threading
from dataclasses import dataclass, field
from typing import Optional

_DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 0.539957


@dataclass
class PortSchedule:
    port_code: str
    eta_hours: float
    etd_hours: Optional[float]


@dataclass
class TimedWaypoint:
    time_hours: float
    lat: float
    lon: float


@dataclass
class ShipTrajectory:
    ship_id: str
    name: str
    service: str
    week_offset: int
    cycle_hours: float
    waypoints: list[TimedWaypoint]
    schedule: list[PortSchedule]


def _load_port_coords() -> dict[str, tuple[float, float]]:
    result: dict[str, tuple[float, float]] = {}
    filepath = os.path.join(_DATA_DIR, "port_coordinates.csv")
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            port_code = row[0].strip()
            if not port_code:
                continue
            lat = float(row[3])
            lon = float(row[4])
            result[port_code] = (lat, lon)
    return result


def _load_route_schedules() -> dict[str, list[PortSchedule]]:
    result: dict[str, list[PortSchedule]] = {}
    filepath = os.path.join(_DATA_DIR, "route_schedules.csv")
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            route_id = row[0].strip()
            port_code = row[2].strip()
            eta_day = float(row[3])
            etd_str = row[4].strip()
            eta_hours = eta_day * 24
            etd_hours = float(etd_str) * 24 if etd_str else None
            if route_id not in result:
                result[route_id] = []
            result[route_id].append(
                PortSchedule(
                    port_code=port_code,
                    eta_hours=eta_hours,
                    etd_hours=etd_hours,
                )
            )
    return result


def _load_waypoint_segments() -> dict[str, list[tuple[float, float]]]:
    result: dict[str, list[tuple[float, float]]] = {}
    filepath = os.path.join(_DATA_DIR, "route_waypoints.csv")
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            from_port = row[1].strip()
            to_port = row[2].strip()
            lat = float(row[4])
            lon = float(row[5])
            key = f"{from_port}\u2192{to_port}"
            if key not in result:
                result[key] = []
            result[key].append((lat, lon))
    return result


class TimetableEngine:
    def __init__(self):
        self.port_coords = _load_port_coords()
        self.route_schedules = _load_route_schedules()
        self.waypoint_segments = _load_waypoint_segments()
        self._trajectories: dict[str, ShipTrajectory] = {}
        self._build_all()

    def _get_leg_points(
        self, from_port: str, to_port: str
    ) -> list[tuple[float, float]]:
        key = f"{from_port}\u2192{to_port}"
        middle = self.waypoint_segments.get(key)
        if middle is None:
            rev = f"{to_port}\u2192{from_port}"
            raw = self.waypoint_segments.get(rev)
            middle = list(reversed(raw)) if raw else []

        start = self.port_coords.get(from_port, (0.0, 0.0))
        end = self.port_coords.get(to_port, (0.0, 0.0))
        if middle:
            return [start] + middle + [end]
        return [start, end]

    def _timed_leg(
        self,
        from_port: str,
        to_port: str,
        depart_h: float,
        arrive_h: float,
    ) -> list[TimedWaypoint]:
        pts = self._get_leg_points(from_port, to_port)
        if len(pts) <= 1:
            lat, lon = pts[0] if pts else (0, 0)
            return [TimedWaypoint(depart_h, lat, lon)]

        dists: list[float] = []
        total_d = 0.0
        for i in range(len(pts) - 1):
            d = _haversine(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
            dists.append(d)
            total_d += d

        duration = arrive_h - depart_h
        if duration <= 0 or total_d <= 0:
            return [TimedWaypoint(depart_h, pts[0][0], pts[0][1])]

        result = [TimedWaypoint(depart_h, pts[0][0], pts[0][1])]
        acc = 0.0
        for i in range(len(dists)):
            acc += dists[i]
            ratio = acc / total_d
            t = depart_h + ratio * duration
            result.append(TimedWaypoint(t, pts[i + 1][0], pts[i + 1][1]))
        return result

    def _build_cycle_waypoints(self, route_id: str) -> list[TimedWaypoint]:
        sched = self.route_schedules.get(route_id, [])
        if not sched:
            return []

        wps: list[TimedWaypoint] = []
        first = sched[0]
        first_coord = self.port_coords.get(first.port_code, (0.0, 0.0))
        wps.append(TimedWaypoint(first.eta_hours, first_coord[0], first_coord[1]))

        for i in range(len(sched) - 1):
            cur = sched[i]
            nxt = sched[i + 1]
            cur_coord = self.port_coords.get(cur.port_code, (0.0, 0.0))

            if cur.etd_hours is not None:
                wps.append(TimedWaypoint(cur.etd_hours, cur_coord[0], cur_coord[1]))
                leg = self._timed_leg(
                    cur.port_code,
                    nxt.port_code,
                    cur.etd_hours,
                    nxt.eta_hours,
                )
                wps.extend(leg[1:])

        last = sched[-1]
        last_coord = self.port_coords.get(last.port_code, (0.0, 0.0))
        wps.append(TimedWaypoint(last.eta_hours, last_coord[0], last_coord[1]))
        return wps

    def _build_all(self):
        ship_names_by_service: dict[str, list[str]] = {}
        try:
            from .aeu_data import AEU_VESSELS

            for v in AEU_VESSELS:
                svc = v["service"]
                ship_names_by_service.setdefault(svc, []).append(v["name"])
        except Exception:
            pass

        for route_id, sched in self.route_schedules.items():
            base_wps = self._build_cycle_waypoints(route_id)
            if not base_wps:
                continue

            cycle_hours = sched[-1].eta_hours
            cycle_weeks = round(cycle_hours / 168)
            names = ship_names_by_service.get(route_id, [])

            for wk in range(cycle_weeks):
                offset = wk * 168
                name = names[wk] if wk < len(names) else f"{route_id}_ship_{wk + 1}"
                ship_id = f"{route_id}_s{wk + 1:03d}"

                shifted_wps = [
                    TimedWaypoint(
                        time_hours=wp.time_hours + offset,
                        lat=wp.lat,
                        lon=wp.lon,
                    )
                    for wp in base_wps
                ]
                shifted_sched = [
                    PortSchedule(
                        port_code=ps.port_code,
                        eta_hours=ps.eta_hours + offset,
                        etd_hours=(ps.etd_hours + offset)
                        if ps.etd_hours is not None
                        else None,
                    )
                    for ps in sched
                ]

                self._trajectories[ship_id] = ShipTrajectory(
                    ship_id=ship_id,
                    name=name,
                    service=route_id,
                    week_offset=wk,
                    cycle_hours=cycle_hours,
                    waypoints=shifted_wps,
                    schedule=shifted_sched,
                )

    # ── Query API ──────────────────────────────────────────────

    def get_trajectory(self, ship_id: str) -> Optional[ShipTrajectory]:
        return self._trajectories.get(ship_id)

    def get_all_trajectories(self) -> dict[str, ShipTrajectory]:
        return self._trajectories

    def get_ship_position(
        self,
        ship_id: str,
        sim_time_h: float,
    ) -> tuple[float, float, str, str]:
        traj = self._trajectories.get(ship_id)
        if not traj:
            return 0.0, 0.0, "unknown", ""

        offset = traj.week_offset * 168.0
        if sim_time_h < offset:
            port = traj.schedule[0].port_code if traj.schedule else ""
            lat, lon = self.port_coords.get(port, (0, 0))
            return lat, lon, "at_port", port

        t_in_cycle = (sim_time_h - offset) % traj.cycle_hours
        abs_t = offset + t_in_cycle

        for ps in traj.schedule:
            if ps.eta_hours <= abs_t:
                if ps.etd_hours is None or abs_t <= ps.etd_hours:
                    lat, lon = self.port_coords.get(ps.port_code, (0, 0))
                    return lat, lon, "at_port", ps.port_code

        wps = traj.waypoints
        lo, hi = 0, len(wps) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if wps[mid].time_hours < abs_t:
                lo = mid + 1
            else:
                hi = mid

        if lo > 0:
            i = lo - 1
        else:
            return wps[0].lat, wps[0].lon, "sailing", ""

        j = lo
        if j >= len(wps):
            return wps[-1].lat, wps[-1].lon, "at_port", ""

        dt = wps[j].time_hours - wps[i].time_hours
        if dt <= 0:
            return wps[i].lat, wps[i].lon, "sailing", ""

        ratio = (abs_t - wps[i].time_hours) / dt
        lat = wps[i].lat + ratio * (wps[j].lat - wps[i].lat)
        lon = wps[i].lon + ratio * (wps[j].lon - wps[i].lon)
        return lat, lon, "sailing", ""

    def get_all_ship_states(self, sim_time_h: float) -> dict:
        result: dict[str, dict] = {}
        for sid, traj in self._trajectories.items():
            lat, lon, state, port = self.get_ship_position(sid, sim_time_h)

            offset = traj.week_offset * 168.0
            if sim_time_h >= offset:
                t_in_cycle = (sim_time_h - offset) % traj.cycle_hours + offset
            else:
                t_in_cycle = offset

            current_port = port
            next_port = ""
            best_eta = -1.0
            for i, ps in enumerate(traj.schedule):
                if ps.eta_hours <= t_in_cycle and ps.eta_hours >= best_eta:
                    best_eta = ps.eta_hours
                    current_port = ps.port_code
                    next_port = (
                        traj.schedule[i + 1].port_code
                        if i + 1 < len(traj.schedule)
                        else traj.schedule[0].port_code
                    )

            result[sid] = {
                "unique_id": sid,
                "name": traj.name,
                "service": traj.service,
                "state": state,
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "current_port": current_port,
                "next_port": next_port,
            }
        return result

    def to_frontend_json(self, num_cycles: int = 10) -> dict:
        result: dict[str, dict] = {}
        for sid, traj in self._trajectories.items():
            offset = traj.week_offset * 168.0
            first_port = traj.schedule[0].port_code if traj.schedule else ""
            first_lat, first_lon = self.port_coords.get(first_port, (0.0, 0.0))

            pts: list[dict] = []
            pts.append({"t": 0.0, "lat": first_lat, "lon": first_lon})

            for cycle in range(num_cycles):
                cycle_start = offset + cycle * traj.cycle_hours
                for wp in traj.waypoints:
                    abs_t = cycle_start + (wp.time_hours - offset)
                    if abs_t < 0:
                        continue
                    pts.append({
                        "t": round(abs_t, 2),
                        "lat": wp.lat,
                        "lon": wp.lon,
                    })

            sched: list[dict] = []
            for ps in traj.schedule:
                sched.append({
                    "port": ps.port_code,
                    "eta": round(ps.eta_hours, 2),
                    "etd": round(ps.etd_hours, 2) if ps.etd_hours is not None else None,
                })

            result[sid] = {
                "ship_id": sid,
                "name": traj.name,
                "service": traj.service,
                "week_offset": traj.week_offset,
                "cycle_hours": traj.cycle_hours,
                "waypoints": pts,
                "schedule": sched,
            }
        return result

    def get_port_states(self, sim_time_h: float) -> dict:
        result: dict[str, dict] = {}
        for port_code, (lat, lon) in self.port_coords.items():
            ships_at_port = 0
            for sid, traj in self._trajectories.items():
                _, _, state, p = self.get_ship_position(sid, sim_time_h)
                if state == "at_port" and p == port_code:
                    ships_at_port += 1
            result[port_code] = {
                "unique_id": port_code,
                "name": port_code,
                "lat": lat,
                "lon": lon,
                "queue_length": max(0, ships_at_port - 30),
                "berth_count": 30,
                "available_berths": max(0, 30 - ships_at_port),
                "ships_at_port": ships_at_port,
            }
        return result


_engine_lock = threading.Lock()
_engine: Optional[TimetableEngine] = None


def get_timetable_engine() -> TimetableEngine:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = TimetableEngine()
    return _engine
