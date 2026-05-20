"""
ECA (Emission Control Area) 排放控制区模块

根据 IMO MARPOL Annex VI 定义：
- 全球硫上限 0.5% (2020年起)
- ECA 区域硫上限 0.1%
- 船舶进入 ECA 区域需切换低硫燃油或使用废气洗涤器
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class FuelType(str, Enum):
    HFO = "HFO"       # 重油 (硫含量 3.5%)
    VLSFO = "VLSFO"   # 超低硫燃油 (硫含量 0.5%)
    MGO = "MGO"       # 船用轻柴油 (硫含量 0.1%)
    LNG = "LNG"       # 液化天然气 (硫含量 ~0%)


class ECARegulation(str, Enum):
    GLOBAL = "GLOBAL"       # 全球 0.5% 硫上限
    ECA_0_1 = "ECA_0_1"     # ECA 区域 0.1% 硫上限
    ECA_FUEL = "ECA_FUEL"   # 需切换至 MGO/LNG


FUEL_PROPERTIES = {
    FuelType.HFO: {
        "sulfur_pct": 3.5,
        "co2_factor": 3.114,       # kg CO2 / kg fuel
        "sox_factor": 0.02,        # kg SOx / kg fuel (approximate)
        "cost_per_ton": 400.0,     # USD/ton (模拟价格)
        "energy_density_mj_kg": 40.5,
    },
    FuelType.VLSFO: {
        "sulfur_pct": 0.5,
        "co2_factor": 3.151,
        "sox_factor": 0.00286,
        "cost_per_ton": 500.0,
        "energy_density_mj_kg": 41.0,
    },
    FuelType.MGO: {
        "sulfur_pct": 0.1,
        "co2_factor": 3.206,
        "sox_factor": 0.00057,
        "cost_per_ton": 650.0,
        "energy_density_mj_kg": 42.8,
    },
    FuelType.LNG: {
        "sulfur_pct": 0.0,
        "co2_factor": 2.750,       # LNG 燃烧 CO2 排放因子更低
        "sox_factor": 0.0,
        "cost_per_ton": 350.0,
        "energy_density_mj_kg": 50.0,
    },
}


@dataclass
class ECARegion:
    name: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    regulation: ECARegulation = ECARegulation.ECA_0_1
    description: str = ""


# IMO 定义的 ECA 区域 (简化边界)
ECA_REGIONS = [
    ECARegion(
        name="North_Sea_ECA",
        lat_min=48.0, lat_max=62.0,
        lon_min=-5.0, lon_max=10.0,
        description="北海排放控制区",
    ),
    ECARegion(
        name="Baltic_Sea_ECA",
        lat_min=53.0, lat_max=66.0,
        lon_min=9.0, lon_max=30.0,
        description="波罗的海排放控制区",
    ),
    ECARegion(
        name="US_Caribbean_ECA",
        lat_min=10.0, lat_max=30.0,
        lon_min=-100.0, lon_max=-70.0,
        description="美国加勒比海排放控制区",
    ),
    ECARegion(
        name="Mediterranean_ECA",
        lat_min=30.0, lat_max=47.0,
        lon_min=-5.0, lon_max=36.0,
        regulation=ECARegulation.ECA_FUEL,
        description="地中海排放控制区（2025年起实施）",
    ),
    ECARegion(
        name="China_Coast_ECA",
        lat_min=20.0, lat_max=42.0,
        lon_min=110.0, lon_max=125.0,
        regulation=ECARegulation.ECA_FUEL,
        description="中国沿海排放控制区（DECA，根据中国 MARPOL 国内法规）",
    ),
]


def is_in_eca(lat: float, lon: float) -> Optional[ECARegion]:
    """检测 (lat, lon) 是否位于某个 ECA 区域内"""
    for region in ECA_REGIONS:
        if (region.lat_min <= lat <= region.lat_max and
            region.lon_min <= lon <= region.lon_max):
            return region
    return None


def get_required_fuel_type(lat: float, lon: float) -> FuelType:
    """根据当前位置返回应使用的燃油类型"""
    region = is_in_eca(lat, lon)
    if region is None:
        return FuelType.VLSFO  # 全球硫上限 0.5%
    return FuelType.MGO  # ECA 区域内使用 MGO (硫含量 0.1%)


def calculate_emission_factor(
    fuel_type: FuelType,
    lat: float,
    lon: float,
    has_scrubber: bool = False,
) -> dict:
    """计算给定位置和燃油类型的排放因子"""
    properties = FUEL_PROPERTIES[fuel_type]
    region = is_in_eca(lat, lon)

    effective_sulfur_pct = properties["sulfur_pct"]
    if has_scrubber and region is not None:
        effective_sulfur_pct = 0.1  # 洗涤器可等效达到 ECA 要求

    return {
        "fuel_type": fuel_type.value,
        "co2_factor": properties["co2_factor"],
        "sox_factor": properties["sox_factor"],
        "sulfur_pct": effective_sulfur_pct,
        "in_eca": region is not None,
        "eca_region": region.name if region else None,
        "cost_per_ton": properties["cost_per_ton"],
    }


def switch_fuel_if_needed(
    current_fuel: FuelType,
    lat: float,
    lon: float,
) -> tuple[FuelType, bool]:
    """检查是否需要切换燃油类型，返回 (新燃料, 是否切换)"""
    required = get_required_fuel_type(lat, lon)
    switched = current_fuel != required
    return required, switched


def calculate_sox_emission(
    fuel_consumption_kg: float,
    fuel_type: FuelType,
) -> float:
    """计算 SOx 排放量 (kg)"""
    properties = FUEL_PROPERTIES[fuel_type]
    return fuel_consumption_kg * properties["sox_factor"]


def calculate_co2_emission(
    fuel_consumption_kg: float,
    fuel_type: FuelType,
) -> float:
    """计算 CO2 排放量 (kg)"""
    properties = FUEL_PROPERTIES[fuel_type]
    return fuel_consumption_kg * properties["co2_factor"]


def calculate_fuel_cost(
    fuel_consumption_kg: float,
    fuel_type: FuelType,
) -> float:
    """计算燃油成本 (USD)"""
    properties = FUEL_PROPERTIES[fuel_type]
    return fuel_consumption_kg * properties["cost_per_ton"] / 1000.0


def get_route_eca_segments(
    waypoints: list[tuple[float, float]],
) -> list[dict]:
    """分析航路中各航段所属的 ECA 区域"""
    segments = []
    for i in range(len(waypoints) - 1):
        lat1, lon1 = waypoints[i]
        lat2, lon2 = waypoints[i + 1]
        mid_lat = (lat1 + lat2) / 2
        mid_lon = (lon1 + lon2) / 2

        region = is_in_eca(mid_lat, mid_lon)
        segments.append({
            "start": (lat1, lon1),
            "end": (lat2, lon2),
            "midpoint": (mid_lat, mid_lon),
            "in_eca": region is not None,
            "eca_region": region.name if region else None,
            "required_fuel": get_required_fuel_type(mid_lat, mid_lon).value,
        })
    return segments
