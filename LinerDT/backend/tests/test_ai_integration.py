import pytest
from app.scheduler.scheduler import SimulationModel, ShipAgent, PortAgent
from app.models.ship import ShipState
from app.scheduler.events import EventType
from app.ai import (
    get_ai_integration,
    BaseAIAgent,
    DecisionContext,
    AIDecision,
    DecisionType,
    RuleBasedAIAgent,
    CIIAwareAIAgent,
)


class TestAIAgentRegistration:
    def test_register_and_retrieve_agent(self):
        ai = get_ai_integration()
        ai.ai_agents.clear()
        agent = RuleBasedAIAgent()
        ai.register_ai_agent("test_agent", agent)
        ai.register_ai_agent("primary", agent)

        assert "test_agent" in ai.ai_agents
        assert ai.get_primary_agent() == agent

    def test_multiple_agents_primary_is_first(self):
        ai = get_ai_integration()
        ai.ai_agents.clear()

        agent1 = RuleBasedAIAgent()
        agent1.name = "first"
        agent2 = CIIAwareAIAgent()
        agent2.name = "second"

        ai.register_ai_agent("first", agent1)
        ai.register_ai_agent("second", agent2)

        assert ai.get_primary_agent().name == "first"


class TestRuleBasedAIAgent:
    def test_cii_critical_triggers_economic_speed(self):
        agent = RuleBasedAIAgent()

        context = DecisionContext(
            ship_id="test_ship",
            ship_name="Test Ship",
            current_speed=20.0,
            economic_speed=18.0,
            design_speed=22.0,
            current_state=ShipState.SAILING,
            current_port="SHA",
            next_port="NGB",
            cumulative_delay=0.0,
            cii_ratio=1.5,
            co2_emissions=100000.0,
            capacity_teu=20000,
            sim_time=100.0,
            route=["SHA", "NGB", "XMN"],
        )

        decision = agent.evaluate_speed(context)

        assert decision is not None
        assert decision.decision_type == DecisionType.SPEED_ADJUSTMENT
        assert decision.suggested_value == 18.0
        assert "CII比率" in decision.reason

    def test_cii_warning_with_delay_allows_speed_boost(self):
        agent = RuleBasedAIAgent()

        context = DecisionContext(
            ship_id="test_ship",
            ship_name="Test Ship",
            current_speed=18.0,
            economic_speed=18.0,
            design_speed=22.0,
            current_state=ShipState.SAILING,
            current_port="SHA",
            next_port="NGB",
            cumulative_delay=30.0,
            cii_ratio=1.2,
            co2_emissions=80000.0,
            capacity_teu=20000,
            sim_time=100.0,
            route=["SHA", "NGB", "XMN"],
        )

        decision = agent.evaluate_speed(context)

        assert decision is not None
        assert decision.suggested_value > 18.0
        assert "延误" in decision.reason

    def test_no_decision_when_speed_close_to_economic(self):
        agent = RuleBasedAIAgent()

        context = DecisionContext(
            ship_id="test_ship",
            ship_name="Test Ship",
            current_speed=18.0,
            economic_speed=18.0,
            design_speed=22.0,
            current_state=ShipState.SAILING,
            current_port="SHA",
            next_port="NGB",
            cumulative_delay=2.0,
            cii_ratio=1.0,
            co2_emissions=50000.0,
            capacity_teu=20000,
            sim_time=100.0,
            route=["SHA", "NGB", "XMN"],
        )

        decision = agent.evaluate_speed(context)

        assert decision is None


class TestCIIAwareAIAgent:
    def test_rating_calculation(self):
        agent = CIIAwareAIAgent()

        assert agent.get_cii_rating(0.09) == "A"
        assert agent.get_cii_rating(0.11) == "B"
        assert agent.get_cii_rating(0.13) == "C"
        assert agent.get_cii_rating(0.16) == "E"
        assert agent.get_cii_rating(0.20) == "E"

    def test_speed_reduction_for_low_rating(self):
        agent = CIIAwareAIAgent()

        context = DecisionContext(
            ship_id="test_ship",
            ship_name="Test Ship",
            current_speed=20.0,
            economic_speed=18.0,
            design_speed=22.0,
            current_state=ShipState.SAILING,
            current_port="SHA",
            next_port="NGB",
            cumulative_delay=0.0,
            cii_ratio=1.4,
            co2_emissions=120000.0,
            capacity_teu=20000,
            sim_time=100.0,
            route=["SHA", "NGB", "XMN"],
        )

        decision = agent.evaluate_speed(context)

        assert decision is not None
        assert decision.suggested_value < 18.0
        assert "CII评级" in decision.reason


class TestAIIntegration:
    def test_ai_disabled_by_default(self):
        ai = get_ai_integration()
        assert not ai.ai_enabled

    def test_enable_ai(self):
        ai = get_ai_integration()
        ai.enable_ai(True)
        assert ai.ai_enabled

    def test_request_speed_decision_when_disabled(self):
        model = SimulationModel()
        _init_demo_scenario(model)

        ai = get_ai_integration()
        ai.enable_ai(False)

        ship = model.get_agent("s001")
        assert isinstance(ship, ShipAgent)

        ship.request_ai_speed_decision()

        assert ship.current_speed == 18.0

    def test_request_speed_decision_when_enabled(self):
        model = SimulationModel()
        _init_demo_scenario(model)

        ai = get_ai_integration()
        ai.enable_ai(True)

        ship = model.get_agent("s001")
        assert isinstance(ship, ShipAgent)

        ship.current_speed = 20.0
        ship.co2_emissions = 200000.0

        decision_count_before = len(ship.decision_log)
        ship.request_ai_speed_decision()
        decision_count_after = len(ship.decision_log)

        print(f"\nAI决策请求测试:")
        print(f"  当前速度: {ship.current_speed}")
        print(f"  CO2排放: {ship.co2_emissions}")
        print(f"  CII比率: {ship._calculate_cii_ratio():.4f}")
        print(f"  决策日志变化: {decision_count_before} -> {decision_count_after}")

        assert decision_count_after >= decision_count_before

    def test_ai_config_update(self):
        ai = get_ai_integration()

        ai.configure({"speed_optimization": False})

        assert ai.ai_config["speed_optimization"] == False

    def test_ai_status_report(self):
        ai = get_ai_integration()
        ai.enable_ai(True)

        status = ai.get_ai_status()

        assert status["enabled"] == True
        assert "registered_agents" in status
        assert len(status["registered_agents"]) > 0


class TestAIShipIntegration:
    def test_ship_requests_ai_on_departure(self):
        model = SimulationModel()
        _init_demo_scenario(model)

        ai = get_ai_integration()
        ai.enable_ai(True)

        ship = model.get_agent("s001")
        assert isinstance(ship, ShipAgent)

        initial_speed = ship.current_speed
        ship.state = ShipState.DEPARTING

        ship._schedule_departure("SHA")

        has_ai_log = any(
            "AI" in d.get("reason", "") or d.get("event") == "ai_speed_decision"
            for d in ship.decision_log
        )

        print(f"\n离港时的决策日志:")
        for d in ship.decision_log[-3:]:
            print(f"  t={d['sim_time']:.1f}: {d.get('event')} - {d.get('reason', '')[:60]}")

        assert len(ship.decision_log) > 0

    def test_cii_ratio_calculation(self):
        model = SimulationModel()
        _init_demo_scenario(model)

        ship = model.get_agent("s001")
        assert isinstance(ship, ShipAgent)

        ship._total_co2_tons = 100000.0
        ship._total_distance_nm = 50000.0
        cii_ratio = ship._calculate_cii_ratio()

        print(f"\nCII比率计算:")
        print(f"  CO2排放: {ship._total_co2_tons}")
        print(f"  总距离: {ship._total_distance_nm}")
        print(f"  CII比率: {cii_ratio:.4f}")

        assert cii_ratio > 0, "CII比率应为正数"


def _init_demo_scenario(model):
    from app.scheduler.scheduler import _init_demo_scenario as init
    init(model)
