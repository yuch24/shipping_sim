import asyncio
import sys

sys.path.insert(0, ".")


async def test():
    from app.scheduler.simulation_runner import (
        start_clock_async,
        get_clock_state,
        set_speed,
    )

    set_speed(3600.0)
    await start_clock_async()
    s = get_clock_state()
    print(f"0s: time={s['current_time']} running={s['is_running']}")
    await asyncio.sleep(2)
    s = get_clock_state()
    print(f"2s: time={s['current_time']:.1f}h")


asyncio.run(test())
