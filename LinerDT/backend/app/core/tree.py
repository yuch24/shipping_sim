"""
树形 Agent 框架 — ActiveObject / Agent 基类
模仿 AnyLogic 的层次化对象组织方式。

核心概念：
  ActiveObject  = 一切可嵌入树中的节点（AnyLogic 里叫 ActiveObject）
  Agent         = 拥有参数+生命周期钩子+状态图 的 ActiveObject
  AgentType     = Agent 的类实例化配置（类似 Population 的模板）

树形导航：
  - get_owner()       → 父节点
  - get_embedded()    → 所有直接子节点 {name: obj}
  - get_full_path()   → "main.model.ports.SHA.cranes.crane_1"
  - resolve(path)     → 从当前节点按路径查找子节点
  - embed(child, name) → 将 child 嵌入到当前节点下
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
from typing import Any, ClassVar, Optional, Type, TYPE_CHECKING
from enum import Enum, auto
import threading

if TYPE_CHECKING:
    from .scheduler import EventDrivenScheduler


# ═══════════════════════════════════════════════════════════════════
# 参数系统
# ═══════════════════════════════════════════════════════════════════


class ParamType(str, Enum):
    STRING = "string"
    FLOAT = "float"
    INT = "int"
    BOOL = "bool"
    ENUM = "enum"
    DISTRIBUTION = "distribution"


@dataclass
class Parameter:
    """单个参数声明。挂在 Agent 类上，描述该类的可配置属性。"""

    key: str
    label: str = ""
    type: ParamType = ParamType.FLOAT
    default: Any = None
    description: str = ""
    unit: str = ""
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    step: Optional[float] = None
    options: list[dict] = field(default_factory=list)

    # 非叶子节点：子参数（递归分组用）
    children: list["Parameter"] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {
            "key": self.key,
            "label": self.label or self.key,
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

    @staticmethod
    def group(key: str, label: str, *children: "Parameter") -> "Parameter":
        """快捷创建参数分组。"""
        return Parameter(
            key=key, label=label, type=ParamType.STRING, children=list(children)
        )


# ═══════════════════════════════════════════════════════════════════
# 树节点基类
# ═══════════════════════════════════════════════════════════════════


class ActiveObject(ABC):
    """
    树形结构的基类。AnyLogic 里一切皆 ActiveObject，所有节点都能：
    - 知道自己属于谁     (owner)
    - 知道嵌入了谁       (embedded)
    - 树形路径导航       (get_full_path / resolve)
    """

    _object_counter: ClassVar[int] = 0

    def __init__(self, owner: Optional["ActiveObject"] = None):
        self._owner: Optional["ActiveObject"] = None
        self._embedded: dict[str, "ActiveObject"] = {}
        # 如果子类还没设置 _name，则使用类名（子类可在 super().__init__ 之前设置 _name）
        if not hasattr(self, "_name"):
            self._name = self.__class__.__name__.lower()
        self._obj_id: int = ActiveObject._object_counter
        ActiveObject._object_counter += 1

        # 如果传入了 owner，则自动嵌入
        if owner is not None:
            owner.embed(self)

    @property
    def name(self) -> str:
        """兼容属性：返回节点名称。等同于 _name。"""
        return self._name

    @name.setter
    def name(self, val: str) -> None:
        self._name = val

    @property
    def display_name(self) -> str:
        """人类可读的显示名称。默认为 _name。"""
        return getattr(self, "_display_name", self._name)

    @display_name.setter
    def display_name(self, val: str) -> None:
        self._display_name = val

    # ── 树形导航 ──────────────────────────────────────

    def get_owner(self) -> Optional["ActiveObject"]:
        """返回父节点。"""
        return self._owner

    def get_embedded(self) -> dict[str, "ActiveObject"]:
        """返回所有直接子节点。"""
        return dict(self._embedded)

    def get_full_path(self) -> str:
        """
        从根节点到自身的完整路径。
        例: "main.model.ports.SHA"
        """
        parts = []
        node: Optional[ActiveObject] = self
        while node is not None:
            parts.append(node._name)
            node = node._owner
        return ".".join(reversed(parts))

    def resolve(self, path: str) -> Optional["ActiveObject"]:
        """
        从当前节点往下查找路径。
        例: resolve("cranes.crane_2") 返回 crane_2 子节点
        自动跳过与当前节点 _name 匹配的首段，使得传入 get_full_path() 的完整路径也能解析。
        """
        current: ActiveObject = self
        parts = path.split(".")
        # 如果首段与当前节点名相同，跳过（兼容 get_full_path() 输出的完整路径）
        if parts and parts[0] == current._name:
            parts = parts[1:]
        for part in parts:
            if not part:
                continue
            found = current._embedded.get(part)
            if found is None:
                return None
            current = found
        return current

    def get_root(self) -> "ActiveObject":
        """返回树的根节点。"""
        node: ActiveObject = self
        while node._owner is not None:
            node = node._owner
        return node

    # ── 树操作 ────────────────────────────────────────

    def embed(
        self, child: "ActiveObject", name: Optional[str] = None
    ) -> "ActiveObject":
        """
        将 child 嵌入到当前节点下。自动设置 parent 链接。
        返回 child（链式调用）。
        """
        # 如果 child 原来属于别的 parent，先从旧 parent 解绑
        if child._owner is not None and child._owner is not self:
            child._owner._embedded.pop(child._name, None)
        elif child._owner is self:
            # 同 owner 下换名：清理旧的 key 条目（避免重复）
            for old_name, old_child in list(self._embedded.items()):
                if old_child is child and old_name != (name or child._name):
                    self._embedded.pop(old_name, None)
                    break

        if name is not None:
            child._name = name
        elif child._name in self._embedded:
            # 自动生成唯一 name
            base = child._name
            idx = 1
            while f"{base}_{idx}" in self._embedded:
                idx += 1
            child._name = f"{base}_{idx}"

        child._owner = self
        self._embedded[child._name] = child
        return child

    def remove(self, child_or_name: "str | ActiveObject") -> None:
        """从子树中移除一个子节点。"""
        if isinstance(child_or_name, str):
            name = child_or_name
            child = self._embedded.pop(name, None)
        else:
            child = child_or_name
            # 找到 child 在本节点的名字
            for n, c in list(self._embedded.items()):
                if c is child:
                    self._embedded.pop(n)
                    break
            else:
                return  # 没找到
        if child is not None:
            child._owner = None

    def unlink(self) -> None:
        """从父节点中移除自己。"""
        if self._owner is not None:
            self._owner.remove(self)

    def iter_tree(self, include_self: bool = True):
        """
        深度优先遍历整棵子树。每个节点产出 (name, obj)。
        """
        if include_self:
            yield self._name, self
        for name, obj in self._embedded.items():
            yield name, obj
            yield from obj.iter_tree(include_self=False)

    def find(self, cls: Type, include_self: bool = True) -> list:
        """在子树中查找所有指定类型的实例。"""
        result = []
        if include_self and isinstance(self, cls):
            result.append(self)
        for child in self._embedded.values():
            result.extend(child.find(cls, include_self=True))
        return result

    def get_engine(self) -> Optional["Engine"]:
        """返回所在的 Engine 实例（如果有的话）。"""
        node: ActiveObject = self
        while node is not None:
            if isinstance(node, Engine):
                return node
            node = node._owner
        return None

    def to_tree_dict(self) -> dict:
        """
        将整棵子树序列化为递归 dict，供前端渲染。
        格式与 AnyLogic agent 树一致。
        """
        return {
            "name": self._name,
            "type": self.__class__.__name__,
            "parameters": self._collect_parameters(),
            "children": {
                name: child.to_tree_dict() for name, child in self._embedded.items()
            },
        }

    def _collect_parameters(self) -> list[dict]:
        """子类可覆盖此方法返回自己的参数列表。支持 get_parameters() 和 get_parameter_defs() 两种格式。"""
        # 优先使用新的 tree.Parameter 格式
        params = self.get_parameters()
        if params:
            return [p.to_dict() for p in params]

        # 兼容旧的 ParameterDef 格式
        if hasattr(self, "get_parameter_defs"):
            defs = self.get_parameter_defs()
            if defs:
                return [d.to_dict() for d in defs]

        return []

    # ── 参数声明（子类覆盖） ────────────────────────────

    @classmethod
    def get_parameters(cls) -> list[Parameter]:
        """返回此类的参数定义。子类可以覆盖此方法。"""
        return []

    def get_param(self, key: str, default: Any = None) -> Any:
        """读取属性值 vs 默认值。"""
        return getattr(self, key, default)

    def set_param(self, key: str, value: Any) -> None:
        """设置属性值（触发 onChange 钩子）。"""
        if hasattr(self, key):
            old = getattr(self, key)
            if old != value:
                setattr(self, key, value)
                self._on_param_changed(key, old, value)
        else:
            setattr(self, key, value)

    def update_params(self, params: dict[str, Any]) -> None:
        """批量更新参数（触发 onChange 钩子）。"""
        for key, value in params.items():
            self.set_param(key, value)

    def _on_param_changed(self, key: str, old: Any, new: Any) -> None:
        """AnyLogic 的 onChange() 钩子。当参数被修改时自动调用。"""
        try:
            self.on_change(key, old, new)
        except Exception:
            pass

    # ── 生命周期钩子 ──────────────────────────────────

    def on_create(self) -> None:
        """AnyLogic 的 On startup action。在 Agent 被创建后调用。"""
        pass

    def on_destroy(self) -> None:
        """AnyLogic 的 On destroy action。在 Agent 被销毁前调用。"""
        pass

    def on_change(self, key: str, old: Any, new: Any) -> None:
        """AnyLogic 的 On change action。当参数被修改时调用。"""
        pass

    def on_before_step(self) -> None:
        """每个仿真步之前调用。"""
        pass

    def on_after_step(self) -> None:
        """每个仿真步之后调用。"""
        pass


# ═══════════════════════════════════════════════════════════════════
# Agent 基类
# ═══════════════════════════════════════════════════════════════════


class Agent(ActiveObject):
    """
    Agent = 拥有完整生命周期的仿真实体。
    对比 AnyLogic: com.anylogic.engine.Agent

    Agent 的生命周期：
      1. __init__() → 创建实例（参数由子类声明）
      2. embed()    → 挂载到父 Agent 下
      3. on_create() → 仿真开始前初始化
      4. 仿真循环...
      5. on_destroy() → 销毁清理

    Agent 的树形组织：
      MainAgent
        └── Model
              ├── Ships (AgentPopulation)
              │     ├── s001 (ShipAgent)
              │     └── s002 (ShipAgent)
              └── Ports (AgentPopulation)
                    └── SHA (PortAgent)
                          └── Cranes (AgentPopulation)
                                ├── crane_1
                                └── crane_2
    """

    def __init__(self, owner: Optional["ActiveObject"] = None, **kwargs):
        super().__init__(owner=owner)

        # 用 kwargs 覆盖默认参数
        for key, value in kwargs.items():
            self.set_param(key, value)

    def get_time(self) -> float:
        """获取当前仿真时间（从 Engine 获取）。"""
        engine = self.get_engine()
        return engine.current_time if engine else 0.0

    def get_scheduler(self) -> Optional["EventDrivenScheduler"]:
        """获取事件调度器。"""
        engine = self.get_engine()
        return engine.scheduler if engine else None

    def schedule_event_at(
        self,
        time: float,
        event_type: str,
        target_agent_id: Optional[str] = None,
        payload: dict = None,
        source: str = "system",
    ) -> None:
        """调度一个未来事件。"""
        scheduler = self.get_scheduler()
        if scheduler:
            scheduler.schedule_event_at(
                time=time,
                event_type=event_type,
                target_agent_id=target_agent_id or self._name,
                payload=payload or {},
                source=source,
            )

    def handle_event(self, event: "Event") -> None:
        """处理事件。子类覆盖此方法实现自己的事件处理逻辑。"""
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}:{self._name} @ {hex(id(self))}>"


# ═══════════════════════════════════════════════════════════════════
# AgentPopulation — 管理 Agent 集合
# ═══════════════════════════════════════════════════════════════════


class AgentPopulation(ActiveObject):
    """
    一组同类型 Agent 的集合。
    对应 AnyLogic 的 Population<T extends Agent>。

    用法:
      ships = AgentPopulation(ShipAgent, owner=model, name="ships")
      ships.add(s001=ship_params_1, name="s001")
      ships.add(name="s002", capacity_teu=15000, design_speed=20)
    """

    def __init__(
        self,
        agent_class: Type[Agent],
        owner: Optional[ActiveObject] = None,
        name: str = "population",
        **default_params,
    ):
        self._name = name  # 必须在 super().__init__ 之前
        super().__init__(owner=owner)
        self._agent_class = agent_class
        self._default_params = default_params
        self._instances: dict[str, Agent] = {}

    @property
    def size(self) -> int:
        return len(self._instances)

    def add(self, name: Optional[str] = None, **params) -> Agent:
        """
        创建并添加一个新的 Agent 实例。
        可指定 name 和初始参数。
        """
        merged = {**self._default_params, **params}
        agent = self._agent_class(owner=None, **merged)
        if name:
            agent._name = name
        # 挂载到 Population 下（同时设置 owner 和树链接）
        super().embed(agent, name=agent._name)
        self._instances[agent._name] = agent
        return agent

    def get(self, name: str) -> Optional[Agent]:
        """按名称获取 Agent。"""
        return self._instances.get(name)

    def get_all(self) -> dict[str, Agent]:
        """返回所有 Agent（字典副本）。"""
        return dict(self._instances)

    def create(self, count: int, name_prefix: str = "agent") -> list[Agent]:
        """批量创建同类型 Agent。"""
        created = []
        for i in range(count):
            agent = self.add(name=f"{name_prefix}_{i}")
            created.append(agent)
        return created

    def to_tree_dict(self) -> dict:
        return {
            "name": self._name,
            "type": f"Population<{self._agent_class.__name__}>",
            "parameters": [
                Parameter(
                    key="size", label="数量", type=ParamType.INT, default=self.size
                ).to_dict()
            ],
            "children": {
                name: agent.to_tree_dict() for name, agent in self._instances.items()
            },
        }

    def embed(self, child, name=None):
        """AgentPopulation 允许正常的树嵌入（子 Agent 通过 add() 调用此方法）。"""
        return super().embed(child, name)

    def remove(self, child_or_name: "str | ActiveObject") -> None:
        """
        覆写 ActiveObject.remove()，同步清理 _instances 和 _embedded。
        """
        name = (
            child_or_name._name if not isinstance(child_or_name, str) else child_or_name
        )
        self._instances.pop(name, None)
        super().remove(child_or_name)

    def remove_by_name(self, name: str):
        """按名称删除 agent，返回被删除的 agent 或 None。"""
        agent = self._instances.pop(name, None)
        if agent is not None:
            self._embedded.pop(name, None)
            agent._owner = None
        return agent

    def remove_all(self) -> list:
        """清空 population 中所有 agent，返回被删除的列表。"""
        removed = list(self._instances.values())
        for name in list(self._instances.keys()):
            self._embedded.pop(name, None)
        self._instances.clear()
        for agent in removed:
            agent._owner = None
        return removed


# ═══════════════════════════════════════════════════════════════════
# Engine — 仿真引擎
# ═══════════════════════════════════════════════════════════════════


class Engine(ActiveObject):
    """
    仿真引擎。每棵树都有一个 Engine，隔离运行。
    对应 AnyLogic 的 com.anylogic.engine.Engine
    """

    def __init__(self, root_agent: Optional[Agent] = None):
        super().__init__(owner=None)
        self._name = "engine"
        self.current_time: float = 0.0
        self.is_running: bool = False
        self.speed: float = 1.0

        if root_agent is not None:
            self.embed(root_agent, name="root")
            root_agent.on_create()

        # 调度器延迟初始化（避免循环导入）
        self.scheduler: Optional["EventDrivenScheduler"] = None

    def get_root_agent(self) -> Optional[ActiveObject]:
        """返回顶层根节点（ActiveObject 或 Agent）。"""
        for child in self._embedded.values():
            return child
        return None

    def get_agent(self, agent_id: str) -> Optional[ActiveObject]:
        """在整个 agent 树中查找（按 _name）。"""
        root = self.get_root_agent()
        if root is None:
            return None
        return root.resolve(agent_id)

    def to_state_dict(self) -> dict:
        """序列化当前状态（供前端同步）。"""
        return {
            "current_time": self.current_time,
            "is_running": self.is_running,
            "speed": self.speed,
            "tree": self.to_tree_dict(),
        }

    def reset(self) -> None:
        """重置引擎。"""
        self.current_time = 0.0
        self.is_running = False
        self.speed = 1.0
        if self.scheduler:
            self.scheduler.event_queue.clear()


# ═══════════════════════════════════════════════════════════════════
# Experiment — 实验框架
# ═══════════════════════════════════════════════════════════════════


class Experiment:
    """
    实验 = 一个参数化场景 + 独立 Engine 实例。
    对应 AnyLogic 的 com.anylogic.engine.Experiment

    每个 Experiment 持有独立的 Engine 树，天然隔离，可并行运行。
    """

    def __init__(self, name: str, root_factory: callable = None):
        self.name = name
        self.description: str = ""
        self._root_factory = root_factory
        self.engine: Optional[Engine] = None

    def setup(self) -> None:
        """创建 Engine 和 root agent。"""
        from .scheduler import EventDrivenScheduler  # 延迟导入避免循环

        if self._root_factory:
            root = self._root_factory()
        else:
            root = Agent()

        self.engine = Engine(root_agent=root)
        self.engine.scheduler = EventDrivenScheduler(self.engine)

    def run(self, end_time: float = 0) -> int:
        """运行实验。"""
        if self.engine is None:
            self.setup()
        self.engine.is_running = True

        root = self.engine.get_root_agent()
        if root:
            root.on_create()

        if self.engine.scheduler:
            steps = self.engine.scheduler.run_until(end_time)
        else:
            steps = 0

        self.engine.is_running = False
        return steps

    def step(self) -> bool:
        """单步执行。"""
        if self.engine is None:
            self.setup()
        if self.engine.scheduler:
            return self.engine.scheduler.step()
        return False

    def clone(self, name: Optional[str] = None) -> "Experiment":
        """深拷贝当前实验配置（创建可独立运行的副本）。"""
        import copy

        new_exp = copy.deepcopy(self)
        new_exp.engine = None  # 新实验需要重新 setup
        if name:
            new_exp.name = name
        return new_exp


class ExperimentSuite:
    """
    实验套件 = 一组 Experiment。
    可以用来批量运行对比实验。
    """

    def __init__(self, name: str = "Suite"):
        self.name = name
        self.experiments: list[Experiment] = []

    def add(self, experiment: Experiment) -> "ExperimentSuite":
        self.experiments.append(experiment)
        return self

    def run_all(self, end_time: float = 0) -> list[dict]:
        results = []
        for exp in self.experiments:
            exp.setup()
            steps = exp.run(end_time)
            results.append(
                {
                    "experiment": exp.name,
                    "steps": steps,
                    "final_time": exp.engine.current_time if exp.engine else 0.0,
                }
            )
        return results
