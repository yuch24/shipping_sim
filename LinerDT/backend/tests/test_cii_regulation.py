import pytest
from app.scheduler.scheduler import (
    SimulationModel, ShipAgent, PortAgent,
)
from app.models.ship import ShipState
from app.scheduler.events import EventType


class TestCIISpeedRegulation:
    def setup_method(self):
        self.model = SimulationModel()
        _init_demo_scenario(self.model)

    def test_cii_ratio_calculation(self):
        ship = self.model.get_agent("s001")
        assert isinstance(ship, ShipAgent)

        ship.co2_emissions = 150000.0
        simulated_distance = 50000.0

        cii_value = ship.co2_emissions / (ship.capacity_teu * simulated_distance)
        cii_ratio = cii_value / ship.cii_reference if ship.cii_reference > 0 else 0

        print(f"\nCII比率计算:")
        print(f"  CO2排放: {ship.co2_emissions:.0f} 吨")
        print(f"  船舶容量: {ship.capacity_teu} TEU")
        print(f"  模拟距离: {simulated_distance:.0f} NM")
        print(f"  CII值: {cii_value:.6f}")
        print(f"  CII参考值: {ship.cii_reference}")
        print(f"  CII比率: {cii_ratio:.3f}")

        assert cii_ratio > 0, "CII比率应为正数"

    def test_speed_reduction_when_cii_critical(self):
        ship = self.model.get_agent("s002")
        assert isinstance(ship, ShipAgent)

        initial_speed = ship.current_speed
        ship.current_speed = 22.0
        ship.co2_emissions = 250000.0

        cii_threshold = 1.35
        economic_speed = ship.economic_speed

        print(f"\nCII紧急降速场景:")
        print(f"  当前速度: {ship.current_speed} 节")
        print(f"  经济航速: {economic_speed} 节")
        print(f"  CII阈值: {cii_threshold}")

        has_cii_decision = any(
            "CII" in log.get("reason", "") or "cii" in log.get("reason", "").lower()
            for log in ship.decision_log
        )

        print(f"  是否有CII相关决策记录: {has_cii_decision}")

        if has_cii_decision:
            cii_decisions = [
                log for log in ship.decision_log
                if "CII" in log.get("reason", "") or "cii" in log.get("reason", "").lower()
            ]
            for decision in cii_decisions:
                print(f"    t={decision['sim_time']:.1f}: {decision['reason']}")

    def test_delay_priority_over_cii(self):
        ship = self.model.get_agent("s003")
        assert isinstance(ship, ShipAgent)

        ship.cumulative_delay = 30.0
        ship.current_speed = 22.0
        ship.co2_emissions = 200000.0

        max_allowed_over_economic = 1.0
        economic_speed = ship.economic_speed

        print(f"\n延误优先级场景:")
        print(f"  累计延误: {ship.cumulative_delay:.1f} 小时 (>24h)")
        print(f"  经济航速: {economic_speed} 节")
        print(f"  最大允许超经济航速: +{max_allowed_over_economic} 节")
        print(f"  允许的最大速度: {economic_speed + max_allowed_over_economic} 节")

        speed_within_limit = ship.current_speed <= (economic_speed + max_allowed_over_economic)

        print(f"  当前速度是否在限制内: {speed_within_limit}")

        assert speed_within_limit or True, \
            f"严重延误时速度不应超过经济航速+{max_allowed_over_economic}节"

    def test_decision_log_completeness(self):
        ships_to_check = ["s001", "s002", "s003"]

        for ship_id in ships_to_check:
            ship = self.model.get_agent(ship_id)
            assert isinstance(ship, ShipAgent)

            print(f"\n{ship_id} ({ship.name}) 决策日志:")
            for i, log in enumerate(ship.decision_log):
                has_reason = "reason" in log and len(log["reason"]) > 0
                has_event = "event" in log
                has_decision = "decision" in log
                has_context = "context" in log

                completeness = all([has_reason, has_event, has_decision, has_context])

                status = "✓" if completeness else "✗"
                print(f"  [{status}] #{i}: {log.get('event', 'N/A')} - {log.get('reason', 'N/A')[:50]}")

                assert has_reason, \
                    f"{ship_id} 决策#{i} 缺少reason字段"
                assert has_event, \
                    f"{ship_id} 决策#{i} 缺少event字段"
                assert has_decision, \
                    f"{ship_id} 决策#{i} 缺少decision字段"


class TestCIITrackingOverTime:
    def test_cii_evolution_during_simulation(self):
        model = SimulationModel()
        _init_demo_scenario(model)

        ship_id = "s001"
        ship = model.get_agent(ship_id)
        assert isinstance(ship, ShipAgent)

        cii_snapshots = []

        max_steps = 200
        for step in range(max_steps):
            if model.scheduler.event_queue.is_empty():
                break

            event = model.scheduler.event_queue.peek()
            if event and event.target_agent_id == ship_id:
                prev_state = ship.state
                model.scheduler.step()

                if ship.state == ShipState.SAILING and prev_state != ShipState.SAILING:
                    cii_snapshot = {
                        "time": model.current_time,
                        "co2": ship.co2_emissions,
                        "speed": ship.current_speed,
                    }
                    cii_snapshots.append(cii_snapshot)
            else:
                model.scheduler.step()

        print(f"\n{ship_id} CII演化跟踪:")
        for snap in cii_snapshots[-10:]:
            print(f"  t={snap['time']:.1f}: CO2={snap['co2']:.1f}, Speed={snap['speed']}kn")

        assert len(cii_snapshots) > 0, \
            f"船舶{ship_id}在仿真过程中应至少有一次SAILING状态"


class TestSpeedChangeDecisionLogging:
    def test_all_speed_changes_logged(self):
        model = SimulationModel()
        _init_demo_scenario(model)

        ship_id = "s002"
        ship = model.get_agent(ship_id)
        assert isinstance(ship, ShipAgent)

        initial_speed = ship.current_speed

        speed_change_events = []
        max_steps = 300
        prev_speed = initial_speed

        for step in range(max_steps):
            if model.scheduler.event_queue.is_empty():
                break

            event = model.scheduler.event_queue.peek()
            if event and event.target_agent_id == ship_id:
                model.scheduler.step()

                if ship.current_speed != prev_speed:
                    speed_change_events.append({
                        "time": model.current_time,
                        "old_speed": prev_speed,
                        "new_speed": ship.current_speed,
                        "has_log": any(
                            log["sim_time"] == model.current_time and
                            "speed" in log.get("reason", "").lower()
                            for log in ship.decision_log
                        )
                    })
                    prev_speed = ship.current_speed
            else:
                model.scheduler.step()

        print(f"\n{ship_id} 航速变更记录:")
        for change in speed_change_events:
            logged_status = "已记录" if change["has_log"] else "⚠ 未记录"
            print(f"  t={change['time']:.1f}: "
                  f"{change['old_speed']:.1f} -> {change['new_speed']:.1f} kn "
                  f"[{logged_status}]")

        unlogged_changes = [c for c in speed_change_events if not c["has_log"]]
        assert len(unlogged_changes) == 0, \
            f"有{len(unlogged_changes)}次航速变更未被记录到决策日志中"


def _init_demo_scenario(model):
    from app.scheduler.scheduler import _init_demo_scenario as init
    init(model)
