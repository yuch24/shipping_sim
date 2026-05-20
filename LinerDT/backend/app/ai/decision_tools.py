"""
决策工具注册表

将原有 Agent 中的 if/else 决策逻辑封装为独立的可调用工具。
每个工具有 schema（LLM 可用）+ 实现函数（Python 可调用）。
Agent 通过配置决定启用哪些工具以及工具的执行参数。
"""

from typing import Any, Dict, Optional, List
from .base_agent import DecisionContext, AIDecision, DecisionType
from ..services.llm_adapter import LLMFunction


# ======== Tool Schemas (for LLM calling) ========

def _number_prop(description: str) -> dict:
    return {"type": "number", "description": description}


def _string_prop(description: str) -> dict:
    return {"type": "string", "description": description}


TOOL_SCHEMAS = {
    "get_cii_status": LLMFunction(
        name="get_cii_status",
        description="获取船舶当前的CII碳排放强度比值（1.0=达标）和A-E评级",
        parameters={
            "type": "object",
            "properties": {"ship_id": _string_prop("船舶ID")},
            "required": ["ship_id"],
        },
    ),
    "get_delay_info": LLMFunction(
        name="get_delay_info",
        description="获取船舶当前的累积延误时间（小时）和航行状态",
        parameters={
            "type": "object",
            "properties": {"ship_id": _string_prop("船舶ID")},
            "required": ["ship_id"],
        },
    ),
    "get_port_queue_info": LLMFunction(
        name="get_port_queue_info",
        description="获取港口当前的排队长度和可用泊位数量",
        parameters={
            "type": "object",
            "properties": {"port_id": _string_prop("港口ID")},
            "required": ["port_id"],
        },
    ),
    "check_cooldown": LLMFunction(
        name="check_cooldown",
        description="检查两次航速调整是否满足冷却间隔要求",
        parameters={
            "type": "object",
            "properties": {
                "ship_id": _string_prop("船舶ID"),
                "sim_time": _number_prop("当前仿真时间(小时)"),
                "last_adjustment_time": _number_prop("上次调整时间(小时)，未知则传-999"),
                "cooldown_hours": _number_prop("冷却间隔(小时)"),
                "speed_change_min": _number_prop("最小调整幅度(节)"),
                "current_speed": _number_prop("当前航速"),
                "suggested_speed": _number_prop("建议航速"),
            },
            "required": ["ship_id", "sim_time", "last_adjustment_time", "cooldown_hours"],
        },
    ),
    "calculate_optimal_speed": LLMFunction(
        name="calculate_optimal_speed",
        description="基于延误和CII状况，使用航运经验公式计算最优航速。返回建议航速和推理说明。",
        parameters={
            "type": "object",
            "properties": {
                "current_speed": _number_prop("当前航速(节)"),
                "economic_speed": _number_prop("经济航速(节)"),
                "design_speed": _number_prop("设计航速(节)"),
                "delay_hours": _number_prop("累积延误(小时)"),
                "cii_ratio": _number_prop("CII比值(1.0=达标)"),
                "delay_critical": _number_prop("严重延误阈值(小时)"),
                "delay_warning": _number_prop("中度延误阈值(小时)"),
                "cii_critical": _number_prop("CII临界阈值"),
                "cii_warning": _number_prop("CII警告阈值"),
                "speed_boost_critical": _number_prop("严重延误时提速幅度(节)"),
                "speed_boost_warning": _number_prop("中度延误时提速幅度(节)"),
                "max_speed_pct": _number_prop("最大航速占设计航速比例"),
                "cii_reduce_speed_pct": _number_prop("CII超标时航速比例"),
                "eco_speed_over_economic": _number_prop("CII警告时超出经济航速(节)"),
                "target_arrival_time": _number_prop("目标到港时间(小时)，可选"),
                "estimated_arrival_time": _number_prop("预计到港时间(小时)，可选"),
            },
            "required": ["current_speed", "economic_speed", "design_speed", "delay_hours", "cii_ratio"],
        },
    ),
    "evaluate_tradeoff": LLMFunction(
        name="evaluate_tradeoff",
        description="计算多目标综合评分（延误+碳排放+燃油+港口效率加权和）",
        parameters={
            "type": "object",
            "properties": {
                "delay_score": _number_prop("延误得分(0-1)"),
                "cii_score": _number_prop("碳排放得分(0-1)"),
                "fuel_score": _number_prop("燃油成本得分(0-1)"),
                "port_score": _number_prop("港口效率得分(0-1)"),
                "delay_weight": _number_prop("延误权重"),
                "cii_weight": _number_prop("碳排放权重"),
                "fuel_weight": _number_prop("燃油成本权重"),
                "port_weight": _number_prop("港口效率权重"),
            },
            "required": ["delay_weight", "cii_weight", "fuel_weight", "port_weight"],
        },
    ),
    "adjust_speed": LLMFunction(
        name="adjust_speed",
        description="执行航速调整。将船舶航速设为新值并记录决策日志。",
        parameters={
            "type": "object",
            "properties": {
                "ship_id": _string_prop("船舶ID"),
                "new_speed": _number_prop("新航速(节)"),
                "reason": _string_prop("调整原因"),
                "confidence": _number_prop("决策置信度(0-1)"),
                "current_speed": _number_prop("当前航速(节)"),
                "economic_speed": _number_prop("经济航速(节)"),
                "cii_ratio": _number_prop("当前CII比值"),
                "cumulative_delay": _number_prop("当前累积延误(小时)"),
            },
            "required": ["ship_id", "new_speed", "reason"],
        },
    ),
}


def get_tool_schema(tool_id: str) -> Optional[LLMFunction]:
    return TOOL_SCHEMAS.get(tool_id)


def get_all_tool_schemas() -> List[LLMFunction]:
    return list(TOOL_SCHEMAS.values())


def get_tool_schema_dict(tool_id: str) -> Optional[dict]:
    """返回 OpenAI 格式的 tool schema dict。"""
    func = TOOL_SCHEMAS.get(tool_id)
    if not func:
        return None
    return {
        "type": "function",
        "function": {
            "name": func.name,
            "description": func.description,
            "parameters": func.parameters,
        },
    }


TOOL_IDS = list(TOOL_SCHEMAS.keys())


# ======== Tool Implementations (for fast path) ========


def execute_cii_status(context: DecisionContext, **kwargs) -> dict:
    """获取 CII 状态信息。"""
    return {
        "cii_ratio": context.cii_ratio,
        "cii_rating": _get_cii_rating_from_ratio(context.cii_ratio),
        "co2_emissions": context.co2_emissions,
        "economic_speed": context.economic_speed,
    }


def execute_delay_info(context: DecisionContext, **kwargs) -> dict:
    """获取延误信息。"""
    return {
        "cumulative_delay": context.cumulative_delay,
        "current_port": context.current_port,
        "next_port": context.next_port,
        "current_speed": context.current_speed,
        "sim_time": context.sim_time,
        "state": context.current_state,
    }


def execute_check_cooldown(
    context: DecisionContext,
    last_adjustment_time: float,
    cooldown_hours: float = 24.0,
    speed_change_min: float = 0.5,
    suggested_speed: Optional[float] = None,
    **kwargs,
) -> dict:
    """检查冷却条件是否满足。"""
    if suggested_speed is not None:
        speed_diff = abs(suggested_speed - (kwargs.get("current_speed", context.current_speed)))
        if speed_diff <= speed_change_min:
            return {"can_adjust": False, "reason": f"调整幅度{speed_diff:.1f}节小于最小幅度{speed_change_min}节"}
    time_since = context.sim_time - last_adjustment_time
    if time_since < cooldown_hours:
        return {"can_adjust": False, "reason": f"距上次调整仅{time_since:.1f}h，冷却需要{cooldown_hours}h"}
    return {"can_adjust": True, "reason": "冷却条件满足"}


def execute_calculate_optimal_speed(
    context: Optional[DecisionContext] = None,
    current_speed: float = 0,
    economic_speed: float = 0,
    design_speed: float = 0,
    delay_hours: float = 0,
    cii_ratio: float = 1.0,
    delay_critical: float = 48.0,
    delay_warning: float = 24.0,
    cii_critical: float = 1.35,
    cii_warning: float = 1.15,
    speed_boost_critical: float = 1.5,
    speed_boost_warning: float = 1.0,
    max_speed_pct: float = 0.92,
    cii_reduce_speed_pct: float = 0.95,
    eco_speed_over_economic: float = 1.0,
    target_arrival_time: Optional[float] = None,
    estimated_arrival_time: Optional[float] = None,
    **kwargs,
) -> dict:
    """
    核心：基于经验公式计算最优航速。

    从 context 中提取值（如果 context 提供且对应参数未显式传入）。
    """
    if context:
        current_speed = current_speed or context.current_speed
        economic_speed = economic_speed or context.economic_speed
        design_speed = design_speed or context.design_speed
        delay_hours = delay_hours or context.cumulative_delay
        cii_ratio = cii_ratio or context.cii_ratio

    suggested_speed = None
    reason = ""
    confidence = 0.8

    # 决策矩阵：优先级从高到低
    if delay_hours >= delay_critical:
        # 严重延误
        if cii_ratio >= cii_critical:
            suggested_speed = min(current_speed * 1.05, design_speed * max_speed_pct)
            reason = (
                f"严重延误{delay_hours:.0f}h但CII={cii_ratio:.2f}偏高，"
                f"轻微提速至{suggested_speed:.1f}节，兼顾减排与赶班"
            )
            confidence = 0.75
        else:
            suggested_speed = min(current_speed + speed_boost_critical, design_speed * max_speed_pct)
            reason = (
                f"严重延误{delay_hours:.0f}h，CII正常，"
                f"提速至{suggested_speed:.1f}节赶班"
            )
            confidence = 0.85

    elif delay_hours >= delay_warning:
        # 中度延误
        if cii_ratio >= cii_warning:
            suggested_speed = economic_speed * 1.0
            reason = (
                f"延误{delay_hours:.0f}h与CII={cii_ratio:.2f}均偏高，"
                f"保持经济航速{economic_speed}节"
            )
            confidence = 0.75
        else:
            suggested_speed = min(current_speed + speed_boost_warning, design_speed * max_speed_pct)
            reason = (
                f"中度延误{delay_hours:.0f}h，CII正常，"
                f"适度提速至{suggested_speed:.1f}节"
            )
            confidence = 0.8

    elif cii_ratio >= cii_critical:
        suggested_speed = economic_speed * cii_reduce_speed_pct
        reason = (
            f"CII={cii_ratio:.2f}偏高，延误{delay_hours:.0f}h尚可接受，"
            f"降速至{suggested_speed:.1f}节优化碳效率"
        )
        confidence = 0.85

    elif cii_ratio >= cii_warning and delay_hours < 12:
        suggested_speed = economic_speed * cii_reduce_speed_pct
        reason = (
            f"CII={cii_ratio:.2f}偏高，无严重延误，"
            f"微降速至{suggested_speed:.1f}节"
        )
        confidence = 0.8

    elif target_arrival_time is not None and estimated_arrival_time is not None:
        if estimated_arrival_time > target_arrival_time:
            max_allowed = min(economic_speed + speed_boost_warning, design_speed * max_speed_pct)
            suggested_speed = max_allowed
            reason = f"目标到港时间紧张，提速至{max_allowed:.1f}节赶班"
            confidence = 0.7

    return {
        "suggested_speed": suggested_speed,
        "reason": reason,
        "confidence": confidence,
    }


def execute_evaluate_tradeoff(
    delay_score: float = 0.0,
    cii_score: float = 0.0,
    fuel_score: float = 0.0,
    port_score: float = 0.0,
    delay_weight: float = 0.40,
    cii_weight: float = 0.20,
    fuel_weight: float = 0.20,
    port_weight: float = 0.20,
    **kwargs,
) -> dict:
    """多目标权衡评分。"""
    composite = (
        delay_weight * delay_score
        + cii_weight * cii_score
        + fuel_weight * fuel_score
        + port_weight * port_score
    )
    return {
        "composite_score": round(composite, 3),
        "details": {
            "delay": round(delay_score, 3),
            "cii": round(cii_score, 3),
            "fuel": round(fuel_score, 3),
            "port": round(port_score, 3),
        },
    }


def execute_adjust_speed(
    context: DecisionContext,
    new_speed: float,
    reason: str,
    confidence: float = 0.8,
    **kwargs,
) -> Optional[dict]:
    """生成航速调整决策（实际执行由 scheduler 负责）。"""
    if abs(new_speed - context.current_speed) <= 0.5:
        return None
    return {
        "decision_type": "speed_adjustment",
        "ship_id": context.ship_id,
        "suggested_action": "adjust_speed",
        "suggested_value": new_speed,
        "reason": reason,
        "confidence": confidence,
        "context": {
            "current_speed": context.current_speed,
            "economic_speed": context.economic_speed,
            "cii_ratio": context.cii_ratio,
            "cumulative_delay": context.cumulative_delay,
        },
    }


def execute_port_queue_info(context: DecisionContext, port_id: str = None, **kwargs) -> dict:
    """获取港口队列信息（注：仅返回 context 中已有的信息）。"""
    return {
        "note": "港口详细信息需要通过 query_port_status 工具获取",
        "next_port": context.next_port,
    }


# ======== 工具注册表 ========

TOOL_EXECUTORS = {
    "get_cii_status": execute_cii_status,
    "get_delay_info": execute_delay_info,
    "get_port_queue_info": execute_port_queue_info,
    "check_cooldown": execute_check_cooldown,
    "calculate_optimal_speed": execute_calculate_optimal_speed,
    "evaluate_tradeoff": execute_evaluate_tradeoff,
    "adjust_speed": execute_adjust_speed,
}


def execute_tool(tool_id: str, context: DecisionContext, tool_params: dict, **overrides) -> Any:
    """执行指定工具，返回执行结果。"""
    executor = TOOL_EXECUTORS.get(tool_id)
    if not executor:
        return {"error": f"未知工具: {tool_id}"}
    merged_params = dict(tool_params)
    merged_params.update(overrides)
    return executor(context=context, **merged_params)


def _get_cii_rating_from_ratio(ratio: float) -> str:
    """将 CII 比值映射到 A-E 评级。"""
    if ratio <= 0.85:
        return "A"
    elif ratio <= 1.00:
        return "B"
    elif ratio <= 1.15:
        return "C"
    elif ratio <= 1.35:
        return "D"
    return "E"
