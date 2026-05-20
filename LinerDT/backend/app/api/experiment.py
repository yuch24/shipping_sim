from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter
import json
import os
import random

from ..scheduler.scheduler import get_model, EventDrivenScheduler
from ..scheduler.event_queue import EventQueue
from ..services.kpi_calculator import get_kpi_calculator

router = APIRouter()

SNAPSHOT_DIR = "snapshots"
SCENARIOS_DIR = "scenarios"


class Snapshot(BaseModel):
    id: str
    name: str
    sim_time: float
    created_at: str
    ships: dict
    ports: dict
    event_queue: list
    speed: float


class ParameterSweepConfig(BaseModel):
    parameter_name: str
    start_value: float
    end_value: float
    step_count: int
    target_metric: str = "on_time_rate"


class MonteCarloConfig(BaseModel):
    runs: int = 100
    seed: Optional[int] = None
    uncertainty_level: str = "medium"


class WhatIfScenario(BaseModel):
    id: str
    name: str
    description: str
    parameter_overrides: dict


class CompareRequest(BaseModel):
    scenario_ids: List[str] = []


DEFAULT_SCENARIOS = [
    WhatIfScenario(
        id="base",
        name="基础场景",
        description="默认参数配置",
        parameter_overrides={},
    ),
    WhatIfScenario(
        id="high_congestion",
        name="港口拥堵",
        description="所有港口处理效率降低30%，反映港口拥堵",
        parameter_overrides={"port_efficiency_factor": 0.7},
    ),
    WhatIfScenario(
        id="carbon_tax",
        name="碳税政策",
        description="碳排放成本增加50%，激励降速航行",
        parameter_overrides={
            "carbon_cost_factor": 1.5,
            "speed_reduction_benefit": 0.15,
        },
    ),
    WhatIfScenario(
        id="cii_strict",
        name="CII严格监管",
        description="CII评级阈值收紧20%，更多船舶面临限速",
        parameter_overrides={"cii_a_threshold": 0.08, "cii_b_threshold": 0.095},
    ),
    WhatIfScenario(
        id="weather_disruption",
        name="恶劣天气",
        description="天气延误增加50%，影响航行可靠性",
        parameter_overrides={"weather_delay_multiplier": 1.5},
    ),
    WhatIfScenario(
        id="fuel_shortage",
        name="燃料供应紧张",
        description="VLSFO价格上涨，经济航速降低15%",
        parameter_overrides={"economic_speed_factor": 0.85, "fuel_cost_factor": 1.3},
    ),
]


def ensure_snapshot_dir():
    if not os.path.exists(SNAPSHOT_DIR):
        os.makedirs(SNAPSHOT_DIR)


def ensure_scenarios_dir():
    if not os.path.exists(SCENARIOS_DIR):
        os.makedirs(SCENARIOS_DIR)


def create_snapshot(model, name: str = "snapshot") -> Snapshot:
    from ..services.state_serializer import serialize_simulation_state

    state = serialize_simulation_state(model)
    event_queue_data = model.scheduler.event_queue.to_list()

    snapshot = Snapshot(
        id=f"{name}_{int(datetime.now().timestamp())}",
        name=name,
        sim_time=model.current_time,
        created_at=datetime.now().isoformat(),
        ships=state["ships"],
        ports=state["ports"],
        event_queue=event_queue_data,
        speed=model.speed,
    )

    return snapshot


def save_snapshot_to_disk(snapshot: Snapshot) -> str:
    ensure_snapshot_dir()
    filepath = os.path.join(SNAPSHOT_DIR, f"{snapshot.id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(snapshot.model_dump(), f, ensure_ascii=False, indent=2)
    return filepath


def load_snapshot_from_disk(snapshot_id: str) -> Optional[Snapshot]:
    filepath = os.path.join(SNAPSHOT_DIR, f"{snapshot_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Snapshot(**data)


def restore_model_from_snapshot(model, snapshot: Snapshot) -> None:
    from ..services.state_serializer import deserialize_simulation_state

    data = {
        "current_time": snapshot.sim_time,
        "speed": snapshot.speed,
        "ships": snapshot.ships,
        "ports": snapshot.ports,
        "ship_routes": {},
        "event_queue": snapshot.event_queue,
    }
    deserialize_simulation_state(model, data)

    AEU_ROUTE = [
        "SHA",
        "NGB",
        "XMN",
        "HKG",
        "SZX",
        "SIN",
        "PIR",
        "RTM",
        "HAM",
        "PIR",
        "SIN",
        "SHA",
    ]
    for ship_id in model._agents.keys():
        model._ship_routes[ship_id] = AEU_ROUTE


@router.get("/snapshots")
def list_snapshots():
    ensure_snapshot_dir()
    files = [f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json")]
    snapshots = []
    for f in files:
        filepath = os.path.join(SNAPSHOT_DIR, f)
        with open(filepath, "r", encoding="utf-8") as fp:
            data = json.load(fp)
            snapshots.append(
                {
                    "id": data["id"],
                    "name": data["name"],
                    "sim_time": data["sim_time"],
                    "created_at": data["created_at"],
                }
            )
    return {"snapshots": sorted(snapshots, key=lambda x: x["created_at"], reverse=True)}


@router.post("/snapshots")
def create_snapshot_endpoint(name: str = "snapshot"):
    model = get_model()
    snapshot = create_snapshot(model, name)
    filepath = save_snapshot_to_disk(snapshot)
    return {
        "status": "success",
        "snapshot_id": snapshot.id,
        "filepath": filepath,
        "sim_time": snapshot.sim_time,
    }


@router.get("/snapshots/{snapshot_id}")
def get_snapshot(snapshot_id: str):
    snapshot = load_snapshot_from_disk(snapshot_id)
    if snapshot is None:
        return {"status": "error", "message": "Snapshot not found"}
    return {
        "status": "success",
        "snapshot": {
            "id": snapshot.id,
            "name": snapshot.name,
            "sim_time": snapshot.sim_time,
            "created_at": snapshot.created_at,
            "ships_count": len(snapshot.ships),
            "ports_count": len(snapshot.ports),
            "events_count": len(snapshot.event_queue),
        },
    }


@router.post("/snapshots/{snapshot_id}/restore")
def restore_snapshot(snapshot_id: str):
    model = get_model()
    snapshot = load_snapshot_from_disk(snapshot_id)
    if snapshot is None:
        return {"status": "error", "message": "Snapshot not found"}

    restore_model_from_snapshot(model, snapshot)
    return {
        "status": "success",
        "message": f"Restored to snapshot {snapshot_id}",
        "sim_time": model.current_time,
    }


@router.delete("/snapshots/{snapshot_id}")
def delete_snapshot(snapshot_id: str):
    filepath = os.path.join(SNAPSHOT_DIR, f"{snapshot_id}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
        return {"status": "success", "message": f"Deleted snapshot {snapshot_id}"}
    return {"status": "error", "message": "Snapshot not found"}


@router.post("/sweep")
def run_parameter_sweep(config: ParameterSweepConfig):
    from ..services.state_serializer import (
        serialize_simulation_state,
        deserialize_simulation_state,
    )
    from ..services.kpi_calculator import get_kpi_calculator

    model = get_model()
    base_state = serialize_simulation_state(model)
    results = []

    step_size = (config.end_value - config.start_value) / max(config.step_count - 1, 1)

    for i in range(config.step_count):
        value = config.start_value + i * step_size

        if hasattr(model, config.parameter_name):
            setattr(model, config.parameter_name, value)

        model.reset()
        model.run_until(7200)

        kpi = get_kpi_calculator()
        dashboard = kpi.get_dashboard_data()

        metric_value = 0.0
        if config.target_metric == "on_time_rate":
            metric_value = dashboard["on_time_rate"]
        elif config.target_metric == "total_carbon":
            metric_value = dashboard["carbon_total"]
        elif config.target_metric == "avg_delay":
            metric_value = dashboard["avg_delay_hours"]

        results.append(
            {
                "parameter_value": round(value, 4),
                "run_index": i,
                "metric_value": round(metric_value, 4),
            }
        )

        deserialize_simulation_state(model, base_state)

    return {
        "status": "completed",
        "parameter": config.parameter_name,
        "target_metric": config.target_metric,
        "runs": results,
    }


@router.post("/monte-carlo")
def run_monte_carlo(config: MonteCarloConfig):
    from ..services.state_serializer import (
        serialize_simulation_state,
        deserialize_simulation_state,
    )
    from ..services.kpi_calculator import get_kpi_calculator
    import numpy as np

    model = get_model()
    base_state = serialize_simulation_state(model)
    results = []

    seeds = [
        config.seed + i if config.seed else random.randint(0, 999999)
        for i in range(config.runs)
    ]

    for seed in seeds:
        random.seed(seed)
        np.random.seed(seed)

        model.reset()
        model.run_until(7200)

        kpi = get_kpi_calculator()
        dashboard = kpi.get_dashboard_data()

        results.append(
            {
                "seed": seed,
                "on_time_rate": round(dashboard["on_time_rate"], 4),
                "total_carbon": round(dashboard["carbon_total"], 2),
                "avg_delay": round(dashboard["avg_delay_hours"], 2),
            }
        )

        deserialize_simulation_state(model, base_state)

    on_time_rates = [r["on_time_rate"] for r in results]
    carbons = [r["total_carbon"] for r in results]
    delays = [r["avg_delay"] for r in results]

    return {
        "status": "completed",
        "runs": config.runs,
        "summary": {
            "on_time_rate": {
                "mean": round(float(np.mean(on_time_rates)), 4),
                "std": round(float(np.std(on_time_rates)), 4),
                "min": round(float(np.min(on_time_rates)), 4),
                "max": round(float(np.max(on_time_rates)), 4),
                "p5": round(float(np.percentile(on_time_rates, 5)), 4),
                "p95": round(float(np.percentile(on_time_rates, 95)), 4),
            },
            "total_carbon": {
                "mean": round(float(np.mean(carbons)), 2),
                "std": round(float(np.std(carbons)), 2),
                "min": round(float(np.min(carbons)), 2),
                "max": round(float(np.max(carbons)), 2),
            },
            "avg_delay": {
                "mean": round(float(np.mean(delays)), 2),
                "std": round(float(np.std(delays)), 2),
                "min": round(float(np.min(delays)), 2),
                "max": round(float(np.max(delays)), 2),
            },
        },
        "individual_runs": results,
    }


@router.get("/scenarios")
def list_whatif_scenarios():
    ensure_scenarios_dir()

    scenarios = DEFAULT_SCENARIOS.copy()

    for f in os.listdir(SCENARIOS_DIR):
        if f.endswith(".json"):
            filepath = os.path.join(SCENARIOS_DIR, f)
            with open(filepath, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                scenarios.append(WhatIfScenario(**data))

    return {
        "scenarios": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "is_default": s.id in [x.id for x in DEFAULT_SCENARIOS],
            }
            for s in scenarios
        ]
    }


@router.post("/scenarios/{scenario_id}/run")
def run_whatif_scenario(scenario_id: str):
    from ..services.state_serializer import (
        serialize_simulation_state,
        deserialize_simulation_state,
    )
    from ..services.kpi_calculator import get_kpi_calculator

    model = get_model()
    base_state = serialize_simulation_state(model)

    scenario = None
    for s in DEFAULT_SCENARIOS:
        if s.id == scenario_id:
            scenario = s
            break

    if not scenario:
        ensure_scenarios_dir()
        filepath = os.path.join(SCENARIOS_DIR, f"{scenario_id}.json")
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                scenario = WhatIfScenario(**json.load(f))

    if not scenario:
        return {"status": "error", "message": "Scenario not found"}

    original_values = {}
    for param, value in scenario.parameter_overrides.items():
        if hasattr(model, param):
            original_values[param] = getattr(model, param)
            setattr(model, param, value)

    model.reset()
    model.run_until(7200)

    kpi = get_kpi_calculator()
    dashboard = kpi.get_dashboard_data()

    for param, original in original_values.items():
        setattr(model, param, original)

    deserialize_simulation_state(model, base_state)

    return {
        "status": "completed",
        "scenario_id": scenario_id,
        "scenario_name": scenario.name,
        "kpi": dashboard,
    }


@router.post("/scenarios/compare")
def compare_scenarios(req: CompareRequest):
    from ..services.state_serializer import (
        serialize_simulation_state,
        deserialize_simulation_state,
    )
    from ..services.kpi_calculator import get_kpi_calculator

    model = get_model()
    base_state = serialize_simulation_state(model)

    results = []
    for scenario_id in req.scenario_ids:
        scenario = None
        for s in DEFAULT_SCENARIOS:
            if s.id == scenario_id:
                scenario = s
                break

        if not scenario:
            ensure_scenarios_dir()
            filepath = os.path.join(SCENARIOS_DIR, f"{scenario_id}.json")
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    scenario = WhatIfScenario(**json.load(f))

        if not scenario:
            continue

        original_values = {}
        for param, value in scenario.parameter_overrides.items():
            if hasattr(model, param):
                original_values[param] = getattr(model, param)
                setattr(model, param, value)

        model.reset()
        model.run_until(7200)

        kpi = get_kpi_calculator()
        dashboard = kpi.get_dashboard_data()

        for param, original in original_values.items():
            setattr(model, param, original)

        results.append(
            {
                "scenario_id": scenario_id,
                "scenario_name": scenario.name,
                "kpi": dashboard,
            }
        )

        deserialize_simulation_state(model, base_state)

    return {
        "status": "completed",
        "scenarios": results,
    }


@router.post("/scenarios")
def create_custom_scenario(scenario: WhatIfScenario):
    ensure_scenarios_dir()
    filepath = os.path.join(SCENARIOS_DIR, f"{scenario.id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(scenario.model_dump(), f, ensure_ascii=False, indent=2)
    return {"status": "success", "scenario_id": scenario.id}


@router.get("/scenarios/{scenario_id}")
def get_scenario_details(scenario_id: str):
    for s in DEFAULT_SCENARIOS:
        if s.id == scenario_id:
            return {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "parameter_overrides": s.parameter_overrides,
                "is_default": True,
            }

    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {**data, "is_default": False}

    return {"status": "error", "message": "Scenario not found"}


@router.post("/experiment/report")
def generate_experiment_report():
    """生成实验报告（Markdown 格式）"""
    from ..scheduler.scheduler import get_model

    model = get_model()
    kpi_calc = get_kpi_calculator()
    dashboard = kpi_calc.get_dashboard_data()

    port_kpis = []
    for port_id, port in model._ports.items():
        total_berths = port.berth_count
        available = port.available_berths
        utilization = (
            ((total_berths - available) / total_berths * 100) if total_berths > 0 else 0
        )
        port_kpis.append(
            {
                "port_id": port_id,
                "name": port.name,
                "utilization": round(utilization, 1),
                "queue_length": len(port.waiting_queue),
            }
        )

    report = f"""# LinerDT 仿真实验报告

## 实验概要

- **仿真时间**: {dashboard["sim_time"]:.1f} 小时 ({dashboard["sim_time"] / 24:.1f} 天)
- **船舶数量**: {dashboard["ships_tracked"]} 艘
- **港口数量**: {len(model._ports)} 个

## 关键绩效指标

| 指标 | 值 |
|------|-----|
| 准班率 | {dashboard["on_time_rate"]}% |
| 平均延误 | {dashboard["avg_delay_hours"]} 小时 |
| 碳排放总量 | {dashboard["carbon_total"]} 吨 |
| 总到港次数 | {dashboard["total_arrivals"]} |

## 港口状态

| 港口 | 泊位利用率 | 排队长度 |
|------|-----------|---------|
"""
    for pk in port_kpis:
        report += f"| {pk['name']} | {pk['utilization']}% | {pk['queue_length']} |\n"

    reliability = kpi_calc.get_reliability_metrics({})
    carbon = kpi_calc.get_carbon_metrics()
    robustness = kpi_calc.get_robustness_metrics()

    report += f"""
## 可靠性分析

- **服务可靠性指数**: {reliability.service_reliability_index:.2f}
- **最大延误**: {reliability.max_delay:.1f} 小时
- **延误方差**: {reliability.delay_variance:.2f}

## 碳排放分析

- **单船平均排放**: {carbon.per_ship_average:.2f} 吨
- **每海里排放**: {carbon.per_nautical_mile:.4f} 吨
- **作业排放**: {carbon.operational_emissions:.2f} 吨
- **机动排放**: {carbon.maneuvering_emissions:.2f} 吨

## 系统鲁棒性

- **恢复时间**: {robustness.recovery_time:.1f} 小时
- **最大队列长度**: {robustness.max_queue_length}
- **泊位阻塞概率**: {robustness.berth_blocking_probability:.3f}
- **系统韧性指数**: {robustness.system_resilience_index:.2f}

## 结论

仿真运行 {dashboard["sim_time"] / 24:.1f} 天，准班率为 {dashboard["on_time_rate"]}%，
碳排放总量 {dashboard["carbon_total"]} 吨。
"""

    return {
        "status": "success",
        "report": report,
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "sim_time_hours": dashboard["sim_time"],
            "total_ships": dashboard["ships_tracked"],
            "report_format": "markdown",
        },
    }


@router.get("/experiment/export")
def export_experiment_config():
    """导出当前实验配置及结果（JSON）"""
    from ..scheduler.scheduler import get_model

    model = get_model()
    kpi_calc = get_kpi_calculator()
    dashboard = kpi_calc.get_dashboard_data()

    config = {
        "experiment": {
            "name": "AEU Route Simulation",
            "description": "Asia-Europe Express 航线仿真",
            "created_at": datetime.now().isoformat(),
            "version": "0.1.0",
        },
        "simulation_state": {
            "current_time": dashboard["sim_time"],
            "ships_count": dashboard["ships_tracked"],
            "ports_count": len(model._ports),
        },
        "results": {
            "kpi": dashboard,
            "reliability": {
                "service_reliability_index": kpi_calc.get_reliability_metrics(
                    {}
                ).service_reliability_index,
                "max_delay": kpi_calc.get_max_delay(),
            },
            "fleet_summary": {
                "total_co2": kpi_calc.get_total_carbon(),
            },
        },
        "reproducibility": {
            "framework": "LinerDT Agent-based DES",
            "scheduler": "EventDrivenScheduler",
            "routing": "AEU 9-port loop",
        },
    }

    return config
