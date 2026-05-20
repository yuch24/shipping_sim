"""
LLM 决策代理 — 调用 LLM 进行决策

将 AgentConfig 的 system_prompt + context + tool schemas 传递给 LLM，
LLM 自主决定调用哪些工具（或直接给出决策），结果解析为 AIDecision。
"""

import json
import logging
from typing import Optional, Dict, Any
from .base_agent import DecisionContext, AIDecision, DecisionType
from .agent_config import AgentConfig
from .decision_tools import TOOL_SCHEMAS, execute_tool, get_tool_schema_dict

logger = logging.getLogger(__name__)


def _build_decision_prompt(config: AgentConfig, context: DecisionContext,
                           target_arrival_time: Optional[float] = None) -> str:
    """构建 LLM 决策提示词，注入当前状态。"""
    ctx_lines = [
        f"仿真时间: D{int(context.sim_time/24)} H{context.sim_time%24:.0f}",
        f"船舶: {context.ship_name}({context.ship_id})",
        f"当前航速: {context.current_speed}节 | 经济航速: {context.economic_speed}节 | 设计航速: {context.design_speed}节",
        f"CII比值: {context.cii_ratio:.3f} | 累积延误: {context.cumulative_delay:.1f}h",
        f"CO₂排放: {context.co2_emissions:.1f}t | 载箱量: {context.capacity_teu}TEU",
        f"状态: {context.current_state}",
        f"当前港口: {context.current_port or '无'} | 下一港: {context.next_port or '无'}",
    ]
    if target_arrival_time is not None:
        ctx_lines.append(f"目标到港时间: {target_arrival_time}h")

    params_lines = "\n".join(f"  {k}: {v}" for k, v in config.parameters.items())

    return (
        f"{config.system_prompt}\n\n"
        f"## 当前状态\n"
        + "\n".join(ctx_lines) + "\n\n"
        f"## 配置参数\n"
        f"{params_lines}\n\n"
        f"## 任务\n"
        f"基于当前状态和你可用的工具，做出航速决策。\n"
        f"如需调整航速，调用 adjust_speed 工具。\n"
        f"如需获取更多信息，可调用查询工具。\n"
        f"如果不需调整，返回 no_adjustment。"
    )


def llm_decide_speed(
    config: AgentConfig,
    context: DecisionContext,
    target_arrival_time: Optional[float] = None,
) -> Optional[AIDecision]:
    """
    使用 LLM 进行航速决策。

    注意：此函数是同步的，LLM 调用会阻塞。
    在仿真循环中使用时性能会降低。
    """
    from ..services.llm_adapter import get_llm_adapter, LLMMessage

    llm = get_llm_adapter()
    if not llm.is_configured():
        logger.warning("LLM 未配置，回退到 fast 路径决策")
        from .decision_agent import DecisionAgent
        fallback = DecisionAgent(config)
        fallback.config.decision_mode = "fast"
        return fallback.evaluate_speed(context, target_arrival_time)

    # 构建可用的 tool schemas
    enabled_tool_ids = {t.tool_id for t in config.tools if t.enabled}
    available_schemas = []
    for tid in enabled_tool_ids:
        schema = get_tool_schema_dict(tid)
        if schema:
            available_schemas.append(schema)

    prompt = _build_decision_prompt(config, context, target_arrival_time)

    try:
        messages = [LLMMessage(role="system", content=prompt)]
        functions = [TOOL_SCHEMAS[tid] for tid in enabled_tool_ids if tid in TOOL_SCHEMAS]

        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # 已在事件循环中 — 使用 chat_with_function_call
            result = llm.chat_with_function_call(messages, functions)
            # 非流式 — 直接返回结果
        else:
            result = asyncio.run(llm.chat_with_function_call(messages, functions))

        return _parse_llm_result(result, context, config.parameters)

    except Exception as e:
        logger.error(f"LLM 决策失败: {e}")
        return None


def _parse_llm_result(
    result: Dict[str, Any],
    context: DecisionContext,
    params: Dict[str, float],
) -> Optional[AIDecision]:
    """解析 LLM 返回结果，转为 AIDecision。"""
    content = result.get("content", "").strip()
    tool_calls = result.get("tool_calls", [])

    # 如果 LLM 表示不需调整
    if "no_adjustment" in content.lower():
        return None

    # 解析工具调用
    for tc in tool_calls:
        if tc.get("name") == "adjust_speed":
            try:
                args = json.loads(tc.get("arguments", "{}"))
            except json.JSONDecodeError:
                continue

            new_speed = args.get("new_speed")
            reason = args.get("reason", "LLM 决策调整")
            if new_speed is None:
                continue

            return AIDecision(
                decision_type=DecisionType.SPEED_ADJUSTMENT,
                ship_id=context.ship_id,
                suggested_action="adjust_speed",
                suggested_value=float(new_speed),
                reason=f"[LLM] {reason}",
                confidence=float(args.get("confidence", 0.7)),
                context={
                    "current_speed": context.current_speed,
                    "economic_speed": context.economic_speed,
                    "cii_ratio": context.cii_ratio,
                    "cumulative_delay": context.cumulative_delay,
                    "llm_decided": True,
                },
            )

    # LLM 未调用 adjust_speed — 无决策
    return None
