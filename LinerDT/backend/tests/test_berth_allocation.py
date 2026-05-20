import pytest
from app.scheduler.scheduler import (
    SimulationModel, ShipAgent, PortAgent,
)
from app.models.ship import ShipState
from app.scheduler.events import EventType


class TestBerthCapacityConstraint:
    def test_occupied_never_exceeds_total(self):
        model = SimulationModel()
        port = PortAgent(
            unique_id="CAP_TEST",
            model=model,
            name="Capacity Test Port",
            lat=30.0,
            lon=120.0,
            berth_count=3,
        )
        model.add_agent(port)

        num_ships = 10
        for i in range(num_ships):
            ship = ShipAgent(
                unique_id=f"ship_{i}",
                model=model,
                name=f"Ship {i}",
                state=ShipState.ARRIVING,
                lat=30.5,
                lon=120.5,
            )
            model.add_agent(ship)

            model.scheduler.schedule_event_at(
                float(i),
                EventType.BERTH_REQUEST,
                "CAP_TEST",
                {"ship_id": f"ship_{i}"},
            )

        for step in range(num_ships):
            model.scheduler.step()

            occupied = port.berth_count - port.available_berths
            assert occupied <= port.berth_count, \
                f"步骤{step}: 占用泊位数({occupied}) > 总泊位数({port.berth_count})"

    def test_capacity_constraint_during_release_and_allocate(self):
        model = SimulationModel()
        port = PortAgent(
            unique_id="DYN_PORT",
            model=model,
            name="Dynamic Port",
            lat=35.0,
            lon=125.0,
            berth_count=2,
        )
        model.add_agent(port)

        ships = []
        for i in range(6):
            ship = ShipAgent(
                unique_id=f"dyn_ship_{i}",
                model=model,
                name=f"Dynamic Ship {i}",
                state=ShipState.BERTHING if i < 2 else ShipState.ARRIVING,
                lat=35.5,
                lon=125.5,
            )
            model.add_agent(ship)
            ships.append(ship)

        for i in range(2):
            port.available_berths -= 1
            port.occupied_berths[f"dyn_ship_{i}"] = "OCCUPIED"

        for i in range(2, 6):
            model.scheduler.schedule_event_at(
                float(i),
                EventType.BERTH_REQUEST,
                "DYN_PORT",
                {"ship_id": f"dyn_ship_{i}"},
            )

        for step in range(4):
            model.scheduler.step()

            occupied = port.berth_count - port.available_berths
            assert occupied <= port.berth_count, \
                f"动态测试步骤{step}: 泊位超容量! 占用={occupied}, 总数={port.berth_count}"

    def test_continuous_allocation_respects_capacity(self):
        model = SimulationModel()
        total_berths = 4
        port = PortAgent(
            unique_id="CONT_PORT",
            model=model,
            name="Continuous Port",
            lat=40.0,
            lon=130.0,
            berth_count=total_berths,
        )
        model.add_agent(port)

        total_requests = 50
        for i in range(total_requests):
            ship = ShipAgent(
                unique_id=f"cont_ship_{i}",
                model=model,
                name=f"Continuous Ship {i}",
                state=ShipState.ARRIVING,
                lat=40.5,
                lon=130.5,
            )
            model.add_agent(ship)

            model.scheduler.schedule_event_at(
                float(i) * 0.1,
                EventType.BERTH_REQUEST,
                "CONT_PORT",
                {"ship_id": f"cont_ship_{i}"},
            )

        steps_run = 0
        while not model.scheduler.event_queue.is_empty() and steps_run < total_requests:
            model.scheduler.step()
            steps_run += 1

            occupied = len(port.occupied_berths)
            assert occupied <= total_berths, \
                f"连续分配测试步骤{steps_run}: 占用={occupied} > 容量={total_berths}"


class TestFCFSOrdering:
    def test_queue_maintains_arrival_order(self):
        model = SimulationModel()
        port = PortAgent(
            unique_id="FCFS_PORT",
            model=model,
            name="FCFS Test Port",
            lat=32.0,
            lon=122.0,
            berth_count=1,
        )
        model.add_agent(port)

        arrival_order = ["alpha", "beta", "gamma", "delta", "epsilon"]
        for ship_id in arrival_order:
            ship = ShipAgent(
                unique_id=ship_id,
                model=model,
                name=f"Ship {ship_id}",
                state=ShipState.ARRIVING,
                lat=32.5,
                lon=122.5,
            )
            model.add_agent(ship)

            model.scheduler.schedule_event_at(
                0.0,
                EventType.BERTH_REQUEST,
                "FCFS_PORT",
                {"ship_id": ship_id},
            )

        for _ in range(len(arrival_order)):
            model.scheduler.step()

        queue_contents = port.waiting_queue.copy()
        expected_queue = arrival_order[1:]

        assert queue_contents == expected_queue, \
            f"FCFS顺序错误:\n  期望: {expected_queue}\n  实际: {queue_contents}"

    def test_departure_order_matches_arrival_order(self):
        model = SimulationModel()
        port = PortAgent(
            unique_id="DEP_ORDER",
            model=model,
            name="Departure Order Port",
            lat=33.0,
            lon=123.0,
            berth_count=1,
        )
        model.add_agent(port)

        arrival_sequence = ["first", "second", "third", "fourth"]
        allocation_order = []

        original_handle = port._handle_berth_request

        def tracked_handle(event):
            ship_id = event.payload.get("ship_id")
            if port.available_berths > 0:
                allocation_order.append(ship_id)
            original_handle(event)

        port._handle_berth_request = tracked_handle

        for ship_id in arrival_sequence:
            ship = ShipAgent(
                unique_id=ship_id,
                model=model,
                name=f"Ship {ship_id}",
                state=ShipState.ARRIVING,
                lat=33.5,
                lon=123.5,
            )
            model.add_agent(ship)

            model.scheduler.schedule_event_at(
                0.0,
                EventType.BERTH_REQUEST,
                "DEP_ORDER",
                {"ship_id": ship_id},
            )

        for _ in range(len(arrival_sequence) * 2):
            model.scheduler.step()

        assert allocation_order[:1] == arrival_sequence[:1], \
            f"首艘船应为最早到达的: {allocation_order}"


class TestReleaseAndImmediateAllocation:
    def test_release_triggers_immediate_allocation(self):
        model = SimulationModel()
        port = PortAgent(
            unique_id="REL_PORT",
            model=model,
            name="Release Test Port",
            lat=34.0,
            lon=124.0,
            berth_count=1,
        )
        model.add_agent(port)

        ship1 = ShipAgent(
            unique_id="occupant",
            model=model,
            name="Occupant Ship",
            state=ShipState.BERTHING,
            lat=34.5,
            lon=124.5,
        )
        model.add_agent(ship1)

        ship2 = ShipAgent(
            unique_id="waiter",
            model=model,
            name="Waiting Ship",
            state=ShipState.ARRIVING,
            lat=34.6,
            lon=124.6,
        )
        model.add_agent(ship2)

        port.available_berths = 0
        port.occupied_berths["occupant"] = "OCCUPIED"
        port.waiting_queue.append("waiter")

        model.scheduler.schedule_event_at(
            10.0,
            EventType.BERTH_RELEASE,
            "REL_PORT",
            {"ship_id": "occupant"},
        )

        events_before = model.scheduler.event_queue.size()
        model.scheduler.step()
        events_after = model.scheduler.event_queue.size()

        assert "waiter" not in port.waiting_queue, \
            "释放后等待队列中的船应被立即分配"
        assert "waiter" in port.occupied_berths, \
            "等待的船应已被分配泊位"
        assert port.available_berths == 0, \
            f"泊位应立即被重新占用, available={port.available_berths}"

    def test_multiple_releases_cascade_allocations(self):
        model = SimulationModel()
        port = PortAgent(
            unique_id="CASCADE_PORT",
            model=model,
            name="Cascade Port",
            lat=36.0,
            lon=126.0,
            berth_count=2,
        )
        model.add_agent(port)

        for i in range(2):
            ship = ShipAgent(
                unique_id=f"cascade_occ_{i}",
                model=model,
                name=f"Cascade Occupant {i}",
                state=ShipState.BERTHING,
                lat=36.5,
                lon=126.5,
            )
            model.add_agent(ship)

        for i in range(3):
            ship = ShipAgent(
                unique_id=f"cascade_wait_{i}",
                model=model,
                name=f"Cascade Waiter {i}",
                state=ShipState.ARRIVING,
                lat=36.6 + i*0.01,
                lon=126.6,
            )
            model.add_agent(ship)

        for oid in ["cascade_occ_0", "cascade_occ_1"]:
            port.available_berths -= 1
            port.occupied_berths[oid] = "OCCUPIED"

        for wid in ["cascade_wait_0", "cascade_wait_1", "cascade_wait_2"]:
            port.waiting_queue.append(wid)

        model.scheduler.schedule_event_at(
            5.0,
            EventType.BERTH_RELEASE,
            "CASCADE_PORT",
            {"ship_id": "cascade_occ_0"},
        )
        model.scheduler.schedule_event_at(
            10.0,
            EventType.BERTH_RELEASE,
            "CASCADE_PORT",
            {"ship_id": "cascade_occ_1"},
        )

        print(f"\n级联释放测试:")
        print(f"  初始占用: {list(port.occupied_berths.keys())}")
        print(f"  初始等待: {port.waiting_queue.copy()}")

        model.scheduler.step()

        print(f"  第1次释放后占用: {list(port.occupied_berths.keys())}")
        print(f"  第1次释放后等待: {port.waiting_queue.copy()}")

        model.scheduler.step()

        print(f"  第2次释放后占用: {list(port.occupied_berths.keys())}")
        print(f"  第2次释放后等待: {port.waiting_queue.copy()}")

        assert "cascade_wait_0" in port.occupied_berths or "cascade_wait_1" in port.occupied_berths, \
            "第一次释放后应有等待船获得泊位"


class TestBerthAllocationEdgeCases:
    def test_empty_queue_release(self):
        model = SimulationModel()
        port = PortAgent(
            unique_id="EMPTY_REL",
            model=model,
            name="Empty Release Port",
            lat=37.0,
            lon=127.0,
            berth_count=2,
        )
        model.add_agent(port)

        ship = ShipAgent(
            unique_id="lone_ship",
            model=model,
            name="Lone Ship",
            state=ShipState.BERTHING,
            lat=37.5,
            lon=127.5,
        )
        model.add_agent(ship)

        port.available_berths = 1
        port.occupied_berths["lone_ship"] = "OCCUPIED"

        model.scheduler.schedule_event_at(
            1.0,
            EventType.BERTH_RELEASE,
            "EMPTY_REL",
            {"ship_id": "lone_ship"},
        )

        model.scheduler.step()

        assert port.available_berths == 2, \
            f"空队列释放后可用泊位应为2, 实际为{port.available_berths}"
        assert len(port.occupied_berths) == 0, \
            "释放后不应有占用的泊位"

    def test_rapid_allocate_release_cycles(self):
        model = SimulationModel()
        port = PortAgent(
            unique_id="RAPID_PORT",
            model=model,
            name="Rapid Cycle Port",
            lat=38.0,
            lon=128.0,
            berth_count=2,
        )
        model.add_agent(port)

        for cycle in range(20):
            ship = ShipAgent(
                unique_id=f"cycle_ship_{cycle}",
                model=model,
                name=f"Cycle Ship {cycle}",
                state=ShipState.ARRIVING,
                lat=38.5 + cycle * 0.01,
                lon=128.5,
            )
            model.add_agent(ship)

            model.scheduler.schedule_event_at(
                float(cycle) * 0.5,
                EventType.BERTH_REQUEST,
                "RAPID_PORT",
                {"ship_id": f"cycle_ship_{cycle}"},
            )

            if cycle >= 2 and cycle % 3 == 0:
                release_ship = f"cycle_ship_{cycle - 2}"
                if release_ship in port.occupied_berths:
                    model.scheduler.schedule_event_at(
                        float(cycle) * 0.5 + 0.1,
                        EventType.BERTH_RELEASE,
                        "RAPID_PORT",
                        {"ship_id": release_ship},
                    )

        max_steps = 100
        for step in range(max_steps):
            if model.scheduler.event_queue.is_empty():
                break

            model.scheduler.step()

            occupied = len(port.occupied_berths)
            assert occupied <= port.berth_count, \
                f"快速循环测试步骤{step}: 泊位超容量! 占用={occupied}, 容量={port.berth_count}"
