from typing import Optional, Dict, Any, AsyncIterator, List
import json
import asyncio
import threading
from dataclasses import dataclass
from ..core.config import settings


@dataclass
class LLMMessage:
    role: str
    content: str


@dataclass
class LLMFunction:
    name: str
    description: str
    parameters: Dict[str, Any]


class LLMAdapter:
    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        api_key: str = "",
        model: str = "gpt-4",
        timeout: float = 60.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def is_configured(self) -> bool:
        return bool(self.api_key and self.base_url)

    async def chat(
        self,
        messages: List[LLMMessage],
        functions: Optional[List[LLMFunction]] = None,
        temperature: float = 0.7,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        import aiohttp

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": stream,
        }

        if functions:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": f.name,
                        "description": f.description,
                        "parameters": f.parameters,
                    }
                }
                for f in functions
            ]

        url = f"{self.base_url}/chat/completions"

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        yield f"error:HTTP {response.status}: {error_text}"
                        return

                    if stream:
                        tool_call_buffer = {"name": "", "arguments": ""}
                        in_tool_call = False

                        async for line in response.content:
                            line = line.decode("utf-8").strip()
                            if not line:
                                continue
                            if line.startswith("data: "):
                                line = line[6:]
                            if line == "[DONE]":
                                break
                            try:
                                data = json.loads(line)
                                delta = data.get("choices", [{}])[0].get("delta", {})

                                if "content" in delta and delta["content"] is not None:
                                    if in_tool_call:
                                        tool_call_buffer["arguments"] += delta["content"]
                                    else:
                                        yield delta["content"]

                                # 中间 chunk 中捕获 tool call 名称和参数
                                tc_list = delta.get("tool_calls")
                                if tc_list:
                                    for tc in tc_list:
                                        fn = tc.get("function", {})
                                        if fn.get("name"):
                                            tool_call_buffer["name"] = fn["name"]
                                        if fn.get("arguments"):
                                            tool_call_buffer["arguments"] += fn["arguments"]

                                choice = data.get("choices", [{}])[0]
                                finish = choice.get("finish_reason")
                                if finish == "tool_calls" and tool_call_buffer["name"]:
                                    yield f"[TOOL_CALL:{tool_call_buffer['name']}|{tool_call_buffer['arguments']}]"
                                    in_tool_call = True

                            except json.JSONDecodeError:
                                continue
                    else:
                        data = await response.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        yield content
        except asyncio.TimeoutError:
            yield "error:Request timeout"
        except Exception as e:
            yield f"error:{str(e)}"

    async def chat_with_function_call(
        self,
        messages: List[LLMMessage],
        functions: List[LLMFunction],
    ) -> Dict[str, Any]:
        import aiohttp

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": f.name,
                        "description": f.description,
                        "parameters": f.parameters,
                    }
                }
                for f in functions
            ],
            "tool_choice": "auto",
        }

        url = f"{self.base_url}/chat/completions"

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return {"error": f"HTTP {response.status}: {error_text}"}

                data = await response.json()
                message = data.get("choices", [{}])[0].get("message", {})

                result = {
                    "content": message.get("content", ""),
                    "tool_calls": [],
                }

                if "tool_calls" in message:
                    for tc in message["tool_calls"]:
                        result["tool_calls"].append({
                            "id": tc.get("id", ""),
                            "name": tc.get("function", {}).get("name", ""),
                            "arguments": tc.get("function", {}).get("arguments", ""),
                        })

                return result


class LLMFunctionRegistry:
    def __init__(self):
        self._functions: Dict[str, LLMFunction] = {}

    def register(self, function: LLMFunction) -> None:
        self._functions[function.name] = function

    def get(self, name: str) -> Optional[LLMFunction]:
        return self._functions.get(name)

    def list_all(self) -> List[LLMFunction]:
        return list(self._functions.values())

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": f.name,
                    "description": f.description,
                    "parameters": f.parameters,
                }
            }
            for f in self._functions.values()
        ]


_llm_adapter_lock: threading.Lock = threading.Lock()
_llm_registry_lock: threading.Lock = threading.Lock()
_llm_adapter: Optional[LLMAdapter] = None
_llm_registry: Optional[LLMFunctionRegistry] = None


def get_llm_adapter() -> LLMAdapter:
    global _llm_adapter
    if _llm_adapter is None:
        with _llm_adapter_lock:
            if _llm_adapter is None:
                _llm_adapter = LLMAdapter(
                    base_url=settings.openai_base_url,
                    api_key=settings.openai_api_key,
                    model=settings.openai_model,
                )
    return _llm_adapter


def get_llm_registry() -> LLMFunctionRegistry:
    global _llm_registry
    if _llm_registry is None:
        with _llm_registry_lock:
            if _llm_registry is None:
                _llm_registry = LLMFunctionRegistry()
                _register_default_tools(_llm_registry)
    return _llm_registry


def _register_default_tools(registry: LLMFunctionRegistry) -> None:
    registry.register(LLMFunction(
        name="query_ship_status",
        description="查询指定船舶的当前状态、位置、航速等信息",
        parameters={
            "type": "object",
            "properties": {
                "ship_id": {"type": "string", "description": "船舶ID，如 s001, s002 等"},
            },
            "required": ["ship_id"],
        },
    ))

    registry.register(LLMFunction(
        name="query_port_status",
        description="查询指定港口的当前状态、泊位占用情况、排队船舶数量",
        parameters={
            "type": "object",
            "properties": {
                "port_name": {"type": "string", "description": "港口名称或ID，如 SHA, SIN, RTM 等"},
            },
            "required": ["port_name"],
        },
    ))

    registry.register(LLMFunction(
        name="query_network_overview",
        description="查询全局概览，包括所有船舶状态、港口状态、当前仿真时间等",
        parameters={"type": "object", "properties": {}},
    ))

    registry.register(LLMFunction(
        name="query_kpi_trend",
        description="查询KPI趋势数据，包括准班率、碳排放等指标的历史变化",
        parameters={
            "type": "object",
            "properties": {
                "metric": {"type": "string", "description": "指标名称，如 on_time_rate, carbon_total 等"},
            },
        },
    ))

    registry.register(LLMFunction(
        name="query_carbon_status",
        description="查询船舶或航线的碳排放状态",
        parameters={
            "type": "object",
            "properties": {
                "ship_id": {"type": "string", "description": "船舶ID"},
                "route_id": {"type": "string", "description": "航线ID"},
            },
        },
    ))

    registry.register(LLMFunction(
        name="query_agent_decision",
        description="查询Agent的决策日志，了解AI做出的决策及原因",
        parameters={
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID"},
                "n": {"type": "integer", "description": "返回最近N条决策", "default": 10},
            },
        },
    ))

    registry.register(LLMFunction(
        name="query_delay_chain",
        description="追踪延误在港口间的传播链，分析延误如何从一个港口传播到另一个港口",
        parameters={
            "type": "object",
            "properties": {
                "port_name": {"type": "string", "description": "起始港口名称或ID，如 RTM(鹿特丹)、SIN(新加坡)等"},
                "max_depth": {"type": "integer", "description": "最大追踪深度，默认为3", "default": 3},
            },
            "required": ["port_name"],
        },
    ))

    registry.register(LLMFunction(
        name="modify_ship_param",
        description="修改船舶运行参数（破坏性操作，需要确认）",
        parameters={
            "type": "object",
            "properties": {
                "ship_id": {"type": "string", "description": "船舶ID"},
                "params": {
                    "type": "object",
                    "description": "要修改的参数，如 current_speed, economic_speed 等",
                    "properties": {
                        "current_speed": {"type": "number", "description": "当前航速 (1-25节)"},
                        "economic_speed": {"type": "number", "description": "经济航速 (10-22节)"},
                        "design_speed": {"type": "number", "description": "设计航速 (15-28节)"},
                    },
                },
            },
            "required": ["ship_id", "params"],
        },
    ))

    registry.register(LLMFunction(
        name="modify_route_param",
        description="修改航线参数（破坏性操作，需要确认）",
        parameters={
            "type": "object",
            "properties": {
                "route_id": {"type": "string", "description": "航线ID"},
                "params": {
                    "type": "object",
                    "description": "要修改的参数",
                    "properties": {
                        "speed_multiplier": {"type": "number", "description": "航速倍数 (0.5-2.0)"},
                        "delay_factor": {"type": "number", "description": "延误因子 (0.0-3.0)"},
                    },
                },
            },
            "required": ["route_id", "params"],
        },
    ))

    registry.register(LLMFunction(
        name="save_snapshot",
        description="保存当前仿真快照",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "快照名称"},
            },
        },
    ))

    registry.register(LLMFunction(
        name="load_snapshot",
        description="加载指定快照恢复仿真状态",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "快照名称"},
            },
            "required": ["name"],
        },
    ))

    registry.register(LLMFunction(
        name="rollback",
        description="回滚到修改前的状态（破坏性操作）",
        parameters={
            "type": "object",
            "properties": {},
        },
    ))

    registry.register(LLMFunction(
        name="compare_experiments",
        description="对比两组实验结果",
        parameters={
            "type": "object",
            "properties": {
                "metric": {"type": "string", "description": "对比指标，如 on_time_rate, total_co2 等"},
                "baseline": {"type": "string", "description": "基线实验名称"},
            },
        },
    ))

    # === 增强分析工具 ===

    registry.register(LLMFunction(
        name="analyze_bottleneck",
        description="分析当前仿真的系统瓶颈，包括拥堵港口、问题船舶，并给出改进建议",
        parameters={"type": "object", "properties": {}},
    ))

    registry.register(LLMFunction(
        name="predict_delay_cascade",
        description="预测延误从某个港口开始的传播链，分析会影响哪些下游船舶和港口",
        parameters={
            "type": "object",
            "properties": {
                "port_name": {"type": "string", "description": "起始港口名称或ID"},
                "max_depth": {"type": "integer", "description": "最大追踪深度，默认3", "default": 3},
            },
            "required": ["port_name"],
        },
    ))

    registry.register(LLMFunction(
        name="compare_ships",
        description="对比多艘船舶的各项指标（航速、CII、延误、碳排放）",
        parameters={
            "type": "object",
            "properties": {
                "ship_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要对比的船舶ID列表，如 ['s001', 's002', 's003']",
                },
            },
            "required": ["ship_ids"],
        },
    ))

    registry.register(LLMFunction(
        name="diagnose_ship",
        description="对某艘船进行深度诊断，分析其延误、运营效率、航速策略等问题并给出建议",
        parameters={
            "type": "object",
            "properties": {
                "ship_id": {"type": "string", "description": "船舶ID，如 s001"},
            },
            "required": ["ship_id"],
        },
    ))

    registry.register(LLMFunction(
        name="suggest_optimization",
        description="基于当前仿真状态，自动生成航速优化及延误恢复建议",
        parameters={
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "目标船舶ID，或 'all' 表示所有船舶", "default": "all"},
            },
        },
    ))

    registry.register(LLMFunction(
        name="navigate_to",
        description="将用户视角导航到指定船舶或港口的位置（前端镜头跳转）",
        parameters={
            "type": "object",
            "properties": {
                "target_type": {"type": "string", "description": "目标类型：ship 或 port"},
                "target_id": {"type": "string", "description": "目标ID，如 s001 或 SHA"},
            },
            "required": ["target_type", "target_id"],
        },
    ))
