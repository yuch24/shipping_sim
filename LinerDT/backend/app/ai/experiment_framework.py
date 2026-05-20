from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import copy
import uuid


class ExperimentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MetricType(Enum):
    ON_TIME_RATE = "on_time_rate"
    AVG_DELAY = "avg_delay_hours"
    TOTAL_CO2 = "total_co2"
    FUEL_CONSUMPTION = "fuel_consumption"
    CII_RATIO = "cii_ratio"
    BERTH_UTILIZATION = "berth_utilization"
    SHIP_UTILIZATION = "ship_utilization"


@dataclass
class MetricResult:
    name: str
    value: float
    unit: str
    control_value: Optional[float] = None
    change_pct: Optional[float] = None


@dataclass
class ExperimentVariant:
    name: str
    description: str
    params: Dict[str, Any]
    metrics: Dict[str, MetricResult] = field(default_factory=dict)


@dataclass
class Experiment:
    id: str
    name: str
    description: str
    control_params: Dict[str, Any]
    variants: List[ExperimentVariant]
    status: ExperimentStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    conclusion: Optional[str] = None


class ExperimentRunner:
    def __init__(self, model):
        self.model = model
        self.experiments: Dict[str, Experiment] = {}
        self._saved_state: Optional[Dict[str, Any]] = None

    def create_experiment(
        self,
        name: str,
        description: str,
        control_params: Dict[str, Any],
        variant_configs: List[Dict[str, Any]],
    ) -> str:
        experiment_id = str(uuid.uuid4())[:8]

        variants = []
        for config in variant_configs:
            variant = ExperimentVariant(
                name=config["name"],
                description=config.get("description", ""),
                params=config.get("params", {}),
            )
            variants.append(variant)

        experiment = Experiment(
            id=experiment_id,
            name=name,
            description=description,
            control_params=control_params,
            variants=variants,
            status=ExperimentStatus.PENDING,
            created_at=datetime.now(),
        )

        self.experiments[experiment_id] = experiment
        return experiment_id

    def save_baseline_state(self) -> None:
        from app.services.state_serializer import serialize_simulation_state

        self._saved_state = serialize_simulation_state(self.model)

    def restore_baseline_state(self) -> None:
        if self._saved_state is None:
            return

        from app.services.state_serializer import deserialize_simulation_state

        deserialize_simulation_state(self.model, self._saved_state)

    def apply_variant_params(self, params: Dict[str, Any]) -> None:
        for ship_id, ship_params in params.get("ship_params", {}).items():
            ship = self.model.get_agent(ship_id)
            if ship and hasattr(ship, "update_params"):
                ship.update_params(ship_params)

        for key, value in params.get("global_params", {}).items():
            if hasattr(self.model, key):
                setattr(self.model, key, value)

    def run_variant(
        self,
        experiment_id: str,
        variant_index: int,
        duration_hours: float,
    ) -> Dict[str, Any]:
        if experiment_id not in self.experiments:
            return {"error": f"Experiment {experiment_id} not found"}

        experiment = self.experiments[experiment_id]
        if variant_index >= len(experiment.variants):
            return {"error": f"Variant {variant_index} not found"}

        variant = experiment.variants[variant_index]

        self.restore_baseline_state()
        self.apply_variant_params(variant.params)

        steps_run = self.model.scheduler.run_until(
            end_time=duration_hours,
            max_steps=5000,
        )

        metrics = self._collect_metrics()
        variant.metrics = metrics

        return {
            "variant_name": variant.name,
            "steps_run": steps_run,
            "final_time": self.model.current_time,
            "metrics": metrics,
        }

    def run_experiment(
        self,
        experiment_id: str,
        duration_hours: float = 0,
    ) -> Dict[str, Any]:
        if experiment_id not in self.experiments:
            return {"error": f"Experiment {experiment_id} not found"}

        experiment = self.experiments[experiment_id]
        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = datetime.now()

        control_result = self.run_variant(experiment_id, 0, duration_hours)

        if "error" in control_result:
            experiment.status = ExperimentStatus.CANCELLED
            return control_result

        results = {
            "experiment_id": experiment_id,
            "experiment_name": experiment.name,
            "control": control_result,
            "variants": [],
        }

        for i in range(1, len(experiment.variants)):
            variant_result = self.run_variant(experiment_id, i, duration_hours)
            results["variants"].append(variant_result)

            if "error" not in variant_result:
                self._compare_with_control(
                    experiment.variants[0].metrics,
                    experiment.variants[i].metrics,
                    experiment.variants[i],
                )

        experiment.status = ExperimentStatus.COMPLETED
        experiment.completed_at = datetime.now()
        experiment.conclusion = self._generate_conclusion(experiment)

        return results

    def _collect_metrics(self) -> Dict[str, MetricResult]:
        from app.services.kpi_calculator import get_kpi_calculator

        kpi = get_kpi_calculator()
        dashboard = kpi.get_dashboard_data(self.model.current_time)

        ships = [
            agent
            for agent in self.model._agents.values()
            if hasattr(agent, "co2_emissions")
        ]
        total_co2 = sum(getattr(ship, "co2_emissions", 0) for ship in ships)
        total_distance = sum(getattr(ship, "_total_distance_nm", 0) for ship in ships)

        avg_speed = (
            sum(getattr(ship, "current_speed", 0) for ship in ships) / len(ships)
            if ships
            else 0
        )

        metrics = {
            "on_time_rate": MetricResult(
                name="准班率",
                value=dashboard.get("on_time_rate", 0),
                unit="%",
            ),
            "avg_delay": MetricResult(
                name="平均延误",
                value=dashboard.get("avg_delay_hours", 0),
                unit="小时",
            ),
            "total_co2": MetricResult(
                name="总碳排放",
                value=total_co2,
                unit="吨",
            ),
            "cii_ratio": MetricResult(
                name="CII比率",
                value=total_co2 / (20000 * max(total_distance, 1)) * 1000,
                unit="",
            ),
        }

        return metrics

    def _compare_with_control(
        self,
        control_metrics: Dict[str, MetricResult],
        variant_metrics: Dict[str, MetricResult],
        variant: ExperimentVariant,
    ) -> None:
        for metric_name, variant_result in variant_metrics.items():
            if metric_name in control_metrics:
                control = control_metrics[metric_name]
                variant_result.control_value = control.value

                if control.value != 0:
                    change_pct = (
                        (variant_result.value - control.value) / control.value
                    ) * 100
                    variant_result.change_pct = change_pct

    def _generate_conclusion(self, experiment: Experiment) -> str:
        if not experiment.variants:
            return "No variants tested"

        control = experiment.variants[0].metrics
        conclusions = []

        for i, variant in enumerate(experiment.variants[1:], start=1):
            parts = []

            on_time_change = variant.metrics.get(
                "on_time_rate", MetricResult("", 0, "")
            ).change_pct
            if on_time_change is not None:
                if on_time_change > 5:
                    parts.append(f"准班率提升 {on_time_change:.1f}%")
                elif on_time_change < -5:
                    parts.append(f"准班率下降 {abs(on_time_change):.1f}%")

            co2_change = variant.metrics.get(
                "total_co2", MetricResult("", 0, "")
            ).change_pct
            if co2_change is not None:
                if co2_change < -5:
                    parts.append(f"碳排放降低 {abs(co2_change):.1f}%")
                elif co2_change > 5:
                    parts.append(f"碳排放增加 {co2_change:.1f}%")

            if parts:
                conclusions.append(f"{variant.name}: {', '.join(parts)}")
            else:
                conclusions.append(f"{variant.name}: 无显著差异")

        return "\n".join(conclusions) if conclusions else "实验完成，差异不显著"

    def get_experiment_results(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        if experiment_id not in self.experiments:
            return None

        experiment = self.experiments[experiment_id]

        return {
            "id": experiment.id,
            "name": experiment.name,
            "description": experiment.description,
            "status": experiment.status.value,
            "created_at": experiment.created_at.isoformat(),
            "started_at": experiment.started_at.isoformat()
            if experiment.started_at
            else None,
            "completed_at": experiment.completed_at.isoformat()
            if experiment.completed_at
            else None,
            "conclusion": experiment.conclusion,
            "variants": [
                {
                    "name": v.name,
                    "description": v.description,
                    "metrics": {
                        name: {
                            "value": m.value,
                            "unit": m.unit,
                            "change_pct": m.change_pct,
                        }
                        for name, m in v.metrics.items()
                    },
                }
                for v in experiment.variants
            ],
        }


def create_predefined_experiments(runner: ExperimentRunner) -> List[str]:
    experiments = []

    exp1 = runner.create_experiment(
        name="航速优化实验",
        description="对比经济航速 vs 全速航行的碳排放和准班率",
        control_params={},
        variant_configs=[
            {
                "name": "控制组",
                "description": "保持当前航速设置",
                "params": {},
            },
            {
                "name": "经济航速组",
                "description": "所有船舶降至经济航速(18节)",
                "params": {
                    "ship_params": {
                        "all": {"current_speed": 18.0, "design_speed": 18.0}
                    }
                },
            },
            {
                "name": "激进降速组",
                "description": "所有船舶降至16节",
                "params": {
                    "ship_params": {
                        "all": {"current_speed": 16.0, "design_speed": 16.0}
                    }
                },
            },
        ],
    )
    experiments.append(exp1)

    exp2 = runner.create_experiment(
        name="CII保护策略实验",
        description="对比开启/关闭CII保护功能的船队表现",
        control_params={"cii_protection": False},
        variant_configs=[
            {
                "name": "无CII保护",
                "description": "关闭CII自动调节",
                "params": {"global_params": {"cii_protection": False}},
            },
            {
                "name": "有CII保护",
                "description": "开启CII自动调节",
                "params": {"global_params": {"cii_protection": True}},
            },
        ],
    )
    experiments.append(exp2)

    return experiments
