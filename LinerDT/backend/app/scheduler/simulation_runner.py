"""
Virtual Clock — broadcasts simulation time at configurable speed.

Speed "x" meaning: x simulation-seconds per real-second.
Presets: 60x (1s=1min), 3600x (1s=1h), 7200x (1s=2h).

Internal: _speed stores the x multiplier. Conversion to hours:
  elapsed_sim_hours = elapsed_real_seconds * _speed / 3600
"""

import asyncio
import logging
import time
from typing import Callable, Awaitable, Optional

from ..data.timetable_engine import get_timetable_engine

logger = logging.getLogger(__name__)

SPEED_PRESETS = [60, 3600, 7200]

_global_clock_task: Optional[asyncio.Task] = None
_state_broadcaster: Optional[Callable[[dict], Awaitable[None]]] = None
_current_time: float = 0.0
_is_running: bool = False
_speed: float = 60.0
_last_broadcast_real: float = 0.0
_last_broadcast_sim: float = -1.0


def set_state_broadcaster(broadcaster: Callable[[dict], Awaitable[None]]) -> None:
    global _state_broadcaster
    _state_broadcaster = broadcaster


def get_clock_state() -> dict:
    return {
        "current_time": _current_time,
        "is_running": _is_running,
        "speed": _speed,
    }


def set_speed(s: float) -> None:
    global _speed
    _speed = max(1, min(72000, s))


def reset_clock() -> None:
    global _current_time, _is_running
    _current_time = 0.0
    _is_running = False


async def _broadcast(data: dict) -> None:
    if _state_broadcaster is None:
        return
    try:
        await _state_broadcaster(data)
    except Exception as e:
        logger.debug("Broadcast failed: %s", e)


async def _clock_loop():
    global _current_time, _last_broadcast_real, _last_broadcast_sim, _is_running

    logger.info(f"Clock loop started, speed={_speed}x, is_running={_is_running}")
    engine = get_timetable_engine()
    logger.info(f"Engine loaded, {len(engine._trajectories)} ships")
    _last_broadcast_real = time.monotonic()
    _last_broadcast_sim = -1.0

    try:
        while _is_running:
            real_now = time.monotonic()
            elapsed_real = real_now - _last_broadcast_real
            elapsed_sim_hours = elapsed_real * _speed / 3600.0
            _current_time += elapsed_sim_hours
            _last_broadcast_real = real_now

            broadcast_interval_hours = max(0.5, _speed / 3600.0 * 0.1)
            if _current_time - _last_broadcast_sim >= broadcast_interval_hours:
                ships = engine.get_all_ship_states(_current_time)
                ports = engine.get_port_states(_current_time)
                await _broadcast(
                    {
                        "type": "clock_update",
                        "current_time": round(_current_time, 2),
                        "is_running": True,
                        "speed": _speed,
                        "ships": ships,
                        "ports": ports,
                    }
                )
                _last_broadcast_sim = _current_time

            await asyncio.sleep(0.05)

    except asyncio.CancelledError:
        logger.info("Clock task cancelled")
    except Exception:
        logger.exception("Clock loop error")
    finally:
        _is_running = False


async def start_clock_async() -> None:
    global _global_clock_task, _is_running, _last_broadcast_real
    _is_running = True
    _last_broadcast_real = time.monotonic()
    if _global_clock_task is None or _global_clock_task.done():
        _global_clock_task = asyncio.create_task(_clock_loop())
        _global_clock_task.add_done_callback(_on_done)
        logger.info(f"Clock task created, speed={_speed}x")
        await asyncio.sleep(0)
        if _global_clock_task.done():
            try:
                exc = _global_clock_task.exception()
                logger.error(f"Clock task failed immediately: {exc}")
            except asyncio.CancelledError:
                logger.error("Clock task cancelled immediately")
    else:
        logger.info(f"Clock task already running, speed={_speed}x")


def stop_clock() -> None:
    global _global_clock_task, _is_running
    _is_running = False
    if _global_clock_task is not None:
        _global_clock_task.cancel()
        _global_clock_task = None


def _on_done(task: asyncio.Task) -> None:
    try:
        exc = task.exception()
        if exc and not isinstance(exc, asyncio.CancelledError):
            logger.error("Clock task failed: %s", exc)
    except asyncio.CancelledError:
        pass


def is_running() -> bool:
    return _is_running
