"""
DecisionAgent — 由 AgentConfig 驱动的决策代理

Agent 的行为完全由其配置定义：
- system_prompt: 人格描述（LLM 模式使用）
- tools: 启用的工具列表 + 参数覆盖
- parameters: 行为参数（阈值、权重等）
- decision_mode: "fast"（默认，快速路径）| "llm"（LLM 模式）

Fast path：读取配置 → 按序执行启用工具 → 返回 AIDecision
LLM path：读取配置 → 调用 LLM + tool schemas → 解析决策

零硬编码 if/else 逻辑。
"""

from typing import Optional, Dict, Any
from .base_agent import BaseAIAgent, DecisionContext, AIDecision, DecisionType
from .agent_config import AgentConfig, get_agent_config_service
from .decision_tools import execute_tool


class DecisionAgent(BaseAIAgent):
    """基于 AgentConfig 的决策代理，行为完全由配置决定。"""

    def __init__(self, config: AgentConfig):
        super().__init__(config.name)
        self.config = config
        self._last_speed_adjustment: Dict[str, float] = {}

    def evaluate_speed(
        self,
        context: DecisionContext,
        target_arrival_time: Optional[float] = None,
    ) -> Optional[AIDecision]:
        """根据配置的 decision_mode 执行决策。"""
        if self.config.decision_mode == "llm":
            return self._llm_decide(context, target_arrival_time)
        return self._fast_decide(context, target_arrival_time)

    def _fast_decide(
        self,
        context: DecisionContext,
        target_arrival_time: Optional[float] = None,
    ) -> Optional[AIDecision]:
        """
        快速路径：按序执行已启用的工具。

        工具执行顺序（由配置的 tools 列表定义）：
        1. get_cii_status / get_delay_info — 获取当前状态
        2. check_cooldown — 检查冷却
        3. calculate_optimal_speed — 计算建议航速
        4. adjust_speed — 执行调整
        """
        params = self.config.parameters
        enabled_tool_ids = {t.tool_id for t in self.config.tools if t.enabled}

        # 1. 获取状态
        cii_info = None
        delay_info = None
        if "get_cii_status" in enabled_tool_ids:
            raw = execute_tool("get_cii_status", context, {})
            cii_info = raw if isinstance(raw, dict) else None

        if "get_delay_info" in enabled_tool_ids:
            raw = execute_tool("get_delay_info", context, {})
            delay_info = raw if isinstance(raw, dict) else None

        delay = context.cumulative_delay
        cii_ratio = context.cii_ratio

        # 2. 计算最优航速
        suggested = None
        reason = ""
        confidence = 0.8

        if "calculate_optimal_speed" in enabled_tool_ids:
            calc_params = {
                "current_speed": context.current_speed,
                "economic_speed": context.economic_speed,
                "design_speed": context.design_speed,
                "delay_hours": delay,
                "cii_ratio": cii_ratio,
            }
            # 从 config 参数注入
            for param_key in [
                "delay_critical", "delay_warning", "cii_critical", "cii_warning",
                "speed_boost_critical", "speed_boost_warning", "max_speed_pct",
                "cii_reduce_speed_pct", "eco_speed_over_economic",
            ]:
                if param_key in params:
                    calc_params[param_key] = params[param_key]

            if target_arrival_time is not None:
                calc_params["target_arrival_time"] = target_arrival_time
                eta = self._estimate_arrival_time(context)
                if eta > 0:
                    calc_params["estimated_arrival_time"] = eta

            result = execute_tool("calculate_optimal_speed", context, calc_params)
            if isinstance(result, dict):
                suggested = result.get("suggested_speed")
                reason = result.get("reason", "")
                confidence = result.get("confidence", 0.8)

        if suggested is None:
            return None

        # 3. 检查冷却
        if "check_cooldown" in enabled_tool_ids:
            last_time = self._last_speed_adjustment.get(context.ship_id, -999)
            cooldown = params.get("cooldown_hours", 24.0)
            change_min = params.get("speed_change_min", 0.5)
            cool_result = execute_tool("check_cooldown", context, {
                "last_adjustment_time": last_time,
                "cooldown_hours": cooldown,
                "speed_change_min": change_min,
                "suggested_speed": suggested,
                "current_speed": context.current_speed,
                "sim_time": context.sim_time,
            })
            if isinstance(cool_result, dict) and not cool_result.get("can_adjust", True):
                return None

        self._last_speed_adjustment[context.ship_id] = context.sim_time

        # 4. 执行调整
        if "adjust_speed" in enabled_tool_ids:
            adj_params = {
                "new_speed": suggested,
                "reason": f"[{self.config.name}] {reason}",
                "confidence": confidence,
                "current_speed": context.current_speed,
                "economic_speed": context.economic_speed,
                "cii_ratio": cii_ratio,
                "cumulative_delay": delay,
            }
            adj_result = execute_tool("adjust_speed", context, adj_params)
            if adj_result is None:
                return None

            return AIDecision(
                decision_type=DecisionType.SPEED_ADJUSTMENT,
                ship_id=context.ship_id,
                suggested_action="adjust_speed",
                suggested_value=suggested,
                reason=reason,
                confidence=confidence,
                context={
                    "current_speed": context.current_speed,
                    "economic_speed": context.economic_speed,
                    "cii_ratio": cii_ratio,
                    "cumulative_delay": delay,
                    "agent_config": self.config.id,
                },
            )

        return None

    def evaluate_port_timing(
        self,
        context: DecisionContext,
        available_ports: list[str],
    ) -> Optional[AIDecision]:
        if len(available_ports) <= 1:
            return None
        return None  # 港口调度暂未实现为工具

    def _llm_decide(
        self,
        context: DecisionContext,
        target_arrival_time: Optional[float] = None,
    ) -> Optional[AIDecision]:
        """LLM 路径：通过 LLM 决策。"""
        from .llm_decision_agent import llm_decide_speed
        return llm_decide_speed(self.config, context, target_arrival_time)

    def _estimate_arrival_time(self, context: DecisionContext) -> float:
        if context.current_port and context.next_port:
            try:
                from app.services.navigation import haversine
                from app.scheduler.scheduler import get_model
                model = get_model()
                next_port = model.get_port(context.next_port)
                if next_port and context.lat and context.lon:
                    distance = haversine(context.lat, context.lon, next_port.lat, next_port.lon)
                    return distance / context.current_speed
            except Exception:
                import logging
                logger = logging.getLogger(__name__)
                logger.debug("无法估算到港时间: %s -> %s", context.current_port, context.next_port, exc_info=True)
        return 0.0
