from typing import Any

from ..data.timetable_engine import get_timetable_engine
from ..scheduler.simulation_runner import get_clock_state


class StateSerializer:
    @staticmethod
    def serialize_state(sim_time_h: float) -> dict[str, Any]:
        engine = get_timetable_engine()
        clock = get_clock_state()
        return {
            "current_time": clock["current_time"],
            "is_running": clock["is_running"],
            "speed": clock["speed"],
            "simulation_mode": "academic",
            "ships": engine.get_all_ship_states(sim_time_h),
            "ports": engine.get_port_states(sim_time_h),
        }

    @staticmethod
    def serialize_delta(sim_time_h: float) -> dict[str, Any]:
        engine = get_timetable_engine()
        clock = get_clock_state()
        return {
            "type": "clock_update",
            "current_time": round(sim_time_h, 2),
            "is_running": clock["is_running"],
            "speed": clock["speed"],
            "ships": engine.get_all_ship_states(sim_time_h),
            "ports": engine.get_port_states(sim_time_h),
        }


def serialize_simulation_state(sim_time_h: float) -> dict[str, Any]:
    return StateSerializer.serialize_state(sim_time_h)


def serialize_delta_state(sim_time_h: float) -> dict[str, Any]:
    return StateSerializer.serialize_delta(sim_time_h)
