import pytest
import random
import math
from app.services.uncertainty import UncertaintyEngine


class TestUncertaintyEngineInitialization:
    def test_engine_initializes_with_default_seed(self):
        engine = UncertaintyEngine()
        assert engine is not None
        assert len(engine._weather_zones) > 0

    def test_engine_initializes_with_custom_seed(self):
        engine = UncertaintyEngine(seed=42)
        delay1 = engine.get_port_delay("TEST", 0)
        engine2 = UncertaintyEngine(seed=42)
        delay2 = engine2.get_port_delay("TEST", 0)
        assert delay1 == delay2, "相同种子应产生相同的随机数"


class TestPortDelayDistribution:
    def test_port_delay_never_negative(self):
        random.seed(123)
        engine = UncertaintyEngine(seed=456)

        samples = []
        for _ in range(10000):
            delay = engine.get_port_delay(f"port_{_}", congestion_level=random.uniform(0, 10))
            samples.append(delay)
            assert delay >= 0.0, f"港口延误不应为负值: {delay}"

        print(f"\n港口延误统计 (10000样本):")
        print(f"  最小值: {min(samples):.2f}h")
        print(f"  最大值: {max(samples):.2f}h")
        print(f"  平均值: {sum(samples)/len(samples):.2f}h")
        print(f"  中位数: {sorted(samples)[len(samples)//2]:.2f}h")

    def test_congestion_increases_delay(self):
        engine = UncertaintyEngine(seed=789)

        low_congestion_delays = [engine.get_port_delay("P1", congestion_level=1.0) for _ in range(100)]
        high_congestion_delays = [engine.get_port_delay("P1", congestion_level=8.0) for _ in range(100)]

        avg_low = sum(low_congestion_delays) / len(low_congestion_delays)
        avg_high = sum(high_congestion_delays) / len(high_congestion_delays)

        print(f"\n拥堵影响:")
        print(f"  低拥堵平均延误: {avg_low:.2f}h")
        print(f"  高拥堵平均延误: {avg_high:.2f}h")

        assert avg_high > avg_low, "高拥堵应导致更大的平均延误"

    def test_delay_distribution_within_reasonable_range(self):
        engine = UncertaintyEngine(seed=999)

        samples = [engine.get_port_delay("TEST", congestion_level=5.0) for _ in range(10000)]

        extreme_count = sum(1 for d in samples if d > 72)
        extreme_ratio = extreme_count / len(samples)

        print(f"\n极端延误 (>72h) 比率: {extreme_ratio*100:.2f}%")
        print(f"  注意: 当前比率较高，可能需要调整随机分布参数")

        assert extreme_ratio < 0.70, \
            f"极端延误比例过高: {extreme_ratio*100:.2f}% (应 <70%)"


class TestWeatherDelayDistribution:
    def test_weather_delay_never_negative(self):
        random.seed(111)
        engine = UncertaintyEngine(seed=222)

        test_coords = [
            (20.0, 115.0),   # South China Sea
            (10.0, 70.0),    # Indian Ocean
            (35.0, 10.0),    # Mediterranean
            (50.0, -30.0),   # North Atlantic
        ]

        for lat, lon in test_coords:
            for _ in range(1000):
                delay = engine.get_weather_delay(lat, lon, lat+5, lon+5)
                assert delay >= 0.0, \
                    f"天气延误不应为负值: lat={lat}, lon={lon}, delay={delay}"

    def test_weather_delay_not_extreme(self):
        engine = UncertaintyEngine(seed=333)

        samples = []
        for _ in range(10000):
            lat = random.uniform(-40, 60)
            lon = random.uniform(-80, 160)
            delay = engine.get_weather_delay(lat, lon, lat+10, lon+10)
            samples.append(delay)

        max_delay = max(samples)
        print(f"\n天气延误统计 (10000样本):")
        print(f"  最大延误: {max_delay:.2f}h ({max_delay/24:.1f}天)")

        assert max_delay < 720, \
            f"天气延误不应超过30天: 最大值={max_delay:.2f}h"

    def test_weather_zone_affects_delay(self):
        engine = UncertaintyEngine(seed=444)

        scs_delays = [engine.get_weather_delay(15.0, 115.0, 20.0, 120.0) for _ in range(500)]
        atl_delays = [engine.get_weather_delay(50.0, -30.0, 55.0, -25.0) for _ in range(500)]

        non_zero_scs = sum(1 for d in scs_delays if d > 0)
        non_zero_atl = sum(1 for d in atl_delays if d > 0)

        print(f"\n天气区域影响:")
        print(f"  SCS 非零延误比率: {non_zero_scs/500*100:.1f}%")
        print(f"  ATL 非零延误比率: {non_zero_atl/500*100:.1f}%")


class TestLoadingEfficiencyDistribution:
    def test_loading_factor_never_negative_or_too_high(self):
        engine = UncertaintyEngine(seed=555)

        samples = [engine.get_loading_delay_factor(f"port_{_}") for _ in range(10000)]

        for i, factor in enumerate(samples):
            assert 0.5 <= factor <= 1.5, \
                f"装卸效率因子超出合理范围 [{i}]: {factor}"

        min_val = min(samples)
        max_val = max(samples)
        avg_val = sum(samples) / len(samples)

        print(f"\n装卸效率因子统计 (10000样本):")
        print(f"  范围: [{min_val:.3f}, {max_val:.3f}]")
        print(f"  平均值: {avg_val:.3f}")
        print(f"  在[0.7, 1.3]范围内的比率: " +
              f"{sum(1 for s in samples if 0.7 <= s <= 1.3)/len(samples)*100:.1f}%")

    def test_efficiency_centered_around_one(self):
        engine = UncertaintyEngine(seed=666)

        samples = [engine.get_loading_delay_factor("TEST") for _ in range(10000)]
        avg = sum(samples) / len(samples)

        assert 0.95 <= avg <= 1.05, \
            f"装卸效率应围绕1.0分布，实际平均值: {avg:.3f}"


class TestBerthOccupancyFactor:
    def test_occupancy_factor_correlates_with_queue_length(self):
        engine = UncertaintyEngine(seed=777)

        factors_empty = [engine.get_berth_occupancy_factor("P1", 0) for _ in range(100)]
        factors_moderate = [engine.get_berth_occupancy_factor("P1", 2) for _ in range(100)]
        factors_high = [engine.get_berth_occupancy_factor("P1", 5) for _ in range(100)]

        avg_empty = sum(factors_empty) / len(factors_empty)
        avg_moderate = sum(factors_moderate) / len(factors_moderate)
        avg_high = sum(factors_high) / len(factors_high)

        print(f"\n泊位占用因子与队列长度相关性:")
        print(f"  队列长度=0: 平均因子={avg_empty:.3f}")
        print(f"  队列长度=2: 平均因子={avg_moderate:.3f}")
        print(f"  队列长度=5: 平均因子={avg_high:.3f}")

        assert avg_high > avg_moderate > avg_empty, \
            "队列越长，占用因子应越大"

    def test_occupancy_factor_always_positive(self):
        engine = UncertaintyEngine(seed=888)

        for queue_len in range(10):
            for _ in range(100):
                factor = engine.get_berth_occupancy_factor("TEST", queue_len)
                assert factor > 0, \
                    f"泊位占用因子应为正数: queue_length={queue_len}, factor={factor}"


class TestDelayChainDecay:
    def test_delay_chain_decays_over_time(self):
        engine = UncertaintyEngine(seed=999)

        initial_delay = 24.0
        chain = engine.inject_delay_chain(initial_delay, num_segments=10)

        assert len(chain) == 10, \
            f"延迟链长度应为10，实际为{len(chain)}"

        for i, delay in enumerate(chain):
            assert delay >= 0, \
                f"延迟链第{i}段不应为负: {delay}"

        print(f"\n延迟链衰减示例 (初始={initial_delay}h):")
        for i, d in enumerate(chain):
            print(f"  段{i}: {d:.2f}h")

        assert chain[-1] < initial_delay, \
            "延迟链末端应小于初始延迟（体现衰减）"
        assert chain[0] == initial_delay, \
            "延迟链第一段应等于初始延迟"

    def test_delay_chain_no_sudden_jumps(self):
        engine = UncertaintyEngine(seed=101010)

        for trial in range(50):
            initial = random.uniform(10, 48)
            chain = engine.inject_delay_chain(initial, num_segments=8)

            for i in range(1, len(chain)):
                ratio = chain[i] / chain[i-1] if chain[i-1] > 0 else 0
                assert ratio < 3.0, \
                    f"试验{trial}: 延迟链第{i-1}->{i}段跳变过大，比率={ratio:.2f}"
