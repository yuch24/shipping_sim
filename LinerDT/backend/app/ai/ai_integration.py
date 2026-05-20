from typing import Optional, Dict, Any, List, TYPE_CHECKING
import threading
from .safe_tools import SafeToolExecutor, ExperimentComparator, requires_confirmation
from .agent_config import get_agent_config_service
from .decision_agent import DecisionAgent

if TYPE_CHECKING:
    from .base_agent import BaseAIAgent, DecisionContext, AIDecision
    from .agent_config import AgentConfig


class AISchedulerIntegration:
    def __init__(self):
        self.ai_agents: Dict[str, "BaseAIAgent"] = {}
        self.ai_enabled: bool = False
        self.ai_config: Dict[str, Any] = {
            "speed_optimization": True,
            "cii_protection": True,
            "port_timing": False,
        }
        self._model = None

    def set_model(self, model) -> None:
        self._model = model

    def register_ai_agent(self, agent_id: str, agent: "BaseAIAgent") -> None:
        self.ai_agents[agent_id] = agent

    def enable_ai(self, enabled: bool = True) -> None:
        self.ai_enabled = enabled

    def configure(self, config: Dict[str, Any]) -> None:
        self.ai_config.update(config)

    def get_primary_agent(self) -> Optional["BaseAIAgent"]:
        if "primary" in self.ai_agents:
            return self.ai_agents["primary"]
        if self.ai_agents:
            return next(iter(self.ai_agents.values()))
        return None

    def request_speed_decision(
        self,
        context: "DecisionContext",
        target_arrival_time: Optional[float] = None
    ) -> Optional["AIDecision"]:
        if not self.ai_enabled:
            return None

        agent = self.get_primary_agent()
        if agent is None:
            return None

        return agent.evaluate_speed(context, target_arrival_time)

    def request_port_decision(
        self,
        context: "DecisionContext",
        available_ports: list[str]
    ) -> Optional["AIDecision"]:
        if not self.ai_enabled or not self.ai_config.get("port_timing", False):
            return None

        agent = self.get_primary_agent()
        if agent is None:
            return None

        return agent.evaluate_port_timing(context, available_ports)

    async def execute_tool(
        self, tool_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        if self._model is None:
            return {"success": False, "error": "Model not set"}

        executor = SafeToolExecutor(self._model)

        if tool_name == "modify_ship_param":
            result = await executor.execute_modify_ship(params["ship_id"], params["params"])
            return {"success": result.success, "message": result.message, "data": result.data}

        elif tool_name == "modify_route_param":
            result = await executor.execute_modify_route(params["route_id"], params["params"])
            return {"success": result.success, "message": result.message, "data": result.data}

        elif tool_name == "save_snapshot":
            result = await executor.execute_snapshot_save(params.get("name", "default"))
            return {"success": result.success, "message": result.message, "data": result.data}

        elif tool_name == "load_snapshot":
            result = await executor.execute_snapshot_load(params["name"])
            return {"success": result.success, "message": result.message, "data": result.data}

        elif tool_name == "rollback":
            result = await executor.execute_rollback()
            return {"success": result.success, "message": result.message, "data": result.data}

        elif tool_name == "compare_experiments":
            comparator = ExperimentComparator()
            return comparator.compare(params.get("metric", "on_time_rate"), params.get("baseline"))

        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

    def tool_requires_confirmation(self, tool_name: str) -> bool:
        return requires_confirmation(tool_name)

    def get_agent_configs(self) -> List[Dict[str, Any]]:
        """返回所有 agent 配置（用于 API / 前端展示）。"""
        return [c.model_dump() for c in get_agent_config_service().get_all()]

    def update_agent_config(self, config_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新 agent 配置并重新注册对应 agent。"""
        svc = get_agent_config_service()
        result = svc.update(config_id, updates)
        if result:
            self.register_ai_agent(config_id, DecisionAgent(result))
            if config_id == "balanced_agent":
                self.register_ai_agent("primary", DecisionAgent(result))
            return result.model_dump()
        return None

    def get_ai_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.ai_enabled,
            "config": self.ai_config,
            "registered_agents": list(self.ai_agents.keys()),
            "primary_agent": self.get_primary_agent().name if self.get_primary_agent() else None,
            "agent_configs": self.get_agent_configs(),
        }


_ai_integration_lock: threading.Lock = threading.Lock()
_ai_integration: Optional[AISchedulerIntegration] = None


def get_ai_integration() -> AISchedulerIntegration:
    global _ai_integration
    if _ai_integration is None:
        with _ai_integration_lock:
            if _ai_integration is None:
                _ai_integration = AISchedulerIntegration()
                _init_default_agents()
    return _ai_integration


def _init_default_agents() -> None:
    global _ai_integration
    if _ai_integration is not None:
        svc = get_agent_config_service()
        for config in svc.get_all():
            _ai_integration.register_ai_agent(config.id, DecisionAgent(config))
        # primary is always balanced_agent
        if "balanced_agent" in _ai_integration.ai_agents:
            _ai_integration.register_ai_agent("primary", _ai_integration.ai_agents["balanced_agent"])
