from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any

from ..data.timetable_engine import get_timetable_engine
from ..scheduler.simulation_runner import (
    start_clock_async,
    stop_clock,
    set_speed as set_clock_speed,
    reset_clock,
    get_clock_state,
)

router = APIRouter(prefix="/api/sim", tags=["simulation"])


class StartRequest(BaseModel):
    speed: Optional[float] = 60.0


class SpeedRequest(BaseModel):
    speed: float


class ResetRequest(BaseModel):
    pass


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/state")
async def get_state():
    engine = get_timetable_engine()
    clock = get_clock_state()
    return {
        "current_time": clock["current_time"],
        "is_running": clock["is_running"],
        "speed": clock["speed"],
        "simulation_mode": "academic",
        "ships": engine.get_all_ship_states(clock["current_time"]),
        "ports": engine.get_port_states(clock["current_time"]),
    }


@router.get("/trajectories")
async def get_trajectories():
    engine = get_timetable_engine()
    return engine.to_frontend_json()


@router.post("/start")
async def start_sim(req: StartRequest = StartRequest()):
    set_clock_speed(max(0.1, min(req.speed, 72000.0)))
    await start_clock_async()
    clock = get_clock_state()
    return {"status": "started", "speed": clock["speed"]}


@router.post("/pause")
async def pause_sim():
    stop_clock()
    return {"status": "paused"}


@router.post("/set-speed")
async def set_speed(req: SpeedRequest):
    set_clock_speed(max(0.1, min(req.speed, 72000.0)))
    clock = get_clock_state()
    return {"status": "ok", "speed": clock["speed"]}


@router.post("/reset")
async def reset_sim():
    stop_clock()
    reset_clock()
    return {"status": "reset", "time": 0.0}


@router.get("/routes")
async def get_routes():
    engine = get_timetable_engine()
    result = []
    for route_id, sched in engine.route_schedules.items():
        ships = [t for t in engine._trajectories.values() if t.service == route_id]
        result.append(
            {
                "route_id": route_id,
                "cycle_hours": sched[-1].eta_hours,
                "num_ships": len(ships),
                "ports": [ps.port_code for ps in sched],
            }
        )
    return result


@router.get("/ports")
async def get_ports():
    engine = get_timetable_engine()
    clock = get_clock_state()
    return engine.get_port_states(clock["current_time"])


@router.get("/ships")
async def get_ships():
    engine = get_timetable_engine()
    clock = get_clock_state()
    return engine.get_all_ship_states(clock["current_time"])
