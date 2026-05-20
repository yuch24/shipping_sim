import pytest
from app.scheduler.scheduler import SimulationModel, ShipAgent, PortAgent
from app.models.ship import ShipState
from app.scheduler.events import EventType
from app.services.kpi_calculator import KPICalculator, get_kpi_calculator


class TestOnTimeRateCalculation:
    def test_on_time_rate_with_known_delays(self):
        kpi = KPICalculator()

        kpi.register_ship("ship1")
        kpi.record_arrival("ship1", scheduled_time=100.0, actual_time=102.0)
        kpi.record_arrival("ship1", scheduled_time=200.0, actual_time=205.0)
        kpi.record_arrival("ship1", scheduled_time=300.0, actual_time=295.0)

        on_time_rate = kpi.get_on_time_rate()

        print(f"\n准班率计算 (容差±4h):")
        print(f"  到港1: 计划100h, 实际102h, 延误2h ✓")
        print(f"  到港2: 计划200h, 实际205h, 延误5h ✗")
        print(f"  到港3: 计划300h, 实际295h, 提前5h ✓")
        print(f"  准班率: {on_time_rate*100:.1f}%")

        assert on_time_rate == pytest.approx(2/3, rel=0.01), \
            f"准班率应为66.7%，实际为{on_time_rate*100:.1f}%"

    def test_on_time_rate_all_on_time(self):
        kpi = KPICalculator()
        kpi.register_ship("perfect_ship")

        for i in range(5):
            kpi.record_arrival("perfect_ship", float(i*100), float(i*100 + 2))

        assert kpi.get_on_time_rate() == 1.0, "全部准班时准班率应为100%"

    def test_on_time_rate_all_late(self):
        kpi = KPICalculator()
        kpi.register_ship("late_ship")

        for i in range(5):
            kpi.record_arrival("late_ship", float(i*100), float(i*100 + 10))

        assert kpi.get_on_time_rate() == 0.0, "全部延误时准班率应为0%"

    def test_injected_delay_reduces_on_time_rate(self):
        model = SimulationModel()
        _init_demo_scenario(model)

        kpi = get_kpi_calculator()
        kpi.reset()

        ships = [agent for agent in model._agents.values() if isinstance(agent, ShipAgent)]

        base_arrivals = 3
        for ship in ships[:3]:
            for arr in range(base_arrivals):
                kpi.record_arrival(ship.unique_id, float(arr * 200), float(arr * 200 + 2))

        base_rate = kpi.get_on_time_rate()
        print(f"\n注入延误前的准班率: {base_rate*100:.1f}%")

        injected_delay = 24.0
        for ship in ships[:3]:
            kpi.record_arrival(
                ship.unique_id,
                float(base_arrivals * 200),
                float(base_arrivals * 200) + injected_delay
            )

        after_rate = kpi.get_on_time_rate()
        print(f"注入{injected_delay}h延误后的准班率: {after_rate*100:.1f}%")

        assert after_rate < base_rate, \
            "注入严重延误后准班率应下降"


class TestUtilizationStatistics:
    def test_utilization_calculation(self):
        kpi = KPICalculator()

        total_berths = 4
        sim_duration = 720.0

        queue_history = [
            (0.0, {"PORT1": 0}),
            (100.0, {"PORT1": 1}),
            (200.0, {"PORT1": 2}),
            (300.0, {"PORT1": 3}),
            (400.0, {"PORT1": 2}),
            (500.0, {"PORT1": 1}),
            (600.0, {"PORT1": 0}),
            (700.0, {"PORT1": 1}),
        ]

        for sim_time, queues in queue_history:
            kpi.record_port_queue(sim_time, queues)

        utilization = kpi.get_utilization("PORT1", total_berths, sim_duration)

        print(f"\n利用率计算:")
        print(f"  总泊位数: {total_berths}")
        print(f"  仿真时长: {sim_duration}h ({sim_duration/24:.0f}天)")
        print(f"  队列历史采样点数: {len(queue_history)}")
        print(f"  利用率: {utilization*100:.1f}%")

        assert 0.0 <= utilization <= 1.0, \
            f"利用率应在[0,1]范围内，实际为{utilization}"

    def test_utilization_matches_manual_calculation(self):
        kpi = KPICalculator()

        port_id = "TEST_PORT"
        berth_count = 3

        all_occupied_scenarios = [
            (0.0, {port_id: 3}),
            (100.0, {port_id: 3}),
            (200.0, {port_id: 3}),
        ]

        half_occupied_scenarios = [
            (300.0, {port_id: 1}),
            (400.0, {port_id: 2}),
            (500.0, {port_id: 1}),
        ]

        for sim_time, queues in all_occupied_scenarios + half_occupied_scenarios:
            kpi.record_port_queue(sim_time, queues)

        utilization = kpi.get_utilization(port_id, berth_count, 600.0)

        avg_queue = (
            sum(q[port_id] for _, q in all_occupied_scenarios) +
            sum(q[port_id] for _, q in half_occupied_scenarios)
        ) / len(all_occupied_scenarios + half_occupied_scenarios)

        expected_util = min(1.0, (avg_queue + berth_count) / (berth_count * 2))

        print(f"\n利用率手算验证:")
        print(f"  平均队列长度: {avg_queue:.2f}")
        print(f"  KPI模块输出: {utilization*100:.1f}%")
        print(f"  手算期望值: {expected_util*100:.1f}%")

        assert abs(utilization - expected_util) < 0.05, \
            f"KPI利用率与手算值差异过大"


class TestCarbonEmissionKPI:
    def test_total_carbon_equals_individual_sum(self):
        kpi = KPICalculator()

        ship_emissions = {
            "s001": [100.0, 150.0, 120.0],
            "s002": [130.0, 140.0],
            "s003": [110.0, 160.0, 130.0, 140.0],
        }

        for ship_id, emissions in ship_emissions.items():
            kpi.register_ship(ship_id)
            for emission in emissions:
                kpi.record_carbon(ship_id, emission)

        total_carbon = kpi.get_total_carbon()
        manual_total = sum(sum(emissions) for emissions in ship_emissions.values())

        print(f"\n碳排放总计验证:")
        print(f"  各船排放:")
        for sid, emissions in ship_emissions.items():
            print(f"    {sid}: {sum(emissions):.1f} 吨 ({len(emissions)}次记录)")
        print(f"  KPI总碳排放: {total_carbon:.1f} 吨")
        print(f"  手算总和: {manual_total:.1f} 吨")

        assert total_carbon == pytest.approx(manual_total, rel=0.001), \
            f"总碳排放应等于各船之和: KPI={total_carbon}, 手算={manual_total}"

    def test_carbon_tracking_per_ship(self):
        kpi = KPICalculator()

        kpi.register_ship("carbon_test")
        emissions_sequence = [50.0, 75.0, 60.0, 80.0]

        for emission in emissions_sequence:
            kpi.record_carbon("carbon_test", emission)

        ship_kpi = kpi._ship_kpis["carbon_test"]
        expected_total = sum(emissions_sequence)

        assert ship_kpi.total_carbon == pytest.approx(expected_total, rel=0.001), \
            f"单船累计排放错误: 期望{expected_total}, 实际{ship_kpi.total_carbon}"


class TestDashboardDataConsistency:
    def test_dashboard_data_components(self):
        model = SimulationModel()
        _init_demo_scenario(model)

        kpi = get_kpi_calculator()
        kpi.reset()

        ships = [agent for agent in model._agents.values() if isinstance(agent, ShipAgent)]
        ports = [agent for agent in model._agents.values() if isinstance(agent, PortAgent)]

        for ship in ships[:3]:
            kpi.register_ship(ship.unique_id)
            kpi.record_arrival(ship.unique_id, 100.0, 102.0)
            kpi.record_arrival(ship.unique_id, 200.0, 198.0)
            kpi.record_carbon(ship.unique_id, 150.0)
            kpi.record_carbon(ship.unique_id, 160.0)

        dashboard = kpi.get_dashboard_data(sim_time=300.0)

        required_fields = ["sim_time", "on_time_rate", "avg_delay_hours",
                          "carbon_total", "total_arrivals", "on_time_arrivals", "ships_tracked"]

        for field in required_fields:
            assert field in dashboard, \
                f"仪表盘数据缺少字段: {field}"

        print(f"\n仪表盘数据一致性检查:")
        print(f"  仿真时间: {dashboard['sim_time']}")
        print(f"  准班率: {dashboard['on_time_rate']}%")
        print(f"  平均延误: {dashboard['avg_delay_hours']}h")
        print(f"  总碳排放: {dashboard['carbon_total']} 吨")
        print(f"  总到港次数: {dashboard['total_arrivals']}")
        print(f"  准班次数: {dashboard['on_time_arrivals']}")
        print(f"  跟踪船舶数: {dashboard['ships_tracked']}")

        manual_on_time = dashboard["on_time_arrivals"] / dashboard["total_arrivals"] if dashboard["total_arrivals"] > 0 else 1.0
        assert abs(dashboard["on_time_rate"]/100 - manual_on_time) < 0.01, \
            "仪表盘准班率与原始数据不一致"

    def test_snapshot_trend_data(self):
        kpi = KPICalculator()
        kpi.register_ship("trend_ship")

        snapshot_times = [0, 100, 200, 300]
        for t in snapshot_times:
            kpi.record_arrival("trend_ship", float(t), float(t + 2))
            snapshot = kpi.take_snapshot(float(t))

            assert snapshot.sim_time == t, \
                f"快照时间应为{t}，实际为{snapshot.sim_time}"
            assert snapshot.on_time_rate > 0, \
                f"快照的准班率应为正"
            assert snapshot.carbon_total >= 0, \
                f"快照的总碳排放不应为负"

        trend_data = kpi.get_trend_data()

        assert len(trend_data) == len(snapshot_times), \
            f"趋势数据点数应为{len(snapshot_times)}，实际为{len(trend_data)}"

        for i, trend in enumerate(trend_data):
            assert trend["time"] == snapshot_times[i], \
                f"趋势数据第{i}点时间不匹配"
            assert "on_time_rate" in trend and "carbon_total" in trend, \
                f"趋势数据第{i}点缺少必要字段"


class TestKPISystemIntegration:
    def test_full_simulation_kpi_consistency(self):
        model = SimulationModel()
        _init_demo_scenario(model)

        kpi = get_kpi_calculator()
        kpi.reset()

        max_steps = 500
        arrival_count = 0

        for step in range(max_steps):
            if model.scheduler.event_queue.is_empty():
                break

            event = model.scheduler.event_queue.peek()
            if event and event.event_type == EventType.ARRIVE_PORT:
                ship = model.get_agent(event.target_agent_id)
                if ship and isinstance(ship, ShipAgent):
                    port_id = event.payload.get("port_id", "")
                    scheduled = ship.schedule_time
                    actual = model.current_time

                    kpi.record_arrival(ship.unique_id, scheduled, actual)
                    arrival_count += 1

            model.scheduler.step()

        final_dashboard = kpi.get_dashboard_data(model.current_time)

        print(f"\n完整仿真KPI一致性检查:")
        print(f"  仿真步数: {step+1}")
        print(f"  总到港事件: {arrival_count}")
        print(f"  KPI记录到港: {final_dashboard['total_arrivals']}")
        print(f"  最终准班率: {final_dashboard['on_time_rate']}%")
        print(f"  平均延误: {final_dashboard['avg_delay_hours']}h")
        print(f"  总碳排放: {final_dashboard['carbon_total']} 吨")

        assert final_dashboard["total_arrivals"] >= arrival_count * 0.9, \
            "KPI到港次数与仿真事件数差异过大"
        assert 0.0 <= final_dashboard["on_time_rate"] <= 100.0, \
            "准班率应在0-100%范围内"


def _init_demo_scenario(model):
    from app.scheduler.scheduler import _init_demo_scenario as init
    init(model)
