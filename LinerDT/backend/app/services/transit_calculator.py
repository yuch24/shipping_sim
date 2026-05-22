import csv
import os
from typing import Dict, Optional, List, Tuple


class TransitCalculator:
    def __init__(self, csv_path: str):
        self._ports: Dict[str, List[Tuple[str, float, float]]] = {}
        self._eta_map: Dict[str, Dict[str, float]] = {}
        self._etd_map: Dict[str, Dict[str, float]] = {}
        self._load(csv_path)

    def _load(self, path: str):
        with open(path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                rid = row["RouteID"].strip()
                port = row["Port"].strip()
                eta = float(row["ETA_day"]) * 24
                etd_raw = (row.get("ETD_day") or "").strip()
                etd = float(etd_raw) * 24 if etd_raw else eta
                if rid not in self._ports:
                    self._ports[rid] = []
                    self._eta_map[rid] = {}
                    self._etd_map[rid] = {}
                self._ports[rid].append((port, eta, etd))
                self._eta_map[rid][port] = eta
                self._etd_map[rid][port] = etd

    def get_transit_hours(self, route: str, origin: str, dest: str) -> Optional[float]:
        if route not in self._ports:
            return None
        seq = self._ports[route]
        n = len(seq)
        for i in range(n):
            if seq[i][0] == origin:
                origin_etd = seq[i][2]  # ETD of this occurrence
                for j in range(i + 1, i + n):
                    if seq[j % n][0] == dest:
                        dest_eta = seq[j % n][1]  # ETA of dest occurrence
                        if j < n:
                            return dest_eta - origin_etd
                        else:
                            return (seq[-1][1] - origin_etd) + dest_eta
        return None

    def get_routes(self) -> List[str]:
        return list(self._ports.keys())


_TC_INSTANCE: Optional[TransitCalculator] = None


def get_transit_calculator() -> TransitCalculator:
    global _TC_INSTANCE
    if _TC_INSTANCE is None:
        csv_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "route_schedules.csv"
        )
        _TC_INSTANCE = TransitCalculator(csv_path)
    return _TC_INSTANCE
