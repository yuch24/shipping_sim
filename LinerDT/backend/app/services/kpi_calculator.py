from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
import threading


@dataclass
class KPISnapshot:
    sim_time: float
    on_time_rate: float
    utilization: float
    carbon_total: float
    avg_delay_hours: float
    ships_in_queue: int


@dataclass
class ShipKPI:
    ship_id: str
    on_time_arrivals: int = 0
    total_arrivals: int = 0
    total_delay_hours: float = 0.0
    total_carbon: float = 0.0
    decision_log: list = field(default_factory=list)


@dataclass
class ReliabilityMetrics:
    on_time_rate: float
    mean_delay: float
    max_delay: float
    delay_variance: float
    service_reliability_index: float
    port_reliability_scores: dict


@dataclass
class CarbonMetrics:
    total_emissions: float
    per_ship_average: float
    per_nautical_mile: float
    operational_emissions: float
    maneuvering_emissions: float
    carbon_intensity: float


@dataclass
class RobustnessMetrics:
    recovery_time: float
    max_queue_length: int
    berth_blocking_probability: float
    schedule_recovery_factor: float
    system_resilience_index: float


class KPICalculator:
    def __init__(self):
        self._ship_kpis: dict[str, ShipKPI] = {}
        self._port_queue_history: list[tuple[float, dict]] = []
        self._snapshots: list[KPISnapshot] = []
        self._delay_history: list[float] = []
        self._max_delay: float = 0.0
        self._delay_variance_sum: float = 0.0

    def register_ship(self, ship_id: str) -> None:
        if ship_id not in self._ship_kpis:
            self._ship_kpis[ship_id] = ShipKPI(ship_id=ship_id)

    def record_arrival(self, ship_id: str, scheduled_time: float, actual_time: float) -> None:
        if ship_id not in self._ship_kpis:
            self.register_ship(ship_id)
        kpi = self._ship_kpis[ship_id]
        kpi.total_arrivals += 1
        delay = max(0.0, actual_time - scheduled_time)
        kpi.total_delay_hours += delay
        if delay <= 4.0:
            kpi.on_time_arrivals += 1
        self._delay_history.append(delay)
        if delay > self._max_delay:
            self._max_delay = delay
        mean_delay = self.get_avg_delay()
        self._delay_variance_sum += (delay - mean_delay) ** 2

    def record_carbon(self, ship_id: str, carbon_amount: float) -> None:
        if ship_id not in self._ship_kpis:
            self.register_ship(ship_id)
        self._ship_kpis[ship_id].total_carbon += carbon_amount

    def record_decision(self, ship_id: str, decision: dict) -> None:
        if ship_id not in self._ship_kpis:
            self.register_ship(ship_id)
        self._ship_kpis[ship_id].decision_log.append(decision)

    def record_port_queue(self, sim_time: float, port_queues: dict[str, int]) -> None:
        self._port_queue_history.append((sim_time, port_queues.copy()))

    def get_on_time_rate(self) -> float:
        total_arrivals = sum(k.total_arrivals for k in self._ship_kpis.values())
        if total_arrivals == 0:
            return 1.0
        on_time_arrivals = sum(k.on_time_arrivals for k in self._ship_kpis.values())
        return on_time_arrivals / total_arrivals

    def get_avg_delay(self) -> float:
        total_arrivals = sum(k.total_arrivals for k in self._ship_kpis.values())
        if total_arrivals == 0:
            return 0.0
        total_delay = sum(k.total_delay_hours for k in self._ship_kpis.values())
        return total_delay / total_arrivals

    def get_total_carbon(self) -> float:
        return sum(k.total_carbon for k in self._ship_kpis.values())

    def get_delay_variance(self) -> float:
        n = len(self._delay_history)
        if n < 2:
            return 0.0
        return self._delay_variance_sum / (n - 1)

    def get_max_delay(self) -> float:
        return self._max_delay

    def get_reliability_metrics(self, port_reliability_scores: dict = None) -> ReliabilityMetrics:
        on_time_rate = self.get_on_time_rate()
        mean_delay = self.get_avg_delay()
        max_delay = self.get_max_delay()
        delay_variance = self.get_delay_variance()
        service_reliability_index = on_time_rate * 100 / (1 + mean_delay / 24)
        return ReliabilityMetrics(
            on_time_rate=round(on_time_rate * 100, 2),
            mean_delay=round(mean_delay, 2),
            max_delay=round(max_delay, 2),
            delay_variance=round(delay_variance, 2),
            service_reliability_index=round(service_reliability_index, 2),
            port_reliability_scores=port_reliability_scores or {},
        )

    def get_carbon_metrics(self, total_nautical_miles: float = 100000) -> CarbonMetrics:
        total = self.get_total_carbon()
        ships_count = len(self._ship_kpis)
        per_ship_avg = total / ships_count if ships_count > 0 else 0
        per_nautical_mile = total / total_nautical_miles if total_nautical_miles > 0 else 0
        operational_emissions = total * 0.6
        maneuvering_emissions = total * 0.4
        carbon_intensity = per_nautical_mile * 1000 if total_nautical_miles > 0 else 0
        return CarbonMetrics(
            total_emissions=round(total, 2),
            per_ship_average=round(per_ship_avg, 2),
            per_nautical_mile=round(per_nautical_mile, 4),
            operational_emissions=round(operational_emissions, 2),
            maneuvering_emissions=round(maneuvering_emissions, 2),
            carbon_intensity=round(carbon_intensity, 2),
        )

    def get_robustness_metrics(self) -> RobustnessMetrics:
        max_queue = 0
        total_blocking_events = 0
        for _, queues in self._port_queue_history:
            for q in queues.values():
                if q > max_queue:
                    max_queue = q
                if q > 5:
                    total_blocking_events += 1
        total_records = len(self._port_queue_history)
        berth_blocking_prob = total_blocking_events / total_records if total_records > 0 else 0
        recovery_time = self._max_delay * 0.5
        schedule_recovery_factor = 1 / (1 + self.get_delay_variance() / 100)
        system_resilience_index = (1 - berth_blocking_prob) * schedule_recovery_factor * 100
        return RobustnessMetrics(
            recovery_time=round(recovery_time, 2),
            max_queue_length=max_queue,
            berth_blocking_probability=round(berth_blocking_prob, 3),
            schedule_recovery_factor=round(schedule_recovery_factor, 3),
            system_resilience_index=round(system_resilience_index, 2),
        )

    def get_utilization(self, port_id: str, total_berths: int, sim_duration_hours: float) -> float:
        relevant_queues = [
            q for _, queues in self._port_queue_history
            for q in [queues.get(port_id, 0)]
        ]
        if not relevant_queues or total_berths == 0:
            return 0.0
        avg_queue = sum(relevant_queues) / len(relevant_queues)
        return min(1.0, (avg_queue + total_berths) / (total_berths * 2))

    def take_snapshot(self, sim_time: float) -> KPISnapshot:
        snapshot = KPISnapshot(
            sim_time=sim_time,
            on_time_rate=self.get_on_time_rate(),
            utilization=0.0,
            carbon_total=self.get_total_carbon(),
            avg_delay_hours=self.get_avg_delay(),
            ships_in_queue=sum(
                q for _, queues in self._port_queue_history[-10:]
                for q in queues.values()
            ) // 10 if self._port_queue_history else 0,
        )
        self._snapshots.append(snapshot)
        return snapshot

    def get_dashboard_data(self, sim_time: float) -> dict:
        return {
            "sim_time": sim_time,
            "on_time_rate": round(self.get_on_time_rate() * 100, 1),
            "avg_delay_hours": round(self.get_avg_delay(), 1),
            "carbon_total": round(self.get_total_carbon(), 1),
            "total_arrivals": sum(k.total_arrivals for k in self._ship_kpis.values()),
            "on_time_arrivals": sum(k.on_time_arrivals for k in self._ship_kpis.values()),
            "ships_tracked": len(self._ship_kpis),
        }

    def get_trend_data(self) -> list[dict]:
        return [
            {
                "time": s.sim_time,
                "on_time_rate": s.on_time_rate * 100,
                "carbon_total": s.carbon_total,
                "avg_delay": s.avg_delay_hours,
            }
            for s in self._snapshots
        ]

    def reset(self) -> None:
        self._ship_kpis.clear()
        self._port_queue_history.clear()
        self._snapshots.clear()


_kpi_lock: threading.Lock = threading.Lock()
_kpi_calculator: Optional[KPICalculator] = None


def get_kpi_calculator() -> KPICalculator:
    global _kpi_calculator
    if _kpi_calculator is None:
        with _kpi_lock:
            if _kpi_calculator is None:
                _kpi_calculator = KPICalculator()
    return _kpi_calculator
