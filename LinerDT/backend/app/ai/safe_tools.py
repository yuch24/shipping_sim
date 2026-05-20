from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import copy


@dataclass
class ToolResult:
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ParameterWhitelist:
    SHIP_PARAMS = {
        "current_speed": {"type": "float", "min": 1.0, "max": 25.0},
        "economic_speed": {"type": "float", "min": 10.0, "max": 22.0},
        "design_speed": {"type": "float", "min": 15.0, "max": 28.0},
        "load_factor": {"type": "float", "min": 0.3, "max": 1.0},
        "base_daily_consumption": {"type": "float", "min": 100.0, "max": 500.0},
    }

    ROUTE_PARAMS = {
        "speed_multiplier": {"type": "float", "min": 0.5, "max": 2.0},
        "delay_factor": {"type": "float", "min": 0.0, "max": 3.0},
    }

    @classmethod
    def validate(cls, category: str, param_name: str, value: Any) -> tuple[bool, str]:
        whitelist = getattr(cls, f"{category.upper()}_PARAMS", {})

        if param_name not in whitelist:
            return False, f"参数 {param_name} 不在白名单中"

        spec = whitelist[param_name]
        expected_type = spec["type"]

        if expected_type == "float":
            if not isinstance(value, (int, float)):
                return False, f"{param_name} 应为数字类型"
            if "min" in spec and value < spec["min"]:
                return False, f"{param_name} 不能小于 {spec['min']}"
            if "max" in spec and value > spec["max"]:
                return False, f"{param_name} 不能大于 {spec['max']}"

        return True, "OK"


class SafeToolExecutor:
    def __init__(self, model):
        self.model = model
        self._baseline: Optional[Dict[str, Any]] = None

    async def _save_baseline(self) -> str:
        from app.services.state_serializer import serialize_simulation_state
        snapshot = serialize_simulation_state(self.model)
        self._baseline = snapshot
        return "baseline_saved"

    async def _load_baseline(self) -> bool:
        if self._baseline is None:
            return False

        try:
            from app.services.state_serializer import deserialize_simulation_state
            deserialize_simulation_state(self.model, self._baseline)
            return True
        except Exception as e:
            print(f"Failed to load baseline: {e}")
            return False

    async def execute_modify_ship(
        self, ship_id: str, params: Dict[str, Any]
    ) -> ToolResult:
        # 先验证所有参数
        ship = self.model.get_agent(ship_id)
        if not ship:
            return ToolResult(False, f"Ship {ship_id} not found", error="Ship not found")

        for param_name, value in params.items():
            valid, msg = ParameterWhitelist.validate("SHIP", param_name, value)
            if not valid:
                return ToolResult(False, f"参数校验失败: {msg}", error=msg)

        await self._save_baseline()

        try:
            original_values = {}
            for param_name, value in params.items():
                if hasattr(ship, param_name):
                    original_values[param_name] = getattr(ship, param_name)
                    setattr(ship, param_name, value)

            ship.log_decision(
                reason=f"[AI Tool] 修改船舶参数: {params}",
                event="modify_ship_param",
                decision="parameter_change",
                context={"original": original_values, "new": params},
            )

            return ToolResult(
                True,
                f"船舶 {ship_id} 参数已修改: {params}",
                data={"ship_id": ship_id, "modified": params, "baseline": "saved"},
            )

        except Exception as e:
            await self._load_baseline()
            return ToolResult(False, f"修改失败，已回滚: {str(e)}", error=str(e))

    async def execute_modify_route(
        self, route_id: str, params: Dict[str, Any]
    ) -> ToolResult:
        for param_name, value in params.items():
            valid, msg = ParameterWhitelist.validate("route", param_name, value)
            if not valid:
                return ToolResult(False, f"参数校验失败: {msg}", error=msg)

        await self._save_baseline()

        try:
            # Check that at least one ship uses this route
            ships_on_route = [
                sid for sid, route in self.model._ship_routes.items()
                if route and (route_id == "AEU" or route == route_id or sid == route_id)
            ]
            if not ships_on_route:
                return ToolResult(False, f"航线 {route_id} 未找到", error="Route not found")

            # Apply route-level speed multiplier to all ships on this route
            speed_mult = params.get("speed_multiplier", 1.0)
            delay_factor = params.get("delay_factor", 0.0)
            modified_count = 0
            for ship_id in ships_on_route:
                ship = self.model.get_agent(ship_id)
                if ship:
                    ship.economic_speed = min(25, max(10, ship.economic_speed * speed_mult))
                    ship.cumulative_delay += delay_factor * 10
                    modified_count += 1

            return ToolResult(
                True,
                f"航线已修改: {params}，影响 {modified_count} 艘船舶",
                data={"route": route_id, "modified": params, "affected_ships": modified_count, "baseline": "saved"},
            )

        except Exception as e:
            await self._load_baseline()
            return ToolResult(False, f"修改失败，已回滚: {str(e)}", error=str(e))

    async def execute_snapshot_save(self, snapshot_name: str) -> ToolResult:
        try:
            from app.services.state_serializer import serialize_simulation_state

            snapshot = serialize_simulation_state(self.model)
            snapshot["snapshot_name"] = snapshot_name

            if not hasattr(self.model, "_snapshots"):
                self.model._snapshots = {}

            self.model._snapshots[snapshot_name] = snapshot

            return ToolResult(
                True,
                f"快照 '{snapshot_name}' 已保存",
                data={"snapshot_name": snapshot_name, "time": self.model.current_time},
            )

        except Exception as e:
            return ToolResult(False, f"保存快照失败: {str(e)}", error=str(e))

    async def execute_snapshot_load(self, snapshot_name: str) -> ToolResult:
        if not hasattr(self.model, "_snapshots") or snapshot_name not in self.model._snapshots:
            return ToolResult(False, f"快照 '{snapshot_name}' 不存在", error="Snapshot not found")

        try:
            from app.services.state_serializer import deserialize_simulation_state

            snapshot = self.model._snapshots[snapshot_name]
            deserialize_simulation_state(self.model, snapshot)

            self.log_decision = (
                lambda **kwargs: None  # Fallback if not available
            )
            for agent in self.model._agents.values():
                if hasattr(agent, "log_decision"):
                    agent.log_decision(
                        reason=f"[AI Tool] 加载快照: {snapshot_name}",
                        event="load_snapshot",
                        decision="state_restore",
                        context={"snapshot": snapshot_name, "time": snapshot.get("current_time")},
                    )
                    break

            return ToolResult(
                True,
                f"快照 '{snapshot_name}' 已加载",
                data={"snapshot_name": snapshot_name, "restored_time": snapshot.get("current_time")},
            )

        except Exception as e:
            return ToolResult(False, f"加载快照失败: {str(e)}", error=str(e))

    async def execute_rollback(self) -> ToolResult:
        if self._baseline is None:
            return ToolResult(False, "没有可回滚的基线", error="No baseline to rollback")

        try:
            from app.services.state_serializer import deserialize_simulation_state

            deserialize_simulation_state(self.model, self._baseline)

            return ToolResult(True, "已回滚到修改前的状态", data={"rollback": "success"})

        except Exception as e:
            return ToolResult(False, f"回滚失败: {str(e)}", error=str(e))


_unsafe_tool_names = {"modify_ship_param", "modify_route_param", "rollback_experiment"}


def requires_confirmation(tool_name: str) -> bool:
    return tool_name in _unsafe_tool_names


class ExperimentComparator:
    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def add_result(self, name: str, kpi_data: Dict[str, Any]) -> None:
        self.results.append({"name": name, "kpi": kpi_data})

    def compare(
        self, metric: str, baseline: str = None
    ) -> Dict[str, Any]:
        if len(self.results) < 2:
            return {"error": "需要至少2个实验结果才能对比"}

        if baseline:
            baseline_result = next((r for r in self.results if r["name"] == baseline), None)
            if not baseline_result:
                return {"error": f"基线 '{baseline}' 不存在"}

        comparison = {
            "metric": metric,
            "experiments": [],
            "winner": None,
            "improvement": {},
        }

        best_value = float("-inf") if metric.endswith("rate") else float("inf")
        winner = None

        for result in self.results:
            value = result.get("kpi", {}).get(metric, 0)
            comparison["experiments"].append({"name": result["name"], "value": value})

            is_better = (
                value > best_value if metric.endswith("rate") else value < best_value
            )

            if is_better:
                best_value = value
                winner = result["name"]

        comparison["winner"] = winner

        if baseline:
            baseline_value = baseline_result.get("kpi", {}).get(metric, 0)
            for exp in comparison["experiments"]:
                if exp["name"] != baseline:
                    improvement = (
                        ((exp["value"] - baseline_value) / baseline_value * 100)
                        if baseline_value != 0
                        else 0
                    )
                    comparison["improvement"][exp["name"]] = f"{improvement:+.1f}%"

        return comparison
