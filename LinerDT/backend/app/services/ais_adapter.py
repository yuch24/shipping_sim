"""
AIS 数据适配器

支持两种模式：
1. 真实模式：连接 AisStream.io WebSocket 获取实时 AIS 数据
2. Mock 模式：基于仿真 ShipAgent 当前位置生成模拟 AIS 数据（比赛演示用，离线可用）

比赛现场使用 MOCK 模式（不依赖网络）。
架构已预留真实连接接口，可通过 API Key 切换。
"""

import asyncio
import json
import os
import random
import logging
from typing import Optional, Callable, Awaitable

from app.services.ais_parser import parse_ais_message, filter_duplicates
from app.core.config import settings

logger = logging.getLogger(__name__)


class AISDataAdapter:
    """
    AIS 数据适配器

    用法：
        adapter = AISDataAdapter()
        adapter.set_ship_data_provider(my_data_func)   # 注册 mock 数据源
        await adapter.start(mode="mock")

    回调 pipeline:
        AIS stream → parse_ais_message() → callback(dict)

    API Key 优先级：构造函数参数 > 环境变量 AISSTREAM_API_KEY
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.aisstream_api_key or os.getenv("AISSTREAM_API_KEY", "")
        self._websocket = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._on_data: Optional[Callable[[dict], Awaitable[None]]] = None

        # Mock 数据源：由外部注册，返回 [ship_id, lat, lon, sog, cog]
        self._ship_data_provider: Optional[Callable[[], list[dict]]] = None

        # 内部缓冲队列（用于真实模式节流）
        self._buffer: list[dict] = []
        self._last_broadcast_time = 0.0
        self._batch_max_size = 100
        self._batch_timeout_ms = 500  # 0.5 秒超时刷新

    def set_data_callback(self, callback: Callable[[dict], Awaitable[None]]) -> None:
        """注册数据回调（由 simulation_runner 注册）"""
        self._on_data = callback

    def set_ship_data_provider(self, provider: Callable[[], list[dict]]) -> None:
        """注册船舶数据源（用于 Mock 模式）"""
        self._ship_data_provider = provider

    async def start(self, mode: str = "mock") -> None:
        """启动 AIS 数据流"""
        if self._running:
            return
        self._running = True

        if mode == "mock":
            self._task = asyncio.create_task(self._run_mock_loop())
            logger.info("AIS adapter started in MOCK mode")
        else:
            self._task = asyncio.create_task(self._run_real_loop())
            logger.info("AIS adapter started in REAL mode")

    async def stop(self) -> None:
        """停止 AIS 数据流"""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
        logger.info("AIS adapter stopped")

    async def _run_mock_loop(self) -> None:
        """Mock 模式：从 ship_data_provider 获取船舶位置，模拟 AIS 推送"""
        tick = 0
        while self._running:
            try:
                if self._ship_data_provider:
                    ships = self._ship_data_provider()
                    for ship in ships:
                        # 为每个船舶添加轻微随机偏移，模拟真实 AIS 抖动
                        ais_msg = {
                            "ship_id": ship.get("ship_id", ship.get("unique_id", "0")),
                            "lat": ship.get("lat", 0.0) + random.uniform(-0.01, 0.01),
                            "lon": ship.get("lon", 0.0) + random.uniform(-0.01, 0.01),
                            "sog": ship.get("current_speed", ship.get("speed", 0)),
                            "cog": random.uniform(0, 360),
                            "timestamp": f"2026-{tick:06d}",
                            "source": "ais_mock",
                        }
                        parsed = parse_ais_message(ais_msg)
                        if parsed and self._on_data:
                            await self._on_data(parsed)

                tick += 1
                # Mock 模式每秒推送一批数据
                await asyncio.sleep(1.0)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Mock AIS error: {e}")
                await asyncio.sleep(1.0)

    async def _run_real_loop(self) -> None:
        """真实模式：连接 AisStream.io WebSocket（比赛现场可能不可用）"""
        import websockets

        uri = "wss://stream.aisstream.io/v0/stream"
        try:
            async with websockets.connect(uri) as ws:
                self._websocket = ws
                subscribe_msg = {
                    "APIKey": self.api_key,
                    "BoundingBoxes": [[[-90, -180], [90, 180]]],
                }
                await ws.send(json.dumps(subscribe_msg))

                async for raw_message in ws:
                    if not self._running:
                        break
                    try:
                        data = json.loads(raw_message)
                        parsed = parse_ais_message(data)
                        if parsed and self._on_data:
                            now = asyncio.get_event_loop().time()
                            self._buffer.append(parsed)
                            should_flush = len(self._buffer) >= 100 or (
                                self._buffer and (now - self._last_broadcast_time) > 0.5
                            )
                            if should_flush:
                                batch = filter_duplicates(self._buffer)
                                for msg in batch:
                                    await self._on_data(msg)
                                self._buffer = []
                                self._last_broadcast_time = now
                    except json.JSONDecodeError:
                        continue

        except (asyncio.CancelledError, Exception) as e:
            logger.warning(f"Real AIS connection failed/stopped: {e}")
            # 真实连接失败时自动回退到 Mock 模式
            if self._running:
                logger.info("Falling back to MOCK AIS mode")
                self._task = asyncio.create_task(self._run_mock_loop())
