"""Agent CRUD 操作测试 — Phase A 新增功能。"""

import pytest
from app.core.tree import (
    ActiveObject, Agent, AgentPopulation, Engine, ParamType, Parameter,
)
from app.scheduler.scheduler import (
    SimulationModel, ShipAgent, PortAgent, CraneAgent, BaseAgent,
)
from app.core.agent_registry import AgentTypeRegistry, AgentTypeEntry


class TestAgentPopulationRemove:
    """测试 AgentPopulation 的 remove 方法同步 _instances 和 _embedded。"""

    def setup_method(self):
        self.pop = AgentPopulation(ShipAgent, name="ships")

    def test_remove_by_name_syncs_both(self):
        agent = self.pop.add(name="s001")
        assert "s001" in self.pop._instances
        assert "s001" in self.pop._embedded

        removed = self.pop.remove_by_name("s001")
        assert removed is agent
        assert "s001" not in self.pop._instances
        assert "s001" not in self.pop._embedded
        assert agent._owner is None

    def test_remove_by_name_nonexistent(self):
        removed = self.pop.remove_by_name("ghost")
        assert removed is None
        assert len(self.pop._instances) == 0

    def test_remove_all_clears_everything(self):
        self.pop.create(5, name_prefix="ship")
        assert self.pop.size == 5

        removed = self.pop.remove_all()
        assert len(removed) == 5
        assert self.pop.size == 0
        assert len(self.pop._instances) == 0
        assert len(self.pop._embedded) == 0
        for agent in removed:
            assert agent._owner is None

    def test_remove_by_object_reference(self):
        agent = self.pop.add(name="s001")
        self.pop.create(2, name_prefix="extra")
        assert self.pop.size == 3

        self.pop.remove(agent)
        assert "s001" not in self.pop._instances
        assert "s001" not in self.pop._embedded
        assert self.pop.size == 2

    def test_remove_by_string_name(self):
        self.pop.add(name="s001")
        self.pop.remove("s001")
        assert "s001" not in self.pop._instances
        assert self.pop.size == 0


class TestAgentTypeRegistry:
    """测试 AgentTypeRegistry 类型注册。"""

    def setup_method(self):
        AgentTypeRegistry.reset_instance()

    def teardown_method(self):
        AgentTypeRegistry.reset_instance()

    def test_registry_has_all_types(self):
        registry = AgentTypeRegistry.get_instance()
        types = registry.get_all_types()
        type_names = {t.type_name for t in types}
        assert "ShipAgent" in type_names
        assert "PortAgent" in type_names
        assert "CraneAgent" in type_names

    def test_registry_type_metadata(self):
        registry = AgentTypeRegistry.get_instance()
        ship_type = registry.get_type("ShipAgent")
        assert ship_type is not None
        assert ship_type.label == "船舶"
        assert ship_type.icon == "🚢"
        assert len(ship_type.parameters) > 0

    def test_registry_unknown_type(self):
        registry = AgentTypeRegistry.get_instance()
        assert registry.get_type("NonExistentAgent") is None

    def test_registry_singleton(self):
        r1 = AgentTypeRegistry.get_instance()
        r2 = AgentTypeRegistry.get_instance()
        assert r1 is r2


class TestAgentCRUD:
    """测试通过 SimulationModel 的 agent 动态增删。"""

    def setup_method(self):
        from app.scheduler.scheduler import _init_demo_scenario
        self.model = SimulationModel()
        _init_demo_scenario(self.model)

    def test_create_ship_agent(self):
        """创建新的 ShipAgent 并验证注册表。"""
        ship = ShipAgent(
            unique_id="s_test",
            owner=None,
            name="Test Ship",
            current_speed=20,
            capacity_teu=18000,
        )
        self.model.add_agent(ship)
        assert "s_test" in self.model._agents
        assert "s_test" in self.model._embedded
        assert self.model.resolve("s_test") is ship

    def test_create_port_agent(self):
        """创建 PortAgent 并验证 _ports 注册表。"""
        port = PortAgent(
            unique_id="PTEST",
            owner=None,
            name="Test Port",
            lat=25.0,
            lon=120.0,
            berth_count=5,
        )
        self.model.add_agent(port)
        assert "PTEST" in self.model._ports
        assert "PTEST" in self.model._agents
        assert self.model.resolve("PTEST") is port

    def test_remove_agent_cleans_registries(self):
        """删除 agent 清理所有内部注册表。"""
        ship = ShipAgent(unique_id="s_kill", owner=None)
        self.model.add_agent(ship)
        assert "s_kill" in self.model._agents

        removed = self.model.remove_agent("s_kill")
        assert removed is ship
        assert "s_kill" not in self.model._agents
        assert "s_kill" not in self.model._embedded
        assert ship._owner is None

    def test_remove_agent_nonexistent(self):
        removed = self.model.remove_agent("ghost_ship")
        assert removed is None

    def test_cannot_delete_root_model(self):
        """model 本身不应被删除。"""
        # resolve 支持与自身 _name 匹配的路径前缀
        assert self.model.resolve("model") is self.model
        # resolve 不支持不存在的路径
        assert self.model.resolve("nonexistent") is None


class TestAgentPopulationCRUD:
    """测试 AgentPopulation 上的 agent 增删操作。"""

    def setup_method(self):
        from app.scheduler.scheduler import _init_demo_scenario
        self.model = SimulationModel()
        _init_demo_scenario(self.model)

    def test_add_to_population(self):
        """向已有的 population 添加 agent。"""
        sha_port = self.model._ports.get("SHA")
        assert sha_port is not None
        assert hasattr(sha_port, 'cranes')

        initial_count = sha_port.cranes.size
        new_crane = sha_port.cranes.add(name="crane_extra", handling_rate=50)
        assert sha_port.cranes.size == initial_count + 1
        assert "crane_extra" in sha_port.cranes._instances
        assert sha_port.resolve("cranes.crane_extra") is new_crane

    def test_remove_from_population(self):
        """从 population 中删除 agent。"""
        sha_port = self.model._ports.get("SHA")
        initial_count = sha_port.cranes.size

        removed = sha_port.cranes.remove_by_name("crane_1")
        assert removed is not None
        assert sha_port.cranes.size == initial_count - 1
        assert "crane_1" not in sha_port.cranes._instances
        assert "crane_1" not in sha_port.cranes._embedded
        # 已删除的 agent 不在树中
        assert sha_port.resolve("cranes.crane_1") is None


class TestTreeNavigationAfterCRUD:
    """测试 agent 增删后树导航仍然正确。"""

    def setup_method(self):
        from app.scheduler.scheduler import _init_demo_scenario
        self.model = SimulationModel()
        _init_demo_scenario(self.model)

    def test_full_path_after_add_agent(self):
        """创建 agent 后 get_full_path 返回正确路径。"""
        ship = ShipAgent(unique_id="s_nav", owner=None, name="Nav Ship")
        self.model.add_agent(ship)
        path = ship.get_full_path()
        assert path == "engine.model.s_nav"

    def test_resolve_after_add_agent(self):
        """创建 agent 后 resolve 能找到它。"""
        ship = ShipAgent(unique_id="s_resolve", owner=None)
        self.model.add_agent(ship)
        found = self.model.resolve("s_resolve")
        assert found is ship

    def test_resolve_with_full_path(self):
        """resolve 支持 get_full_path() 格式的完整路径。"""
        ship = ShipAgent(unique_id="s_fullpath", owner=None)
        self.model.add_agent(ship)
        full_path = ship.get_full_path()
        assert full_path == "engine.model.s_fullpath"
        # 从根节点用完整路径解析
        root = self.model.get_root()
        assert root.resolve(full_path) is ship
        # 从 model 自身用完整路径解析（会跳过 engine 段匹配自身 name）
        assert self.model.resolve("model.s_fullpath") is ship

    def test_resolve_returns_none_after_delete(self):
        """删除 agent 后 resolve 返回 None。"""
        ship = ShipAgent(unique_id="s_gone", owner=None)
        self.model.add_agent(ship)
        self.model.remove_agent("s_gone")
        assert self.model.resolve("s_gone") is None

    def test_tree_dict_doesnt_include_deleted(self):
        """删除 agent 后 to_tree_dict 不包含它。"""
        ship = ShipAgent(unique_id="s_temp", owner=None)
        self.model.add_agent(ship)
        self.model.remove_agent("s_temp")

        tree = self.model.to_tree_dict()
        children_names = list(tree.get("children", {}).keys())
        assert "s_temp" not in children_names

    def test_iter_tree_finds_new_agent(self):
        """创建 agent 后 iter_tree 能找到它。"""
        ship = ShipAgent(unique_id="s_iter", owner=None)
        self.model.add_agent(ship)

        found = any(
            obj is ship
            for _name, obj in self.model.iter_tree(include_self=False)
        )
        assert found
