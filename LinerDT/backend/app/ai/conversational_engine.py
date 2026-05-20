"""
对话引擎 — 多智能体路由与对话管理。

将用户输入路由到合适的"虚拟智能体"行为模式：
- Observer: 状态查询、异常检测
- Analyst: 根因分析、What-if、策略对比
- Controller: 执行操作（改参数、调速、实验）
- Teacher: 概念解释（DES原理、KPI体系、ECA规则）
"""

from typing import Optional, List, Dict, Any, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum

from .simulation_context import SimulationContext


class IntentCategory(str, Enum):
    QUERY = "query"         # 查询状态
    ANALYSIS = "analysis"   # 深度分析
    CONTROL = "control"     # 执行操作
    TEACHING = "teaching"   # 概念教学
    WHAT_IF = "what_if"     # 假设推演
    GENERAL = "general"     # 一般对话


@dataclass
class ConversationTurn:
    role: str
    content: str
    intent: Optional[IntentCategory] = None
    tool_calls: List[Dict] = field(default_factory=list)


SYSTEM_PROMPT_TEMPLATE = """你是 LinerDT（班轮航运数字孪生仿真平台）的 AI 运营助手。

## 你的身份
你是航运运营团队的智能助手，可以：
1. **查询与监控**：查看船舶状态、港口情况、KPI指标（准班率、延误、碳排放等）
2. **分析与诊断**：解释延误原因、检测系统瓶颈、对比运营策略
3. **决策与控制**：调整航速、修改参数、创建A/B实验
4. **教学与解释**：讲解DES仿真原理、KPI体系、ECA区域规则

## 交互原则
- 用简洁专业的航运术语回答
- 当发现异常（高延误、港口拥堵、CII超标）时主动提醒
- 提出具体、可执行的建议（如"建议将 S003 航速降至 18 节"）
- 执行修改操作前，简要说明预期影响
- 使用工具获取实时数据，不要猜测

## 航运知识
- ECA (Emission Control Areas): 北海和华南沿海须切换MGO低硫油
- VLSFO/MGO: 低硫燃油/船用轻柴油，CO2因子分别为3.114和3.206
- DES/DEVS: 离散事件仿真，事件驱动的时序推进机制
- KPI: 准班率、平均延误、碳排放、CII评级等多维度指标

{simulation_context}

当前对话中，请基于上面的仿真状态信息与用户交流。"""


class ConversationalEngine:
    """对话引擎 — 管理 LLM 对话的意图路由和上下文注入。"""

    def __init__(self, model):
        self.model = model
        self.ctx_builder = SimulationContext(model)

    def classify_intent(self, message: str) -> IntentCategory:
        """快速关键字意图分类（备选方案，实际由 LLM 自行判断）。"""
        msg_lower = message.lower()

        # What-if 场景
        wh_if_keywords = ["如果", "假设", "假如", "要是", "what if", "会怎样", "会怎么样",
                          "改成", "调整到", "降低到", "提高到"]
        if any(kw in msg_lower for kw in wh_if_keywords):
            return IntentCategory.WHAT_IF

        # 控制操作
        control_keywords = ["调速", "改航速", "改参数", "修改", "设置",
                           "回滚", "保存快照", "实验", "开始实验",
                           "modify", "set speed", "change"]
        if any(kw in msg_lower for kw in control_keywords):
            return IntentCategory.CONTROL

        # 分析
        analysis_keywords = ["为什么", "原因", "分析", "诊断", "瓶颈",
                            "影响", "导致", "趋势", "对比", "比较",
                            "why", "analyze", "compare", "diagnose"]
        if any(kw in msg_lower for kw in analysis_keywords):
            return IntentCategory.ANALYSIS

        # 教学
        teaching_keywords = ["是什么", "什么是", "解释", "讲解", "介绍",
                            "原理", "概念", "定义", "cia", "eca",
                            "cii", "devs", "des"]
        if any(kw in msg_lower for kw in teaching_keywords):
            return IntentCategory.TEACHING

        return IntentCategory.QUERY

    def build_system_prompt(self, user_message: str = "") -> str:
        """构建包含仿真上下文的完整 system prompt。"""
        sim_ctx = self.ctx_builder.build(user_message)
        return SYSTEM_PROMPT_TEMPLATE.format(simulation_context=sim_ctx)

    def build_messages(
        self,
        user_message: str,
        history: List[Dict[str, str]],
    ) -> List:
        """构建发送给 LLM 的完整消息列表。"""
        from app.services.llm_adapter import LLMMessage

        messages = []
        messages.append(LLMMessage(
            role="system",
            content=self.build_system_prompt(user_message)
        ))

        # 添加历史（最近10轮，20条消息）
        for h in history[-20:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role in ("user", "assistant", "tool"):
                messages.append(LLMMessage(role=role, content=content))

        messages.append(LLMMessage(role="user", content=user_message))
        return messages

    def get_detail_context(self, target_type: str, target_id: str) -> str:
        """获取特定目标的详细上下文（用于用户询问特定船舶/港口时）。"""
        if target_type == "ship":
            return self.ctx_builder.build_detailed_ship_context(target_id)
        elif target_type == "port":
            return self.ctx_builder.build_detailed_port_context(target_id)
        return ""


def get_conversational_engine(model=None) -> ConversationalEngine:
    """获取对话引擎单例。"""
    if model is None:
        from app.scheduler.scheduler import get_model
        model = get_model()
    return ConversationalEngine(model)
