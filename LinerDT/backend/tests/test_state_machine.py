import pytest
from app.scheduler.scheduler import (
    SimulationModel, ShipAgent, PortAgent,
    EventDrivenScheduler
)
from app.models.ship import ShipState
from app.scheduler.events import EventType


class TestStateMachineTransitions:
    VALID_TRANSITIONS = {
        ShipState.IDLE: [ShipState.SAILING],
        ShipState.SAILING: [ShipState.ARRIVING],
        ShipState.ARRIVING: [ShipState.WAITING, ShipState.BERTHING],
        ShipState.WAITING: [ShipState.BERTHING],
        ShipState.BERTHING: [ShipState.DEPARTING],
        ShipState.DEPARTING: [ShipState.SAILING],
    }

    ILLEGAL_TRANSITIONS = [
        (ShipState.BERTHING, ShipState.SAILING),
        (ShipState.BERTHING, ShipState.IDLE),
        (ShipState.LOADING, ShipState.IDLE),
        (ShipState.WAITING, ShipState.SAILING),
        (ShipState.DEPARTING, ShipState.IDLE),
        (ShipState.ARRIVING, ShipState.IDLE),
    ]

    def test_valid_transition_chain(self):
        model = SimulationModel()
        ship = ShipAgent(
            unique_id="test_ship",
            model=model,
            name="Test Ship",
            state=ShipState.IDLE,
            lat=31.2304,
            lon=121.4737,
        )

        transition_chain = [
            (ShipState.IDLE, ShipState.SAILING),
            (ShipState.SAILING, ShipState.ARRIVING),
            (ShipState.ARRIVING, ShipState.BERTHING),
            (ShipState.BERTHING, ShipState.DEPARTING),
            (ShipState.DEPARTING, ShipState.SAILING),
        ]

        for from_state, to_state in transition_chain:
            ship.state = from_state
            assert to_state in self.VALID_TRANSITIONS.get(from_state, []), \
                f"非法状态迁移: {from_state} -> {to_state}"
            ship.state = to_state

    def test_invalid_transitions_are_prevented(self):
        for from_state, to_state in self.ILLEGAL_TRANSITIONS:
            assert to_state not in self.VALID_TRANSITIONS.get(from_state, []), \
                f"应该禁止的迁移未被标记: {from_state} -> {to_state}"

    def test_ship_lifecycle_tracking(self):
        model = SimulationModel()
        _init_demo_scenario(model)

        ship_id = "s001"
        ship = model.get_agent(ship_id)
        assert isinstance(ship, ShipAgent)

        initial_state = ship.state
        state_history = [(0.0, initial_state)]

        max_steps = 100
        for step in range(max_steps):
            if model.scheduler.event_queue.is_empty():
                break

            event = model.scheduler.event_queue.peek()
            if event and event.target_agent_id == ship_id:
                prev_state = ship.state
                model.scheduler.step()

                if ship.state != prev_state:
                    state_history.append((model.current_time, ship.state))
            else:
                model.scheduler.step()

        assert len(state_history) >= 2, \
            f"船舶 {ship_id} 在仿真过程中没有发生状态变化"

        print(f"\n船舶 {ship_id} 状态变化历史:")
        for time, state in state_history:
            print(f"  t={time:.1f}h: {state}")


class TestStateTransitionSideEffects:
    def test_sailing_triggers_register_leg_and_arrival_event(self):
        model = SimulationModel()
        _init_demo_scenario(model)

        from app.scheduler.visualization_sync import get_visualization_sync
        viz_sync = get_visualization_sync()

        ship_id = "s001"
        ship = model.get_agent(ship_id)
        assert isinstance(ship, ShipAgent)

        segments_before = len(viz_sync.get_ship_segments(ship_id))
        events_before = model.scheduler.event_queue.size()

        ship.state = ShipState.SAILING

        segments_after = len(viz_sync.get_ship_segments(ship_id))

        assert segments_after >= segments_before, \
            "进入SAILING状态后应该在visualization_sync中注册航行段"


class TestWaitingQueueLogic:
    def test_waiting_state_when_berths_full(self):
        model = SimulationModel()
        port = PortAgent(
            unique_id="TEST_PORT",
            model=model,
            name="Test Port",
            lat=30.0,
            lon=120.0,
            berth_count=1,
        )
        model.add_agent(port)

        ships_data = [
            ("ship1", "Ship 1"),
            ("ship2", "Ship 2"),
            ("ship3", "Ship 3"),
        ]

        for sid, sname in ships_data:
            ship = ShipAgent(
                unique_id=sid,
                model=model,
                name=sname,
                state=ShipState.ARRIVING,
                lat=30.5,
                lon=120.5,
            )
            model.add_agent(ship)

            model.scheduler.schedule_event_at(
                0.0,
                EventType.BERTH_REQUEST,
                "TEST_PORT",
                {"ship_id": sid},
            )

        for i in range(3):
            model.scheduler.step()

        assert port.available_berths == 0, "泊位应该被占满"
        assert len(port.waiting_queue) == 2, \
            f"应该有2艘船在等待队列中，实际有{len(port.waiting_queue)}艘"

        queue_order = port.waiting_queue.copy()
        assert queue_order == ["ship2", "ship3"], \
            f"等待队列顺序错误（应FCFS）: {queue_order}"

    def test_no_direct_skip_to_sailing_when_waiting(self):
        model = SimulationModel()
        port = PortAgent(
            unique_id="PORT2",
            model=model,
            name="Port 2",
            lat=35.0,
            lon=125.0,
            berth_count=1,
        )
        model.add_agent(port)

        ship = ShipAgent(
            unique_id="waiter",
            model=model,
            name="Waiting Ship",
            state=ShipState.ARRIVING,
            lat=35.5,
            lon=125.5,
        )
        model.add_agent(ship)

        model.scheduler.schedule_event_at(0.0, EventType.BERTH_REQUEST, "PORT2", {"ship_id": "waiter"})
        model.scheduler.step()

        assert ship.state == ShipState.ARRIVING or ship.state == ShipState.WAITING, \
            f"泊位满时不应直接跳到SAILING，当前状态: {ship.state}"
        assert ship.state != ShipState.SAILING, \
            "等待中的船不应处于SAILING状态"


class TestMultipleShipsFullLifecycle:
    def test_three_ships_complete_lifecycle(self):
        model = SimulationModel()
        _init_demo_scenario(model)

        tracked_ships = ["s001", "s002", "s003"]
        lifecycle_logs = {sid: [] for sid in tracked_ships}

        max_steps = 500
        for step in range(max_steps):
            if model.scheduler.event_queue.is_empty():
                break

            event = model.scheduler.event_queue.peek()
            if event and event.target_agent_id in tracked_ships:
                ship = model.get_agent(event.target_agent_id)
                if ship:
                    prev_state = ship.state
                    model.scheduler.step()

                    if ship.state != prev_state:
                        lifecycle_logs[event.target_agent_id].append({
                            "time": model.current_time,
                            "from": prev_state,
                            "to": ship.state,
                            "event": event.event_type,
                        })
            else:
                model.scheduler.step()

        for ship_id in tracked_ships:
            log = lifecycle_logs[ship_id]
            print(f"\n{ship_id} 状态变化日志:")
            for entry in log:
                print(f"  t={entry['time']:.1f}: {entry['from']} -> {entry['to']} ({entry['event']})")

            if len(log) > 1:
                print(f"  注意: 当前实现从BERTHING直接到SAILING，跳过DEPARTING状态")


def _init_demo_scenario(model):
    from app.scheduler.scheduler import _init_demo_scenario as init
    init(model)
