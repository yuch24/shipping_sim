"""
AgentTypeRegistry — 集中注册所有可用 Agent 类型。
为前端 Agent 创建面板提供元数据，模仿 AnyLogic 的 Agent Palette。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional, Type


@dataclass
class AgentTypeEntry:
    """单个 Agent 类型的元数据。"""
    type_name: str
    label: str
    description: str
    category: str           # "agent" | "population" | "model"
    icon: str               # emoji 图标
    parameters: list[dict]  # 序列化的参数定义
    is_population_compatible: bool = True

    def to_dict(self) -> dict:
        return {
            "type_name": self.type_name,
            "label": self.label,
            "description": self.description,
            "category": self.category,
            "icon": self.icon,
            "parameters": self.parameters,
            "is_population_compatible": self.is_population_compatible,
        }


class AgentTypeRegistry:
    """
    Agent 类型注册表单例。
    前端 GET /api/sim/tree/types → 显示可创建的 agent 类型面板。
    """

    _instance: Optional["AgentTypeRegistry"] = None

    def __init__(self):
        self._types: dict[str, AgentTypeEntry] = {}

    @classmethod
    def get_instance(cls) -> "AgentTypeRegistry":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._init_defaults()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """测试用：重置单例。"""
        cls._instance = None

    def register(self, entry: AgentTypeEntry) -> None:
        self._types[entry.type_name] = entry

    def get_type(self, type_name: str) -> Optional[AgentTypeEntry]:
        return self._types.get(type_name)

    def get_all_types(self) -> list[AgentTypeEntry]:
        return list(self._types.values())

    def _init_defaults(self) -> None:
        """延迟导入注册所有具体 Agent 类型，避免循环依赖。"""
        from ..scheduler.scheduler import ShipAgent, PortAgent, CraneAgent

        self.register(AgentTypeEntry(
            type_name="ShipAgent",
            label="船舶",
            description="集装箱船仿真实体，具备航速决策、CII 追踪、延误管理能力",
            category="agent",
            icon="🚢",
            parameters=self._collect_params(ShipAgent),
            is_population_compatible=True,
        ))

        self.register(AgentTypeEntry(
            type_name="PortAgent",
            label="港口",
            description="港口仿真实体，管理泊位分配、装卸作业和岸桥调度",
            category="agent",
            icon="⚓",
            parameters=self._collect_params(PortAgent),
            is_population_compatible=True,
        ))

        self.register(AgentTypeEntry(
            type_name="CraneAgent",
            label="岸桥",
            description="港口岸桥仿真实体，处理集装箱装卸作业",
            category="agent",
            icon="🏗️",
            parameters=self._collect_params(CraneAgent),
            is_population_compatible=True,
        ))

    @staticmethod
    def _collect_params(cls: Type) -> list[dict]:
        """统一收集参数元数据，兼容新旧两种格式 (Parameter / ParameterDef)。"""
        # 新格式：tree.Parameter
        if hasattr(cls, 'get_parameters'):
            params = cls.get_parameters()
            if params:
                return [p.to_dict() for p in params]

        # 旧格式：schema.ParameterDef
        if hasattr(cls, 'get_parameter_defs'):
            defs = cls.get_parameter_defs()
            if defs:
                return [d.to_dict() for d in defs]

        return []
