import pytest
from app.services.eca import (
    is_in_eca,
    get_required_fuel_type,
    calculate_emission_factor,
    switch_fuel_if_needed,
    calculate_sox_emission,
    calculate_co2_emission,
    calculate_fuel_cost,
    ECA_REGIONS,
    FuelType,
)


class TestECARegionDetection:
    """ECA 区域边界检测测试"""

    def test_north_sea_eca_inside(self):
        """北海 ECA 内部点"""
        region = is_in_eca(52.0, 2.0)  # 北海中部
        assert region is not None
        assert region.name == "North_Sea_ECA"

    def test_north_sea_eca_outside(self):
        """北海 ECA 外部点（赤道附近）"""
        region = is_in_eca(0.0, 50.0)
        assert region is None

    def test_baltic_sea_eca_inside(self):
        """波罗的海 ECA 内部点"""
        region = is_in_eca(58.0, 18.0)
        assert region is not None
        assert region.name == "Baltic_Sea_ECA"

    def test_china_coast_eca_inside(self):
        """中国沿海 ECA 内部点（上海外海）"""
        region = is_in_eca(31.0, 122.0)
        assert region is not None
        assert region.name == "China_Coast_ECA"

    def test_china_coast_eca_outside(self):
        """中国沿海 ECA 外部点（太平洋中部）"""
        region = is_in_eca(30.0, 140.0)
        assert region is None

    def test_mediterranean_eca_inside(self):
        """地中海 ECA 内部点"""
        region = is_in_eca(38.0, 15.0)
        assert region is not None
        assert region.name == "Mediterranean_ECA"

    def test_us_caribbean_eca_inside(self):
        """美国加勒比海 ECA 内部点"""
        region = is_in_eca(20.0, -85.0)
        assert region is not None
        assert region.name == "US_Caribbean_ECA"

    def test_boundary_point_inclusive(self):
        """边界点应被包含（lat_min/lat_max 是闭区间）"""
        region = is_in_eca(48.0, 2.0)  # North_Sea 南边界
        assert region is not None
        assert region.name == "North_Sea_ECA"

        region = is_in_eca(62.0, 2.0)  # North_Sea 北边界
        assert region is not None
        assert region.name == "North_Sea_ECA"

    def test_multiple_regions(self):
        """新加坡附近（东南亚）不应属于任何 ECA"""
        region = is_in_eca(1.3, 103.8)
        assert region is None

    def test_all_regions_have_unique_names(self):
        """所有 ECA 区域应有唯一名称"""
        names = [r.name for r in ECA_REGIONS]
        assert len(names) == len(set(names)), f"重复的 ECA 区域名称: {names}"


class TestFuelTypeSelection:
    """燃油类型选择测试"""

    def test_outside_eca_uses_vlsfo(self):
        """ECA 区域外应使用 VLSFO（全球硫上限 0.5%）"""
        fuel = get_required_fuel_type(1.3, 103.8)  # 新加坡
        assert fuel == FuelType.VLSFO

    def test_inside_eca_uses_mgo(self):
        """ECA 区域内应使用 MGO（硫上限 0.1%）"""
        fuel = get_required_fuel_type(52.0, 2.0)  # 北海
        assert fuel == FuelType.MGO

    def test_china_coast_eca_uses_mgo(self):
        """中国沿海 ECA 区域内应使用 MGO"""
        fuel = get_required_fuel_type(31.0, 122.0)
        assert fuel == FuelType.MGO


class TestEmissionFactor:
    """排放因子计算测试"""

    def test_outside_eca_baseline(self):
        """ECA 区域外应返回正确的 CO2/SOx 因子"""
        factor = calculate_emission_factor(FuelType.VLSFO, 1.3, 103.8)
        assert factor["fuel_type"] == "VLSFO"
        assert factor["in_eca"] is False
        assert factor["eca_region"] is None
        assert factor["co2_factor"] > 0
        assert factor["sox_factor"] > 0

    def test_inside_eca_detected(self):
        """ECA 区域内应正确标记"""
        factor = calculate_emission_factor(FuelType.MGO, 52.0, 2.0)
        assert factor["in_eca"] is True
        assert factor["eca_region"] == "North_Sea_ECA"

    def test_scrubber_equivalent(self):
        """有洗涤器时在 ECA 区域内硫含量应降至 0.1%"""
        factor = calculate_emission_factor(FuelType.HFO, 52.0, 2.0, has_scrubber=True)
        assert factor["sulfur_pct"] == pytest.approx(0.1, abs=0.01)
        assert factor["in_eca"] is True

    def test_cost_per_ton(self):
        """不同燃油类型的成本应不同"""
        hfo_cost = calculate_emission_factor(FuelType.HFO, 0, 0)["cost_per_ton"]
        mgo_cost = calculate_emission_factor(FuelType.MGO, 0, 0)["cost_per_ton"]
        assert hfo_cost < mgo_cost  # HFO 应比 MGO 便宜


class TestFuelSwitch:
    """燃油切换逻辑测试"""

    def test_switch_needed_entering_eca(self):
        """进入 ECA 区域时应切换燃油"""
        new_fuel, switched = switch_fuel_if_needed(FuelType.VLSFO, 52.0, 2.0)
        assert switched is True
        assert new_fuel == FuelType.MGO

    def test_no_switch_outside_eca(self):
        """在 ECA 区域外不应切换"""
        new_fuel, switched = switch_fuel_if_needed(FuelType.VLSFO, 1.3, 103.8)
        assert switched is False
        assert new_fuel == FuelType.VLSFO

    def test_no_switch_already_correct(self):
        """已在 ECA 区域内且已使用正确燃油时不切换"""
        new_fuel, switched = switch_fuel_if_needed(FuelType.MGO, 52.0, 2.0)
        assert switched is False
        assert new_fuel == FuelType.MGO

    def test_switch_leaving_eca(self):
        """离开 ECA 区域时应切回 VLSFO"""
        new_fuel, switched = switch_fuel_if_needed(FuelType.MGO, 1.3, 103.8)
        assert switched is True
        assert new_fuel == FuelType.VLSFO


class TestEmissionCalculations:
    """排放量计算测试"""

    def test_co2_emission_hfo(self):
        """HFO 燃烧 CO2 排放量"""
        co2 = calculate_co2_emission(1000.0, FuelType.HFO)
        expected = 1000.0 * 3.114
        assert co2 == pytest.approx(expected, rel=0.01)

    def test_co2_emission_lng(self):
        """LNG 燃烧 CO2 排放量（应低于 HFO）"""
        co2_lng = calculate_co2_emission(1000.0, FuelType.LNG)
        co2_hfo = calculate_co2_emission(1000.0, FuelType.HFO)
        assert co2_lng < co2_hfo  # LNG 碳排放因子更低

    def test_sox_emission_hfo(self):
        """HFO 燃烧 SOx 排放量"""
        sox = calculate_sox_emission(1000.0, FuelType.HFO)
        expected = 1000.0 * 0.02
        assert sox == pytest.approx(expected, rel=0.01)

    def test_sox_emission_lng_zero(self):
        """LNG 燃烧 SOx 排放量应为 0"""
        sox = calculate_sox_emission(1000.0, FuelType.LNG)
        assert sox == 0.0

    def test_fuel_cost(self):
        """燃油成本计算"""
        cost = calculate_fuel_cost(1000.0, FuelType.HFO)
        expected = 1000.0 * 400.0 / 1000.0  # $400/ton
        assert cost == pytest.approx(expected, rel=0.01)
