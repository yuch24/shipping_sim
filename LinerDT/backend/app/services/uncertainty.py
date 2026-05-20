"""
不确定性引擎。

管理仿真中所有随机变量，使用可配置的 Distribution 对象。
支持 JSON 序列化/反序列化，可复现的种子控制。
"""

import threading
from typing import Optional

from .distributions import (
    Distribution, NormalDist, UniformDist, BernoulliDist,
    distribution_from_dict, get_distribution_schema,
)


class UncertaintyEngine:
    def __init__(
        self,
        seed: Optional[int] = None,
        # 可配置的分布对象
        port_delay_dist: Optional[Distribution] = None,
        congestion_extra_dist: Optional[Distribution] = None,
        weather_delay_prob_dist: Optional[Distribution] = None,
        weather_delay_dist: Optional[Distribution] = None,
        berth_occupancy_dists: Optional[dict[str, Distribution]] = None,
        loading_delay_dist: Optional[Distribution] = None,
        delay_chain_variation_dist: Optional[Distribution] = None,
    ):
        import random
        if seed is not None:
            random.seed(seed)

        # 默认：匹配原始硬编码值
        self.port_delay_dist = port_delay_dist or NormalDist(4.0, 2.0, min_val=0)
        self.congestion_extra_dist = congestion_extra_dist or UniformDist(8.0, 24.0)
        self.weather_delay_prob_dist = weather_delay_prob_dist or BernoulliDist(0.3)
        self.weather_delay_dist = weather_delay_dist or NormalDist(0, 4.0, min_val=0)
        self.berth_occupancy_dists = berth_occupancy_dists or {
            "empty": UniformDist(0.6, 0.8),
            "low": UniformDist(0.8, 0.9),
            "medium": UniformDist(0.9, 1.0),
            "high": UniformDist(1.0, 1.2),
        }
        self.loading_delay_dist = loading_delay_dist or NormalDist(1.0, 0.1, min_val=0.5, max_val=1.5)
        self.delay_chain_variation_dist = delay_chain_variation_dist or UniformDist(0.8, 1.2)

        self._weather_zones = self._init_weather_zones()
        self._port_delay_multipliers = {}

    def _init_weather_zones(self) -> dict:
        return {
            "SCS": {"name": "South China Sea", "base_delay": 0.1},
            "IO": {"name": "Indian Ocean", "base_delay": 0.15},
            "MOS": {"name": "Mediterranean/Red Sea", "base_delay": 0.12},
            "ATL": {"name": "North Atlantic", "base_delay": 0.2},
        }

    def get_port_delay(self, port_id: str, congestion_level: float = 0.0) -> float:
        base_delay = self.port_delay_dist.sample()
        congestion_extra = congestion_level * self.congestion_extra_dist.sample()
        total_delay = base_delay + congestion_extra
        self._port_delay_multipliers[port_id] = total_delay
        return max(0.0, total_delay)

    def get_weather_delay(
        self, start_lat: float, start_lon: float, end_lat: float, end_lon: float
    ) -> float:
        mid_lat = (start_lat + end_lat) / 2
        mid_lon = (start_lon + end_lon) / 2

        zone_key = self._determine_weather_zone(mid_lat, mid_lon)
        zone = self._weather_zones.get(zone_key, {"base_delay": 0.05})

        # 天气延误触发判断
        if self.weather_delay_prob_dist.sample() == 0.0:
            return 0.0

        # 使用带基数的天气延误分布
        delay = self.weather_delay_dist.sample() + zone["base_delay"] * 24
        return max(0.0, delay)

    def _determine_weather_zone(self, lat: float, lon: float) -> Optional[str]:
        if 5 <= lat <= 25 and 105 <= lon <= 125:
            return "SCS"
        if -30 <= lat <= 30 and 40 <= lon <= 100:
            return "IO"
        if 25 <= lat <= 50 and -20 <= lon <= 40:
            return "MOS"
        if 40 <= lat <= 65 and -60 <= lon <= 0:
            return "ATL"
        return None

    def get_berth_occupancy_factor(self, port_id: str, current_queue_length: int) -> float:
        if current_queue_length == 0:
            return self.berth_occupancy_dists["empty"].sample()
        if current_queue_length <= 2:
            return self.berth_occupancy_dists["low"].sample()
        if current_queue_length <= 4:
            return self.berth_occupancy_dists["medium"].sample()
        return self.berth_occupancy_dists["high"].sample()

    def get_loading_delay_factor(self, port_id: str) -> float:
        return self.loading_delay_dist.sample()

    def inject_delay_chain(
        self,
        current_delay: float,
        num_segments: int,
        decay_rate: float = 0.3
    ) -> list[float]:
        delays = [current_delay]
        for i in range(1, num_segments):
            decay = decay_rate ** i
            variation = self.delay_chain_variation_dist.sample()
            delayed = delays[-1] * decay * variation
            delays.append(max(0.0, delayed))
        return delays

    def to_config(self) -> dict:
        """序列化为可 JSON 传输的配置字典。"""
        return {
            "port_delay_dist": self.port_delay_dist.to_dict(),
            "congestion_extra_dist": self.congestion_extra_dist.to_dict(),
            "weather_delay_prob_dist": self.weather_delay_prob_dist.to_dict(),
            "weather_delay_dist": self.weather_delay_dist.to_dict(),
            "berth_occupancy_dists": {
                k: v.to_dict() for k, v in self.berth_occupancy_dists.items()
            },
            "loading_delay_dist": self.loading_delay_dist.to_dict(),
            "delay_chain_variation_dist": self.delay_chain_variation_dist.to_dict(),
        }

    @classmethod
    def from_config(cls, config: dict, seed: Optional[int] = None) -> "UncertaintyEngine":
        """从配置字典重建引擎。"""
        return cls(
            seed=seed,
            port_delay_dist=distribution_from_dict(config.get("port_delay_dist", NormalDist(4.0, 2.0, min_val=0).to_dict())),
            congestion_extra_dist=distribution_from_dict(config.get("congestion_extra_dist", UniformDist(8.0, 24.0).to_dict())),
            weather_delay_prob_dist=distribution_from_dict(config.get("weather_delay_prob_dist", BernoulliDist(0.3).to_dict())),
            weather_delay_dist=distribution_from_dict(config.get("weather_delay_dist", NormalDist(0, 4.0, min_val=0).to_dict())),
            berth_occupancy_dists={
                k: distribution_from_dict(v)
                for k, v in config.get("berth_occupancy_dists", {}).items()
            } if "berth_occupancy_dists" in config else None,
            loading_delay_dist=distribution_from_dict(config.get("loading_delay_dist", NormalDist(1.0, 0.1, min_val=0.5, max_val=1.5).to_dict())),
            delay_chain_variation_dist=distribution_from_dict(config.get("delay_chain_variation_dist", UniformDist(0.8, 1.2).to_dict())),
        )


_uncertainty_lock: threading.Lock = threading.Lock()
_uncertainty_engine: Optional[UncertaintyEngine] = None


def get_uncertainty_engine() -> UncertaintyEngine:
    global _uncertainty_engine
    if _uncertainty_engine is None:
        with _uncertainty_lock:
            if _uncertainty_engine is None:
                _uncertainty_engine = UncertaintyEngine()
    return _uncertainty_engine


def set_uncertainty_engine(engine: UncertaintyEngine) -> None:
    """设置全局不确定性引擎（用于从配置重建）。"""
    global _uncertainty_engine
    _uncertainty_engine = engine


def reset_uncertainty_engine() -> None:
    """重置不确定性引擎（用于仿真重置）。"""
    global _uncertainty_engine
    _uncertainty_engine = None
