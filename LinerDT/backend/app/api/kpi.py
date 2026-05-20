from fastapi import APIRouter
from pydantic import BaseModel

from ..scheduler.scheduler import get_model, ShipAgent
from ..services.kpi_calculator import get_kpi_calculator

router = APIRouter()


class KPIData(BaseModel):
    sim_time: float
    on_time_rate: float
    avg_delay_hours: float
    carbon_total: float
    total_arrivals: int
    on_time_arrivals: int
    ships_in_queue: int


class PortKPI(BaseModel):
    port_id: str
    name: str
    queue_length: int
    available_berths: int
    utilization: float


class ShipKPI(BaseModel):
    ship_id: str
    name: str
    state: str
    cumulative_delay: float
    co2_emissions: float


@router.get("/kpi/dashboard")
def get_dashboard_kpi():
    model = get_model()
    kpi_calc = get_kpi_calculator()

    ships_in_queue = sum(
        len(p.waiting_queue) for p in model._ports.values()
    )

    return {
        "sim_time": model.current_time,
        "on_time_rate": round(kpi_calc.get_on_time_rate() * 100, 1),
        "avg_delay_hours": round(kpi_calc.get_avg_delay(), 1),
        "carbon_total": round(kpi_calc.get_total_carbon(), 1),
        "total_arrivals": sum(k.total_arrivals for k in kpi_calc._ship_kpis.values()),
        "on_time_arrivals": sum(k.on_time_arrivals for k in kpi_calc._ship_kpis.values()),
        "ships_in_queue": ships_in_queue,
    }


@router.get("/kpi/ports")
def get_port_kpi():
    model = get_model()
    port_kpis = []

    for port_id, port in model._ports.items():
        total_berths = port.berth_count
        available = port.available_berths
        occupied = total_berths - available
        queue_len = len(port.waiting_queue)
        utilization = (occupied + queue_len) / (total_berths * 2) if total_berths > 0 else 0

        port_kpis.append({
            "port_id": port_id,
            "name": port.name,
            "queue_length": queue_len,
            "available_berths": available,
            "occupied_berths": occupied,
            "utilization": round(min(1.0, utilization) * 100, 1),
        })

    return {"ports": port_kpis}


@router.get("/kpi/ships")
def get_ship_kpi():
    model = get_model()
    ship_kpis = []

    for ship_id, agent in model._agents.items():
        if isinstance(agent, ShipAgent):
            ship_kpis.append({
                "ship_id": ship_id,
                "name": agent.name,
                "state": agent.state,
                "cumulative_delay": round(agent.cumulative_delay, 1),
                "co2_emissions": round(agent.co2_emissions, 1),
                "lat": agent.lat,
                "lon": agent.lon,
                "current_port": agent.current_port,
                "next_port": agent.next_port,
            })

    return {"ships": ship_kpis}


@router.get("/kpi/trend")
def get_kpi_trend():
    kpi_calc = get_kpi_calculator()
    return {
        "trend": kpi_calc.get_trend_data(),
        "snapshots_count": len(kpi_calc._snapshots),
    }


@router.post("/kpi/snapshot")
def take_kpi_snapshot():
    model = get_model()
    kpi_calc = get_kpi_calculator()
    snapshot = kpi_calc.take_snapshot(model.current_time)
    return {
        "status": "success",
        "sim_time": snapshot.sim_time,
        "on_time_rate": round(snapshot.on_time_rate * 100, 1),
        "carbon_total": round(snapshot.carbon_total, 1),
        "avg_delay": round(snapshot.avg_delay_hours, 1),
    }


@router.post("/kpi/reset")
def reset_kpi():
    kpi_calc = get_kpi_calculator()
    kpi_calc.reset()
    return {"status": "success", "message": "KPI data reset"}


@router.get("/kpi/reliability")
def get_reliability_kpi():
    kpi_calc = get_kpi_calculator()
    model = get_model()
    port_scores = {}
    for port_id, port in model._ports.items():
        port_ontime = sum(1 for ship_id in port.waiting_queue if hasattr(model._agents.get(ship_id, None), 'cumulative_delay'))
        port_scores[port_id] = round((1 - port_ontime / max(len(port.waiting_queue), 1)) * 100, 1)
    reliability = kpi_calc.get_reliability_metrics(port_scores)
    return {
        "on_time_rate": reliability.on_time_rate,
        "mean_delay": reliability.mean_delay,
        "max_delay": reliability.max_delay,
        "delay_variance": reliability.delay_variance,
        "service_reliability_index": reliability.service_reliability_index,
        "port_reliability_scores": reliability.port_reliability_scores,
    }


@router.get("/kpi/carbon/breakdown")
def get_carbon_breakdown():
    kpi_calc = get_kpi_calculator()
    carbon = kpi_calc.get_carbon_metrics()
    return {
        "total_emissions": carbon.total_emissions,
        "per_ship_average": carbon.per_ship_average,
        "per_nautical_mile": carbon.per_nautical_mile,
        "operational_emissions": carbon.operational_emissions,
        "maneuvering_emissions": carbon.maneuvering_emissions,
        "carbon_intensity": carbon.carbon_intensity,
    }


@router.get("/kpi/robustness")
def get_robustness_kpi():
    kpi_calc = get_kpi_calculator()
    robustness = kpi_calc.get_robustness_metrics()
    return {
        "recovery_time": robustness.recovery_time,
        "max_queue_length": robustness.max_queue_length,
        "berth_blocking_probability": robustness.berth_blocking_probability,
        "schedule_recovery_factor": robustness.schedule_recovery_factor,
        "system_resilience_index": robustness.system_resilience_index,
    }


@router.get("/kpi/full-report")
def get_full_kpi_report():
    kpi_calc = get_kpi_calculator()
    model = get_model()
    port_scores = {}
    for port_id, port in model._ports.items():
        port_ontime = sum(1 for ship_id in port.waiting_queue if hasattr(model._agents.get(ship_id, None), 'cumulative_delay'))
        port_scores[port_id] = round((1 - port_ontime / max(len(port.waiting_queue), 1)) * 100, 1)
    reliability = kpi_calc.get_reliability_metrics(port_scores)
    carbon = kpi_calc.get_carbon_metrics()
    robustness = kpi_calc.get_robustness_metrics()
    return {
        "sim_time": model.current_time,
        "reliability": {
            "on_time_rate": reliability.on_time_rate,
            "mean_delay": reliability.mean_delay,
            "max_delay": reliability.max_delay,
            "delay_variance": reliability.delay_variance,
            "service_reliability_index": reliability.service_reliability_index,
        },
        "carbon": {
            "total_emissions": carbon.total_emissions,
            "per_ship_average": carbon.per_ship_average,
            "per_nautical_mile": carbon.per_nautical_mile,
            "operational_emissions": carbon.operational_emissions,
            "maneuvering_emissions": carbon.maneuvering_emissions,
            "carbon_intensity": carbon.carbon_intensity,
        },
        "robustness": {
            "recovery_time": robustness.recovery_time,
            "max_queue_length": robustness.max_queue_length,
            "berth_blocking_probability": robustness.berth_blocking_probability,
            "schedule_recovery_factor": robustness.schedule_recovery_factor,
            "system_resilience_index": robustness.system_resilience_index,
        },
    }
