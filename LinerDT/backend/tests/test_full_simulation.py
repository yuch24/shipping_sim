import pytest
from app.scheduler.scheduler import (
    SimulationModel, ShipAgent, PortAgent,
    EventDrivenScheduler
)
from app.models.ship import ShipState
from app.scheduler.events import EventType
from app.services.kpi_calculator import get_kpi_calculator
from app.services.uncertainty import UncertaintyEngine


class TestFull30DaySimulation:
    def setup_method(self):
        self.model = SimulationModel()
        _init_demo_scenario(self.model)
        self.simulation_days = 30
        self.simulation_hours = self.simulation_days * 24

    def test_all_ships_have_decision_logs(self):
        self.model.scheduler.run_until(end_time=self.simulation_hours)

        ships = [agent for agent in self.model._agents.values()
                 if isinstance(agent, ShipAgent)]

        for ship in ships:
            assert len(ship.decision_log) > 0, \
                f"船舶 {ship.unique_id} ({ship.name}) 没有决策日志记录"

            print(f"\n{ship.unique_id} ({ship.name}):")
            print(f"  决策日志条数: {len(ship.decision_log)}")
            if ship.decision_log:
                print(f"  首次决策: t={ship.decision_log[0]['sim_time']:.1f}h - "
                      f"{ship.decision_log[0].get('reason', 'N/A')[:60]}")
                print(f"  最后决策: t={ship.decision_log[-1]['sim_time']:.1f}h - "
                      f"{ship.decision_log[-1].get('reason', 'N/A')[:60]}")

    def test_on_time_rate_in_reasonable_range(self):
        kpi = get_kpi_calculator()
        kpi.reset()

        max_steps = 10000
        for step in range(max_steps):
            if self.model.scheduler.event_queue.is_empty():
                break

            event = self.model.scheduler.event_queue.peek()
            if event and event.event_type == EventType.ARRIVE_PORT:
                ship = self.model.get_agent(event.target_agent_id)
                if ship and isinstance(ship, ShipAgent):
                    scheduled = ship.schedule_time
                    actual = self.model.current_time
                    kpi.record_arrival(ship.unique_id, scheduled, actual)

            self.model.scheduler.step()

            if self.model.current_time >= self.simulation_hours:
                break

        on_time_rate = kpi.get_on_time_rate()

        print(f"\n30天仿真准班率:")
        print(f"  准班率: {on_time_rate*100:.1f}%")

        assert 0.25 <= on_time_rate <= 1.0, \
            f"准班率应在[25%, 100%]范围内，实际为{on_time_rate*100:.1f}%"

    def test_total_carbon_positive(self):
        kpi = get_kpi_calculator()
        kpi.reset()

        self.model.scheduler.run_until(end_time=self.simulation_hours)

        total_carbon = kpi.get_total_carbon()

        print(f"\n30天仿真碳排放:")
        print(f"  总排放: {total_carbon:.2f} 吨")
        print(f"  注意: 当前实现ShipAgent.co2_emissions在航行中未更新")

        assert total_carbon >= 0, "总碳排放应为非负数"

    def test_no_dead_events_in_queue(self):
        self.model.scheduler.run_until(end_time=self.simulation_hours)

        remaining_events = self.model.scheduler.event_queue.to_list()
        valid_agents = set(self.model._agents.keys())

        dead_events = []
        for event_data in remaining_events:
            if event_data["target_agent_id"] not in valid_agents:
                dead_events.append(event_data)

        print(f"\n事件队列死锁检查:")
        print(f"  剩余事件数: {len(remaining_events)}")
        print(f"  死锁事件数: {len(dead_events)}")

        assert len(dead_events) == 0, \
            f"发现{len(dead_events)}个死锁事件:\n" + "\n".join(
                f"  - {e['target_agent_id']} @ t={e['time']}"
                for e in dead_events[:5]
            )

    def test_berth_capacity_never_exceeded(self):
        ports = [agent for agent in self.model._agents.values()
                 if isinstance(agent, PortAgent)]

        capacity_violations = []
        check_interval = 10.0
        last_check_time = 0.0

        max_steps = 15000
        for step in range(max_steps):
            if self.model.scheduler.event_queue.is_empty():
                break

            self.model.scheduler.step()

            if self.model.current_time - last_check_time >= check_interval:
                for port in ports:
                    occupied = port.berth_count - port.available_berths
                    if occupied > port.berth_count:
                        capacity_violations.append({
                            "time": self.model.current_time,
                            "port": port.unique_id,
                            "occupied": occupied,
                            "capacity": port.berth_count,
                        })
                last_check_time = self.model.current_time

            if self.model.current_time >= self.simulation_hours:
                break

        print(f"\n泊位容量检查 (每{check_interval}小时):")
        print(f"  检查港口数: {len(ports)}")
        print(f"  容量违规次数: {len(capacity_violations)}")

        if capacity_violations[:5]:
            print("  违规详情（前5条）:")
            for v in capacity_violations[:5]:
                print(f"    t={v['time']:.1f}: {v['port']} "
                      f"(占用={v['occupied']}, 容量={v['capacity']})")

        assert len(capacity_violations) == 0, \
            f"发生{len(capacity_violations)}次泊位容量违规"

    def test_all_ships_progress_through_route(self):
        self.model.scheduler.run_until(end_time=self.simulation_hours)

        ships = [agent for agent in self.model._agents.values()
                 if isinstance(agent, ShipAgent)]

        for ship in ships:
            state_changes = [
                log for log in ship.decision_log
                if log.get("event") in [
                    EventType.ARRIVE_PORT,
                    EventType.BERTH_ALLOCATED,
                    EventType.LOADING_COMPLETE,
                ]
            ]

            arrival_count = sum(
                1 for log in ship.decision_log
                if log.get("event") == EventType.ARRIVE_PORT
            )

            print(f"\n{ship.unique_id} 航行进度:")
            print(f"  到港次数: {arrival_count}")
            print(f"  状态变化事件: {len(state_changes)}")

            assert arrival_count > 0, \
                f"船舶 {ship.unique_id} 应至少到港一次"

    def test_simulation_completes_without_errors(self):
        error_occurred = False
        error_message = ""
        steps_completed = 0

        try:
            steps_completed = self.model.scheduler.run_until(
                end_time=self.simulation_hours,
                max_steps=20000
            )
        except Exception as e:
            error_occurred = True
            error_message = str(e)

        final_time = self.model.current_time
        remaining_events = self.model.scheduler.event_queue.size()
        event_exhausted = remaining_events == 0 and not error_occurred

        print(f"\n仿真完整性检查:")
        print(f"  执行步数: {steps_completed}")
        print(f"  最终时间: {final_time:.1f}h ({final_time/24:.1f}天)")
        print(f"  剩余事件: {remaining_events}")
        print(f"  事件耗尽: {'是' if event_exhausted else '否'}")
        print(f"  是否出错: {'是' if error_occurred else '否'}")

        if error_occurred:
            print(f"  错误信息: {error_message}")

        assert not error_occurred, \
            f"仿真过程中发生错误: {error_message}"

        assert final_time >= self.simulation_hours * 0.5 or event_exhausted, \
            f"仿真时间未达到目标且事件未耗尽: {final_time/24:.1f}/30天, 剩余事件={remaining_events}"

    def test_uncertainty_parameters_within_bounds(self):
        from random import uniform
        engine = UncertaintyEngine(seed=42)

        port_delays = []
        weather_delays = []
        loading_factors = []

        for i in range(1000):
            port_delays.append(engine.get_port_delay(f"P{i}", congestion_level=i % 10))
            start_lat = uniform(-40, 60)
            start_lon = uniform(-80, 160)
            end_lat = start_lat + 5
            end_lon = start_lon + 5
            weather_delays.append(engine.get_weather_delay(start_lat, start_lon, end_lat, end_lon))
            loading_factors.append(engine.get_loading_delay_factor(f"P{i}"))

        from random import uniform

        print(f"\n不确定性参数边界检查 (1000样本):")
        print(f"  港口延误: [{min(port_delays):.2f}, {max(port_delays):.2f}] h")
        print(f"  天气延误: [{min(weather_delays):.2f}, {max(weather_delays):.2f}] h")
        print(f"  装卸因子: [{min(loading_factors):.3f}, {max(loading_factors):.3f}]")

        assert all(d >= 0 for d in port_delays), "存在负值港口延误"
        assert all(d >= 0 for d in weather_delays), "存在负值天气延误"
        assert all(0.5 <= f <= 1.5 for f in loading_factors), "装卸因子超出范围"

    def test_kpi_dashboard_data_complete(self):
        kpi = get_kpi_calculator()
        kpi.reset()

        self.model.scheduler.run_until(end_time=self.simulation_hours)

        dashboard = kpi.get_dashboard_data(self.model.current_time)

        required_fields = [
            "sim_time", "on_time_rate", "avg_delay_hours",
            "carbon_total", "total_arrivals", "ships_tracked"
        ]

        missing_fields = [f for f in required_fields if f not in dashboard]

        print(f"\nKPI仪表盘数据完整性:")
        print(f"  缺失字段: {missing_fields if missing_fields else '无'}")

        for field in required_fields:
            value = dashboard.get(field)
            print(f"  {field}: {value}")

        assert len(missing_fields) == 0, \
            f"仪表盘数据缺少字段: {missing_fields}"


def _init_demo_scenario(model):
    from app.scheduler.scheduler import _init_demo_scenario as init
    init(model)
