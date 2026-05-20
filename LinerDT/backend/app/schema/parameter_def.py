"""Agent 参数声明系统 — 模仿 AnyLogic 的参数元数据模式。"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional


class ParamType(str, Enum):
    STRING = "string"
    FLOAT = "float"
    INT = "int"
    BOOL = "bool"
    ENUM = "enum"
    DISTRIBUTION = "distribution"


@dataclass
class ParameterDef:
    """单个参数的定义元数据。"""
    key: str
    label: str
    type: ParamType
    default: Any = None
    description: str = ""
    unit: str = ""
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    step: Optional[float] = None
    options: list[dict] = field(default_factory=lambda: [])
    """options: 仅 ENUM 类型使用，格式 [{"label": "...", "value": "..."}]"""

    # 嵌套子参数（用于 Distribution 类型的具体参数）
    children: list["ParameterDef"] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {
            "key": self.key,
            "label": self.label,
            "type": self.type.value,
            "default": self.default,
            "description": self.description,
        }
        if self.unit:
            d["unit"] = self.unit
        if self.min_val is not None:
            d["min"] = self.min_val
        if self.max_val is not None:
            d["max"] = self.max_val
        if self.step is not None:
            d["step"] = self.step
        if self.options:
            d["options"] = self.options
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


def param_group(key: str, label: str, children: list[ParameterDef]) -> ParameterDef:
    """便捷函数：创建一个分组（用于树形结构的非叶节点）。"""
    return ParameterDef(key=key, label=label, type=ParamType.STRING, children=children)
