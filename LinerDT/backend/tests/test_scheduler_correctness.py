import pytest
from app.scheduler.event_queue import EventQueue, Event
from app.scheduler.scheduler import EventDrivenScheduler, SimulationModel, ShipAgent, PortAgent
from app.models.ship import ShipState
from app.scheduler.events import EventType


class TestEventSchedulingOrder:
    def test_events_pop_in_strictly_increasing_time_order(self):
        eq = EventQueue()
        events_data = [
            (100.0, "event_100", "ship1"),
            (50.0, "event_50", "ship2"),
            (200.0, "event_200", "ship1"),
            (10.0, "event_10", "ship3"),
            (75.0, "event_75", "ship2"),
            (150.0, "event_150", "ship1"),
        ]
        for time, etype, target in events_data:
            eq.push(Event(time=time, event_type=etype, target_agent_id=target))

        popped_times = []
        while not eq.is_empty():
            event = eq.pop()
            popped_times.append(event.time)

        for i in range(1, len(popped_times)):
            assert popped_times[i] > popped_times[i-1], \
                f"事件时序错误: 第{i}个事件时间{popped_times[i]} <= 第{i-1}个事件时间{popped_times[i-1]}"

    def test_out_of_order_insertion_maintains_order(self):
        eq = EventQueue()
        times = [5.0, 1.0, 3.0, 4.0, 2.0]
        for t in times:
            eq.push(Event(time=t, event_type="test", target_agent_id="s1"))

        prev_time = -float('inf')
        while not eq.is_empty():
            event = eq.pop()
            assert event.time > prev_time, f"乱序插入后弹出顺序错误"
            prev_time = event.time

    def test_large_number_of_events_order(self):
        import random
        random.seed(42)
        eq = EventQueue()

        for i in range(1000):
            time = random.uniform(0, 10000)
            eq.push(Event(time=time, event_type=f"e{i}", target_agent_id=f"ship{i % 10}"))

        prev_time = -float('inf')
        count = 0
        while not eq.is_empty():
            event = eq.pop()
            assert event.time >= prev_time, f"大规模测试中第{count}个事件时序错误"
            prev_time = event.time
            count += 1

        assert count == 1000


class TestNoEventLoss:
    def setup_method(self):
        self.model = SimulationModel()
        _init_demo_scenario(self.model)

    def test_all_ships_have_arrival_events(self):
        total_events_before = self.model.scheduler.event_queue.size()

        steps = self.model.scheduler.run_until(end_time=720.0)  # 运行30天（小时）

        ships = [agent for agent in self.model._agents.values() if isinstance(agent, ShipAgent)]
        for ship in ships:
            arrival_count = sum(
                1 for log in ship.decision_log
                if log.get("event") == EventType.ARRIVE_PORT
            )
            assert arrival_count > 0, f"船舶 {ship.unique_id} 没有任何到港记录"

    def test_no_events_lost_during_long_simulation(self):
        initial_event_count = self.model.scheduler.event_queue.size()
        steps_run = self.model.scheduler.run_until(end_time=720.0)

        assert steps_run > 0, "仿真应该执行了至少一个步骤"


class TestEventDeadlockDetection:
    def test_no_orphaned_events_after_simulation(self):
        model = SimulationModel()
        _init_demo_scenario(model)

        model.scheduler.run_until(end_time=480.0)  # 运行20天

        remaining_events = model.scheduler.event_queue.to_list()
        for event_data in remaining_events:
            event = Event(**event_data)
            agent = model.get_agent(event.target_agent_id)
            assert agent is not None, \
                f"发现死锁事件: 时间={event.time}, 类型={event.event_type}, 目标Agent={event.target_agent_id} 不存在"

    def test_all_target_agents_exist_in_scheduler(self):
        model = SimulationModel()
        _init_demo_scenario(model)

        model.scheduler.run_until(end_time=240.0)

        queue_list = model.scheduler.event_queue.to_list()
        valid_agent_ids = set(model._agents.keys())

        for event_data in queue_list:
            assert event_data["target_agent_id"] in valid_agent_ids, \
                f"事件目标Agent不存在: {event_data['target_agent_id']}"


class TestZeroTimestepEventHandling:
    def test_simultaneous_events_all_processed(self):
        eq = EventQueue()
        same_time = 100.0

        eq.push(Event(time=same_time, event_type="arrive_A", target_agent_id="ship1"))
        eq.push(Event(time=same_time, event_type="arrive_B", target_agent_id="ship2"))
        eq.push(Event(time=same_time, event_type="arrive_C", target_agent_id="ship3"))

        processed_types = []
        while not eq.is_empty():
            event = eq.pop()
            processed_types.append(event.event_type)
            assert event.time == same_time

        assert len(processed_types) == 3, \
            f"同时刻事件丢失! 应处理3个, 实际处理{len(processed_types)}个"
        assert set(processed_types) == {"arrive_A", "arrive_B", "arrive_C"}

    def test_simultaneous_events_fifo_order(self):
        eq = EventQueue()
        same_time = 50.0

        insertion_order = ["first", "second", "third", "fourth"]
        for etype in insertion_order:
            eq.push(Event(time=same_time, event_type=etype, target_agent_id="s1"))

        popped_order = []
        while not eq.is_empty():
            event = eq.pop()
            popped_order.append(event.event_type)

        assert popped_order == insertion_order, \
            f"同时刻事件FIFO顺序错误: 插入顺序={insertion_order}, 弹出顺序={popped_order}"

    def test_many_simultaneous_events_no_loss(self):
        eq = EventQueue()
        same_time = 200.0

        for i in range(50):
            eq.push(Event(time=same_time, event_type=f"event_{i}", target_agent_id=f"ship{i}"))

        processed_count = 0
        while not eq.is_empty():
            eq.pop()
            processed_count += 1

        assert processed_count == 50, f"50个同时刻事件只处理了{processed_count}个"


def _init_demo_scenario(model):
    from app.scheduler.scheduler import _init_demo_scenario as init
    init(model)
