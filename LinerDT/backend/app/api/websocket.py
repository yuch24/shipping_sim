from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional
import asyncio
import json
from datetime import datetime

from ..scheduler.simulation_runner import (
    start_clock_async,
    stop_clock,
    set_speed as set_clock_speed,
    reset_clock,
    get_clock_state,
    set_state_broadcaster,
    is_running,
)
from ..data.timetable_engine import get_timetable_engine

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        dead = []
        for conn in self.active_connections:
            try:
                await conn.send_json(data)
            except Exception:
                dead.append(conn)
        for d in dead:
            self.disconnect(d)


manager = ConnectionManager()
set_state_broadcaster(manager.broadcast)


@router.websocket("/ws/sim")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    print(f"WebSocket connected. Total: {len(manager.active_connections)}")

    heartbeat_task = None

    try:

        async def send_heartbeat():
            while True:
                try:
                    await websocket.send_json(
                        {"type": "heartbeat", "time": datetime.now().isoformat()}
                    )
                    await asyncio.sleep(30)
                except Exception:
                    break

        heartbeat_task = asyncio.create_task(send_heartbeat())

        engine = get_timetable_engine()
        clock = get_clock_state()
        init_msg = {
            "type": "full_sync",
            "current_time": clock["current_time"],
            "is_running": clock["is_running"],
            "speed": clock["speed"],
            "simulation_mode": "academic",
            "trajectories": engine.to_frontend_json(),
            "ships": engine.get_all_ship_states(clock["current_time"]),
            "ports": engine.get_port_states(clock["current_time"]),
        }
        await websocket.send_json(init_msg)

        while True:
            try:
                data = await websocket.receive_text()
                msg = json.loads(data)

                if msg.get("action") == "ping":
                    await websocket.send_json(
                        {"type": "pong", "time": datetime.now().isoformat()}
                    )
                elif msg.get("action") == "start":
                    spd = msg.get("speed", 60.0)
                    set_clock_speed(spd)
                    await start_clock_async()
                    await manager.broadcast(get_full_sync_msg())
                elif msg.get("action") == "pause":
                    stop_clock()
                    await manager.broadcast(get_full_sync_msg())
                elif msg.get("action") == "set-speed":
                    set_clock_speed(msg.get("speed", 60.0))
                    await manager.broadcast(get_full_sync_msg())
                elif msg.get("action") == "reset":
                    stop_clock()
                    reset_clock()
                    await manager.broadcast(get_full_sync_msg())
                elif msg.get("action") == "get_state":
                    await websocket.send_json(get_full_sync_msg())
                elif msg.get("action") == "get_trajectories":
                    await websocket.send_json(
                        {
                            "type": "trajectories",
                            "data": engine.to_frontend_json(),
                        }
                    )

            except json.JSONDecodeError:
                pass
            except WebSocketDisconnect:
                break

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if heartbeat_task:
            heartbeat_task.cancel()
        manager.disconnect(websocket)
        print(f"WebSocket disconnected. Total: {len(manager.active_connections)}")


def get_full_sync_msg() -> dict:
    engine = get_timetable_engine()
    clock = get_clock_state()
    return {
        "type": "full_sync",
        "current_time": clock["current_time"],
        "is_running": clock["is_running"],
        "speed": clock["speed"],
        "simulation_mode": "academic",
        "ships": engine.get_all_ship_states(clock["current_time"]),
        "ports": engine.get_port_states(clock["current_time"]),
    }


ai_alert_connections: list[WebSocket] = []


@router.websocket("/ws/ai/alerts")
async def websocket_ai_alerts(websocket: WebSocket):
    await websocket.accept()
    ai_alert_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("action") == "ping":
                await websocket.send_json(
                    {"type": "pong", "time": datetime.now().isoformat()}
                )
    except Exception:
        pass
    finally:
        if websocket in ai_alert_connections:
            ai_alert_connections.remove(websocket)
