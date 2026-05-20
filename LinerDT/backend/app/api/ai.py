from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json

from ..services.llm_adapter import (
    get_llm_adapter,
    get_llm_registry,
    LLMMessage,
)
from ..scheduler.scheduler import get_model
from ..ai.ai_integration import get_ai_integration
from ..ai.conversational_engine import get_conversational_engine
from ..ai.simulation_context import SimulationContext
from ..ai.decision_rules import get_decision_rule_service
from ..ai.enhanced_tools import (
    analyze_bottleneck,
    predict_delay_cascade,
    compare_ships,
    diagnose_ship,
    suggest_optimization,
)
from ..services.kpi_calculator import get_kpi_calculator
from ..core.config import settings, save_ai_config
from ..services import llm_adapter as llm_module

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []
    temperature: float = 0.7


class ConfigRequest(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


def _trace_delay_chain(model, start_port: str, max_depth: int = 3) -> str:
    """追踪延误传播链，委托给 enhanced_tools 中的统一实现。"""
    return predict_delay_cascade(model, start_port, max_depth)


async def execute_tool_call(tool_name: str, arguments: str) -> str:
    """执行工具调用并返回结果。"""
    try:
        args = json.loads(arguments) if arguments else {}
    except json.JSONDecodeError:
        return f"参数解析错误: {arguments}"

    model = get_model()

    # === 原有查询工具 ===

    if tool_name == "query_ship_status":
        agent = model.get_agent(args.get("ship_id", ""))
        if not agent or not hasattr(agent, "state"):
            return f"未找到船舶 {args.get('ship_id')}"
        ctx = SimulationContext(model)
        return ctx.build_detailed_ship_context(args["ship_id"])

    elif tool_name == "query_port_status":
        port = model.get_port(args.get("port_name", ""))
        if not port:
            return f"未找到港口 {args.get('port_name')}"
        ctx = SimulationContext(model)
        return ctx.build_detailed_port_context(args["port_name"])

    elif tool_name == "query_network_overview":
        ctx = SimulationContext(model)
        return ctx.build("")

    elif tool_name == "query_kpi_trend":
        kpi = get_kpi_calculator()
        trend = kpi.get_trend_data()
        return json.dumps({"trend": trend[-10:]}, indent=2, ensure_ascii=False)

    elif tool_name == "query_carbon_status":
        ship_id = args.get("ship_id")
        if ship_id:
            agent = model.get_agent(ship_id)
            if agent and hasattr(agent, "co2_emissions"):
                carbon = agent.get_carbon_stats()
                return json.dumps(
                    {
                        "ship_id": ship_id,
                        "name": agent.name,
                        "total_co2": agent.co2_emissions,
                        "cii_ratio": round(agent._get_cii_ratio(), 3),
                        "cii_rating": agent._cii_rating,
                        "carbon_stats": carbon,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
        return "未找到船舶碳排放信息"

    elif tool_name == "query_agent_decision":
        agent_id = args.get("agent_id")
        n = args.get("n", 10)
        if agent_id:
            agent = model.get_agent(agent_id)
            if agent and hasattr(agent, "decision_log"):
                return json.dumps(
                    {"agent_id": agent_id, "decisions": agent.decision_log[-n:]},
                    indent=2,
                    ensure_ascii=False,
                )
        return "未找到决策日志"

    elif tool_name == "query_delay_chain":
        return _trace_delay_chain(
            model, args.get("port_name", ""), args.get("max_depth", 3)
        )

    # === 原有修改工具 ===

    elif tool_name == "modify_ship_param":
        ai = get_ai_integration()
        ship_id = args.get("ship_id", "")
        params = args.get("params", {})
        if not ship_id or not params:
            return "缺少必要参数: ship_id 和 params"
        result = await ai.execute_tool(
            tool_name, {"ship_id": ship_id, "params": params}
        )
        return json.dumps(result, indent=2, ensure_ascii=False)

    elif tool_name == "modify_route_param":
        ai = get_ai_integration()
        route_id = args.get("route_id", "")
        params = args.get("params", {})
        if not route_id or not params:
            return "缺少必要参数: route_id 和 params"
        result = await ai.execute_tool(
            tool_name, {"route_id": route_id, "params": params}
        )
        return json.dumps(result, indent=2, ensure_ascii=False)

    elif tool_name == "save_snapshot":
        ai = get_ai_integration()
        result = await ai.execute_tool(tool_name, {"name": args.get("name", "default")})
        return json.dumps(result, indent=2, ensure_ascii=False)

    elif tool_name == "load_snapshot":
        ai = get_ai_integration()
        name = args.get("name", "")
        if not name:
            return "缺少必要参数: name"
        result = await ai.execute_tool(tool_name, {"name": name})
        return json.dumps(result, indent=2, ensure_ascii=False)

    elif tool_name == "rollback":
        ai = get_ai_integration()
        result = await ai.execute_tool(tool_name, {})
        return json.dumps(result, indent=2, ensure_ascii=False)

    elif tool_name == "compare_experiments":
        ai = get_ai_integration()
        result = await ai.execute_tool(
            tool_name,
            {
                "metric": args.get("metric", "on_time_rate"),
                "baseline": args.get("baseline"),
            },
        )
        return json.dumps(result, indent=2, ensure_ascii=False)

    # === 增强分析工具 ===

    elif tool_name == "analyze_bottleneck":
        return analyze_bottleneck(model)

    elif tool_name == "predict_delay_cascade":
        return predict_delay_cascade(
            model, args.get("port_name", ""), args.get("max_depth", 3)
        )

    elif tool_name == "compare_ships":
        return compare_ships(model, args.get("ship_ids", []))

    elif tool_name == "diagnose_ship":
        return diagnose_ship(model, args.get("ship_id", ""))

    elif tool_name == "suggest_optimization":
        return suggest_optimization(model, args.get("target", "all"))

    elif tool_name == "navigate_to":
        target_type = args.get("target_type", "")
        target_id = args.get("target_id", "")
        return json.dumps(
            {
                "action": "navigate",
                "target_type": target_type,
                "target_id": target_id,
                "message": f"导航到 {target_type}:{target_id}",
            },
            ensure_ascii=False,
        )

    else:
        return f"未知工具: {tool_name}"


async def generate_chat_response(
    message: str,
    history: List[Dict[str, str]],
    temperature: float,
):
    """流式生成对话响应，注入仿真上下文。"""
    llm = get_llm_adapter()
    registry = get_llm_registry()

    if not llm.is_configured():
        yield f"data: {json.dumps({'error': 'LLM 未配置，请先在设置中配置 API Key'})}\n\n"
        return

    # 使用对话引擎构建消息（注入仿真上下文）
    engine = get_conversational_engine()
    messages = engine.build_messages(message, history)

    tools = registry.get_tool_schemas()

    full_response = ""
    tool_call_mode = False
    tool_call_name = ""
    tool_call_arguments = ""

    # 第一轮：LLM 回复（可能触发工具调用）
    async for chunk in llm.chat(messages, temperature=temperature, stream=True):
        if chunk is None:
            continue

        if chunk.startswith("error:"):
            yield f"data: {json.dumps({'error': chunk[6:]})}\n\n"
            return

        if chunk.startswith("[TOOL_CALL:"):
            tool_call_mode = True
            content = chunk[11:-1]
            if "|" in content:
                parts = content.split("|", 1)
                tool_call_name = parts[0]
                tool_call_arguments = parts[1] if len(parts) > 1 else ""
            else:
                tool_call_name = content
                tool_call_arguments = ""
        else:
            full_response += chunk
            yield f"data: {json.dumps({'content': chunk})}\n\n"

    messages.append(LLMMessage(role="assistant", content=full_response or "[调用工具]"))

    # 如果触发了工具调用，执行并继续
    if tool_call_mode and tool_call_name:
        yield f"data: {json.dumps({'tool_start': tool_call_name})}\n\n"

        tool_result = await execute_tool_call(tool_call_name, tool_call_arguments)
        messages.append(
            LLMMessage(
                role="tool", content=f"工具 {tool_call_name} 执行结果:\n{tool_result}"
            )
        )

        # 特殊处理：navigate_to 的结果直接推送给前端
        if tool_call_name == "navigate_to":
            yield f"data: {json.dumps({'action': 'navigate', 'result': tool_result})}\n\n"

        yield f"data: {json.dumps({'tool_result': tool_result})}\n\n"

        # 第二轮：LLM 基于工具结果继续回复
        async for chunk in llm.chat(messages, temperature=temperature, stream=True):
            if chunk is None:
                continue
            if chunk.startswith("error:"):
                yield f"data: {json.dumps({'error': chunk[6:]})}\n\n"
                return
            if not chunk.startswith("[TOOL_CALL:"):
                yield f"data: {json.dumps({'content': chunk})}\n\n"

    yield "data: [DONE]\n\n"


@router.post("/chat")
async def chat(request: ChatRequest):
    """AI 对话端点 — 流式响应，注入仿真上下文。"""
    return StreamingResponse(
        generate_chat_response(
            message=request.message,
            history=request.history or [],
            temperature=request.temperature,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/config")
async def get_ai_config():
    llm = get_llm_adapter()
    return {
        "configured": llm.is_configured(),
        "base_url": llm.base_url,
        "model": llm.model,
    }


@router.post("/config")
async def update_ai_config(request: ConfigRequest):
    if request.api_key is not None:
        settings.openai_api_key = request.api_key
    if request.base_url is not None:
        settings.openai_base_url = request.base_url
    if request.model is not None:
        settings.openai_model = request.model

    # 持久化到本地文件
    save_ai_config()

    llm_module._llm_adapter = None

    llm = get_llm_adapter()
    return {
        "status": "ok",
        "configured": llm.is_configured(),
        "base_url": llm.base_url,
        "model": llm.model,
    }


@router.get("/tools")
async def list_tools():
    registry = get_llm_registry()
    return {"tools": registry.get_tool_schemas()}


# === 自然语言实验（保留） ===


class NLExperimentRequest(BaseModel):
    description: str
    default_duration_hours: float = 0


class NLExperimentResponse(BaseModel):
    success: bool
    experiment_config: Optional[Dict[str, Any]] = None
    validation_errors: Optional[List[str]] = None
    message: str


import re


def _parse_nl_to_experiment(description: str) -> Dict[str, Any]:
    description_lower = description.lower()
    config = {
        "name": "自然语言实验",
        "description": description,
        "control_params": {},
        "variants": [],
    }

    if "航速" in description or "速度" in description or "speed" in description_lower:
        speed_values = []
        if (
            "降低" in description
            or "降低" in description_lower
            or "减速" in description
        ):
            speed_match = re.search(r"(\d+)节", description)
            base_speed = int(speed_match.group(1)) if speed_match else 18
            speed_values = [base_speed, base_speed - 2]
            config["variants"] = [
                {"name": "控制组", "description": "保持原始航速设置", "params": {}},
                {
                    "name": "降速组",
                    "description": f"航速降至{speed_values[1]}节",
                    "params": {
                        "ship_params": {
                            "all": {
                                "current_speed": speed_values[1],
                                "economic_speed": speed_values[1],
                            }
                        }
                    },
                },
            ]
        elif "提高" in description or "提速" in description or "增加" in description:
            speed_match = re.search(r"(\d+)节", description)
            base_speed = int(speed_match.group(1)) if speed_match else 18
            speed_values = [base_speed, base_speed + 2]
            config["variants"] = [
                {"name": "控制组", "description": "保持原始航速设置", "params": {}},
                {
                    "name": "提速组",
                    "description": f"航速提高至{speed_values[1]}节",
                    "params": {
                        "ship_params": {"all": {"current_speed": speed_values[1]}}
                    },
                },
            ]

    if (
        "燃油" in description
        or "燃油价格" in description
        or "fuel" in description_lower
    ):
        price_factor = 1.5
        if "50%" in description:
            price_factor = 1.5
        elif "30%" in description:
            price_factor = 1.3
        elif "100%" in description:
            price_factor = 2.0
        config["variants"] = [
            {"name": "当前油价", "description": "使用当前油价", "params": {}},
            {
                "name": f"油价上涨{int((price_factor - 1) * 100)}%",
                "description": f"燃油价格上涨{int((price_factor - 1) * 100)}%",
                "params": {"global_params": {"fuel_price_multiplier": price_factor}},
            },
        ]

    if "拥堵" in description or "congestion" in description_lower:
        port_name = None
        if (
            "鹿特丹" in description
            or "rotterdam" in description_lower
            or "RTM" in description.upper()
        ):
            port_name = "RTM"
        elif (
            "新加坡" in description
            or "singapore" in description_lower
            or "SIN" in description.upper()
        ):
            port_name = "SIN"
        if port_name:
            config["variants"] = [
                {"name": "正常港口", "description": "港口正常运营", "params": {}},
                {
                    "name": f"{port_name}拥堵",
                    "description": f"{port_name}港口拥堵，泊位减少",
                    "params": {"port_params": {port_name: {"available_berths": 1}}},
                },
            ]

    if not config["variants"]:
        config["variants"] = [
            {"name": "控制组", "description": "默认参数", "params": {}},
            {
                "name": "实验组",
                "description": "修改参数",
                "params": {"ship_params": {"all": {"current_speed": 16}}},
            },
        ]

    return config


@router.post("/nl_experiment", response_model=NLExperimentResponse)
async def create_nl_experiment(request: NLExperimentRequest):
    try:
        config = _parse_nl_to_experiment(request.description)
        validation_errors = []
        if not config["variants"]:
            validation_errors.append("未能解析出有效的实验变体")
        if len(config["variants"]) < 2:
            validation_errors.append("实验至少需要2个变体（控制组和实验组）")
        if validation_errors:
            return NLExperimentResponse(
                success=False,
                validation_errors=validation_errors,
                message="实验配置解析失败",
            )
        return NLExperimentResponse(
            success=True, experiment_config=config, message="实验配置解析成功"
        )
    except Exception as e:
        return NLExperimentResponse(
            success=False, validation_errors=[str(e)], message="实验配置解析失败"
        )


# === 教学挑战（保留） ===


class TeachingChallenge(BaseModel):
    challenge_type: str
    description: str
    constraints: Dict[str, Any]
    success_criteria: Dict[str, Any]


class TeachChallengeRequest(BaseModel):
    topic: Optional[str] = None


class TeachChallengeResponse(BaseModel):
    success: bool
    challenge: Optional[TeachingChallenge] = None
    message: str


class TeachEvaluateRequest(BaseModel):
    challenge_type: str
    modifications: Dict[str, Any]
    baseline_metrics: Dict[str, float]


class TeachEvaluateResponse(BaseModel):
    success: bool
    score: float
    feedback: str
    suggestions: List[str]


TEACHING_CHALLENGES = {
    "speed_optimization": TeachingChallenge(
        challenge_type="speed_optimization",
        description="请调整各船舶航速，在确保准班率不低于70%的前提下，优化整体运营效率",
        constraints={"on_time_rate_min": 0.70},
        success_criteria={"on_time_rate": {"min": 0.70}, "avg_delay": {"max": 12}},
    ),
    "port_congestion": TeachingChallenge(
        challenge_type="port_congestion",
        description="鹿特丹港发生拥堵，请调整挂港顺序或航速，避免延误传播",
        constraints={"max_delay_hours": 24},
        success_criteria={
            "delay_propagation": {"max": 12},
            "on_time_rate": {"min": 0.70},
        },
    ),
    "fuel_cost": TeachingChallenge(
        challenge_type="fuel_cost",
        description="燃油价格上涨30%，请制定节省燃油的航行策略",
        constraints={"budget_increase_max": 0.15},
        success_criteria={
            "fuel_cost_reduction": {"min": 0.10},
            "on_time_rate": {"min": 0.70},
        },
    ),
    "schedule_recovery": TeachingChallenge(
        challenge_type="schedule_recovery",
        description="多艘船舶出现延误，请通过航速调整和港口调度恢复班期",
        constraints={"recovery_window_hours": 72},
        success_criteria={"on_time_rate": {"min": 0.75}, "avg_delay": {"max": 8}},
    ),
}


@router.post("/teach_challenge", response_model=TeachChallengeResponse)
async def create_teaching_challenge(request: TeachChallengeRequest):
    topic = request.topic or "speed_optimization"
    if topic not in TEACHING_CHALLENGES:
        available = list(TEACHING_CHALLENGES.keys())
        return TeachChallengeResponse(
            success=False,
            message=f"未知主题: {topic}。可用主题: {', '.join(available)}",
        )
    challenge = TEACHING_CHALLENGES[topic]
    return TeachChallengeResponse(
        success=True, challenge=challenge, message=f"挑战主题: {challenge.description}"
    )


@router.post("/teach_evaluate", response_model=TeachEvaluateResponse)
async def evaluate_student_solution(request: TeachEvaluateRequest):
    challenge_type = request.challenge_type
    modifications = request.modifications
    baseline_metrics = request.baseline_metrics

    if challenge_type not in TEACHING_CHALLENGES:
        return TeachEvaluateResponse(
            success=False, score=0.0, feedback="未知挑战类型", suggestions=[]
        )

    challenge = TEACHING_CHALLENGES[challenge_type]
    score = 0.0
    feedback_parts = []
    suggestions = []

    if challenge_type == "speed_optimization":
        on_time_rate = baseline_metrics.get("on_time_rate", 0)
        avg_delay = baseline_metrics.get("avg_delay", 0)
        if on_time_rate >= 0.70:
            score += 50.0
            feedback_parts.append(f"✓ 准班率达标: {on_time_rate * 100:.1f}%")
        else:
            feedback_parts.append(
                f"✗ 准班率未达标: {on_time_rate * 100:.1f}% (需要≥70%)"
            )
            suggestions.append("适当提高航速以改善准班率")
        if avg_delay <= 12:
            score += 50.0
            feedback_parts.append(f"✓ 平均延误控制良好: {avg_delay:.1f}h")
        else:
            feedback_parts.append(f"✗ 平均延误偏高: {avg_delay:.1f}h")
            suggestions.append("优化港口停留时间或调整航速")

    elif challenge_type == "port_congestion":
        delay_hours = baseline_metrics.get("max_delay", 0)
        on_time_rate = baseline_metrics.get("on_time_rate", 0)
        if delay_hours <= 24:
            score += 50.0
            feedback_parts.append(f"✓ 延误控制良好: 最大延误{delay_hours:.1f}小时")
        else:
            feedback_parts.append(f"✗ 延误超出限制: {delay_hours:.1f}小时")
            suggestions.append("考虑调整航线顺序或提前加速")
        if on_time_rate >= 0.70:
            score += 50.0
            feedback_parts.append(f"✓ 准班率可接受: {on_time_rate * 100:.1f}%")

    elif challenge_type == "schedule_recovery":
        on_time_rate = baseline_metrics.get("on_time_rate", 0)
        avg_delay = baseline_metrics.get("avg_delay", 0)
        if on_time_rate >= 0.75:
            score += 50.0
            feedback_parts.append(f"✓ 准班率恢复良好: {on_time_rate * 100:.1f}%")
        else:
            feedback_parts.append(f"✗ 准班率仍需改善: {on_time_rate * 100:.1f}%")
            suggestions.append("进一步提速或调整挂港计划")
        if avg_delay <= 8:
            score += 50.0
            feedback_parts.append(f"✓ 平均延误已控制在 {avg_delay:.1f}h")
        else:
            feedback_parts.append(f"✗ 平均延误仍有 {avg_delay:.1f}h")
            suggestions.append("考虑调整后续港口顺序减少等待时间")

    elif challenge_type == "fuel_cost":
        fuel_cost_change = baseline_metrics.get("fuel_cost_change", 0)
        if fuel_cost_change <= 0.15:
            score += 50.0
            feedback_parts.append(f"✓ 燃油成本控制: {fuel_cost_change * 100:.1f}%增幅")
        else:
            feedback_parts.append(f"✗ 燃油成本增幅过大: {fuel_cost_change * 100:.1f}%")
            suggestions.append("降低航速是最有效的燃油节省策略")
        on_time_rate = baseline_metrics.get("on_time_rate", 0)
        if on_time_rate >= 0.70:
            score += 50.0
            feedback_parts.append(f"✓ 准班率保持良好: {on_time_rate * 100:.1f}%")

    feedback = "\n".join(feedback_parts) if feedback_parts else "评估完成"
    return TeachEvaluateResponse(
        success=True,
        score=min(100.0, max(0.0, score)),
        feedback=feedback,
        suggestions=suggestions,
    )


# === Agent 配置 API（替代旧的决策规则 API） ===


@router.get("/agents")
async def list_agent_configs():
    """获取所有 agent 配置。"""
    ai = get_ai_integration()
    configs = ai.get_agent_configs()
    return {
        "agents": configs,
        "total": len(configs),
    }


@router.get("/agents/{config_id}")
async def get_agent_config(config_id: str):
    """获取单个 agent 配置。"""
    from ..ai.agent_config import get_agent_config_service

    config = get_agent_config_service().get(config_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Agent 配置 {config_id} 不存在")
    return config.model_dump()


class AgentUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    decision_mode: Optional[str] = None
    system_prompt: Optional[str] = None
    parameters: Optional[Dict[str, float]] = None
    tools: Optional[List[Dict[str, Any]]] = None


@router.put("/agents/{config_id}")
async def update_agent_config(config_id: str, body: AgentUpdateRequest):
    """更新 agent 配置（prompt / tools / params / mode）。"""
    ai = get_ai_integration()
    updates = {}
    if body.enabled is not None:
        updates["enabled"] = body.enabled
    if body.decision_mode is not None:
        updates["decision_mode"] = body.decision_mode
    if body.system_prompt is not None:
        updates["system_prompt"] = body.system_prompt
    if body.parameters is not None:
        updates["parameters"] = body.parameters
    if body.tools is not None:
        updates["tools"] = body.tools

    result = ai.update_agent_config(config_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail=f"Agent 配置 {config_id} 不存在")
    return result


@router.post("/agents/reset")
async def reset_agent_configs():
    """重置所有 agent 配置为默认值。"""
    from ..ai.agent_config import get_agent_config_service

    svc = get_agent_config_service()
    configs = svc.reset_to_defaults()

    # 重新注册 agent
    from ..ai.decision_agent import DecisionAgent

    ai = get_ai_integration()
    for config in configs:
        ai.register_ai_agent(config.id, DecisionAgent(config))
    if "balanced_agent" in ai.ai_agents:
        ai.register_ai_agent("primary", ai.ai_agents["balanced_agent"])

    return {
        "agents": [c.model_dump() for c in configs],
        "message": "已重置为默认 Agent 配置",
    }


class DecideRequest(BaseModel):
    target_arrival_time: Optional[float] = None


@router.post("/agents/{config_id}/decide")
async def trigger_agent_decision(
    config_id: str, body: DecideRequest, ship_id: str = ""
):
    """手动触发 agent 决策（用于调试 / 按需决策）。"""
    from ..ai.agent_config import get_agent_config_service
    from ..ai.decision_agent import DecisionAgent
    from ..ai.base_agent import DecisionContext

    config = get_agent_config_service().get(config_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Agent 配置 {config_id} 不存在")

    # 如果没有指定 ship_id，取仿真中第一艘船
    if not ship_id:
        model = get_model()
        ships = model.get_all_ships()
        if not ships:
            raise HTTPException(status_code=400, detail="仿真中没有船舶")
        ship_id = next(iter(ships.keys()))

    agent_ship = get_model().get_agent(ship_id)
    if not agent_ship:
        raise HTTPException(status_code=404, detail=f"船舶 {ship_id} 不存在")

    context = DecisionContext(
        ship_id=agent_ship.unique_id,
        ship_name=getattr(agent_ship, "name", ship_id),
        current_speed=getattr(agent_ship, "current_speed", 0),
        economic_speed=getattr(agent_ship, "economic_speed", 18),
        design_speed=getattr(agent_ship, "design_speed", 22),
        current_state=str(getattr(agent_ship, "state", "UNKNOWN")),
        current_port=getattr(agent_ship, "current_port", None),
        next_port=getattr(agent_ship, "next_port", None),
        lat=getattr(agent_ship, "lat", None),
        lon=getattr(agent_ship, "lon", None),
        cumulative_delay=getattr(agent_ship, "cumulative_delay", 0),
        cii_ratio=getattr(agent_ship, "_get_cii_ratio", lambda: 1.0)(),
        co2_emissions=getattr(agent_ship, "co2_emissions", 0),
        capacity_teu=getattr(agent_ship, "capacity_teu", 20000),
        sim_time=get_model().current_time,
        route=get_model().get_route_for_ship(ship_id),
    )

    agent = DecisionAgent(config)
    decision = agent.evaluate_speed(context, body.target_arrival_time)
    if decision is None:
        return {"decision": None, "message": "Agent 决定不做调整"}
    return {
        "decision": {
            "type": decision.decision_type.value,
            "ship_id": decision.ship_id,
            "action": decision.suggested_action,
            "value": decision.suggested_value,
            "reason": decision.reason,
            "confidence": decision.confidence,
        }
    }


# === 旧决策规则 API（保留向后兼容） ===


class RuleUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    params: Optional[Dict[str, float]] = None


@router.get("/rules")
async def list_rules():
    """获取所有可编辑决策规则（含参数详情）。"""
    service = get_decision_rule_service()
    rules = service.get_all_rules()
    return {
        "rules": [rule.model_dump() for rule in rules],
        "total": len(rules),
    }


@router.get("/rules/{rule_id}")
async def get_rule(rule_id: str):
    """获取单条规则详情。"""
    service = get_decision_rule_service()
    rule = service.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")
    return rule.model_dump()


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, body: RuleUpdateRequest):
    """更新规则（启用/禁用、调整参数值）。"""
    service = get_decision_rule_service()
    updates = {}
    if body.enabled is not None:
        updates["enabled"] = body.enabled
    if body.params is not None:
        updates["params"] = body.params
    rule = service.update_rule(rule_id, updates)
    if not rule:
        raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")
    return rule.model_dump()


@router.post("/rules/reset")
async def reset_rules():
    """重置所有规则为出厂默认值。"""
    service = get_decision_rule_service()
    rules = service.reset_to_defaults()
    return {
        "rules": [rule.model_dump() for rule in rules],
        "message": "已重置为默认规则",
    }
