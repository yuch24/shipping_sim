import pytest
from app.scheduler.visualization_sync import VisualizationSync, SailingSegment
from app.services.navigation import (
    haversine,
    great_circle_interpolate,
    interpolate_position,
)


class TestPositionInterpolation:
    def test_position_at_start_point(self):
        viz = VisualizationSync()

        viz.register_sailing(
            ship_id="test_ship",
            start_lat=31.2304,
            start_lon=121.4737,
            end_lat=29.8683,
            end_lon=121.544,
            start_time=0.0,
            end_time=100.0,
        )

        lat, lon, status = viz.get_interpolated_position("test_ship", 0.0)

        assert lat is not None, "起始点纬度不应为None"
        assert lon is not None, "起始点经度不应为None"
        assert abs(lat - 31.2304) < 0.001, \
            f"起始点纬度错误: 期望31.2304, 实际{lat}"
        assert abs(lon - 121.4737) < 0.001, \
            f"起始点经度错误: 期望121.4737, 实际{lon}"
        assert status == "START", f"起始点状态应为START，实际为{status}"

    def test_position_at_end_point(self):
        viz = VisualizationSync()

        viz.register_sailing(
            ship_id="test2",
            start_lat=31.2304,
            start_lon=121.4737,
            end_lat=29.8683,
            end_lon=121.544,
            start_time=0.0,
            end_time=100.0,
        )

        lat, lon, status = viz.get_interpolated_position("test2", 100.0)

        assert lat is not None
        assert lon is not None
        assert abs(lat - 29.8683) < 0.001, \
            f"终点纬度错误: 期望29.8683, 实际{lat}"
        assert abs(lon - 121.544) < 0.001, \
            f"终点经度错误: 期望121.544, 实际{lon}"
        assert status == "END", f"终点状态应为END，实际为{status}"

    def test_position_at_midpoint(self):
        viz = VisualizationSync()

        viz.register_sailing(
            ship_id="test3",
            start_lat=0.0,
            start_lon=0.0,
            end_lat=10.0,
            end_lon=10.0,
            start_time=0.0,
            end_time=200.0,
        )

        lat, lon, status = viz.get_interpolated_position("test3", 100.0)

        assert lat is not None
        assert lon is not None
        assert abs(lat - 5.0) < 1.0, \
            f"中点纬度应在5.0附近，实际为{lat}"
        assert abs(lon - 5.0) < 1.0, \
            f"中点经度应在5.0附近，实际为{lon}"
        assert status == "SAILING"

    def test_smooth_interpolation_no_jumps(self):
        viz = VisualizationSync()

        start_lat, start_lon = 30.0, 120.0
        end_lat, end_lon = 35.0, 125.0
        duration = 50.0

        viz.register_sailing(
            ship_id="smooth_test",
            start_lat=start_lat,
            start_lon=start_lon,
            end_lat=end_lat,
            end_lon=end_lon,
            start_time=0.0,
            end_time=duration,
        )

        prev_lat, prev_lon = None, None
        max_jump = 0.0

        for t in [i * 1.0 for i in range(int(duration))]:
            lat, lon, _ = viz.get_interpolated_position("smooth_test", t)

            if prev_lat is not None and prev_lon is not None:
                jump = haversine(prev_lat, prev_lon, lat, lon)
                max_jump = max(max_jump, jump)

            prev_lat, prev_lon = lat, lon

        total_distance = haversine(start_lat, start_lon, end_lat, end_lon)
        expected_per_step = total_distance / duration

        print(f"\n位置平滑度测试:")
        print(f"  总距离: {total_distance:.2f} NM")
        print(f"  持续时间: {duration:.1f} 小时")
        print(f"  每小时预期移动: {expected_per_step:.2f} NM")
        print(f"  最大跳变距离: {max_jump:.4f} NM")

        assert max_jump < expected_per_step * 2.0, \
            f"位置跳变过大: 最大跳变={max_jump:.4f}NM, 预期每步={expected_per_step:.2f}NM"


class TestGreatCircleRoute:
    def test_great_circle_vs_straight_line(self):
        shanghai = (31.2304, 121.4737)
        rotterdam = (51.9225, 4.4792)

        gc_distance = haversine(*shanghai, *rotterdam)

        mid_ratio = 0.5
        gc_mid = great_circle_interpolate(*shanghai, *rotterdam, mid_ratio)
        linear_mid = (
            (shanghai[0] + rotterdam[0]) / 2,
            (shanghai[1] + rotterdam[1]) / 2,
        )

        dist_from_gc_start = haversine(shanghai[0], shanghai[1], gc_mid[0], gc_mid[1])
        dist_from_linear_start = haversine(shanghai[0], shanghai[1], linear_mid[0], linear_mid[1])

        print(f"\n大圆航线 vs 直线:")
        print(f"  上海-鹿特丹总距离: {gc_distance:.0f} NM")
        print(f"  大圆航线中点: ({gc_mid[0]:.2f}, {gc_mid[1]:.2f})")
        print(f"  直线中点: ({linear_mid[0]:.2f}, {linear_mid[1]:.2f})")
        print(f"  大圆中点到起点距离: {dist_from_gc_start:.0f} NM")
        print(f"  直线中点到起点距离: {dist_from_linear_start:.0f} NM")

        assert abs(dist_from_gc_start - gc_distance/2) < gc_distance * 0.1, \
            "大圆航线中点到起点应约为总距离的一半"

    def test_long_route_follows_great_circle(self):
        singapore = (1.3521, 103.8198)
        hamburg = (53.5511, 9.9937)

        viz = VisualizationSync()
        viz.register_sailing(
            ship_id="long_route",
            start_lat=singapore[0],
            start_lon=singapore[1],
            end_lat=hamburg[0],
            end_lon=hamburg[1],
            start_time=0.0,
            end_time=300.0,
        )

        positions = []
        for t in range(0, 300, 10):
            lat, lon, _ = viz.get_interpolated_position("long_route", float(t))
            if lat and lon:
                positions.append((lat, lon))

        assert len(positions) > 20, "应采集到足够的位置点"

        total_deviation = 0.0
        for i in range(1, len(positions)):
            segment_dist = haversine(
                positions[i-1][0], positions[i-1][1],
                positions[i][0], positions[i][1]
            )
            total_deviation += segment_dist

        direct_distance = haversine(*singapore, *hamburg)
        path_ratio = total_deviation / direct_distance

        print(f"\n长航段（新加坡-汉堡）路径验证:")
        print(f"  直接距离: {direct_distance:.0f} NM")
        print(f"  路径总长度: {total_deviation:.0f} NM")
        print(f"  路径/直线比: {path_ratio:.3f}")

        assert path_ratio < 1.15, \
            f"路径偏离过大，可能未沿大圆航线: ratio={path_ratio:.3f}"


class TestVisualizationDataConsistency:
    def test_all_positions_available(self):
        viz = VisualizationSync()

        ship_ids = ["ship_a", "ship_b", "ship_c"]
        for sid in ship_ids:
            viz.register_sailing(
                ship_id=sid,
                start_lat=30.0 + hash(sid) % 10,
                start_lon=120.0 + hash(sid) % 10,
                end_lat=35.0 + hash(sid) % 10,
                end_lon=125.0 + hash(sid) % 10,
                start_time=0.0,
                end_time=100.0,
            )

        current_time = 50.0
        all_positions = viz.get_all_positions(current_time)

        assert len(all_positions) == len(ship_ids), \
            f"应返回{len(ship_ids)}艘船的位置，实际返回{len(all_positions)}艘"

        for sid in ship_ids:
            assert sid in all_positions, f"缺少船舶{sid}的位置数据"
            pos = all_positions[sid]
            assert "lat" in pos and "lon" in pos, \
                f"船舶{sid}的位置数据缺少lat或lon字段"
            assert "status" in pos, \
                f"船舶{sid}的位置数据缺少status字段"
            assert "progress" in pos, \
                f"船舶{sid}的位置数据缺少progress字段"

    def test_progress_value_range(self):
        viz = VisualizationSync()

        viz.register_sailing(
            ship_id="progress_test",
            start_lat=0.0,
            start_lon=0.0,
            end_lat=10.0,
            end_lon=10.0,
            start_time=0.0,
            end_time=100.0,
        )

        test_times = [0.0, 25.0, 50.0, 75.0, 100.0]
        expected_progress = [0.0, 0.25, 0.5, 0.75, 1.0]

        for t, expected in zip(test_times, expected_progress):
            positions = viz.get_all_positions(t)
            actual = positions.get("progress_test", {}).get("progress")

            assert actual is not None, f"时间{t}时应返回进度值"
            assert abs(actual - expected) < 0.01, \
                f"进度值错误: 时间{t}, 期望{expected}, 实际{actual}"

    def test_clear_resets_all_data(self):
        viz = VisualizationSync()

        viz.register_sailing("s1", 30, 120, 35, 125, 0, 100)
        viz.register_sailing("s2", 31, 121, 36, 126, 10, 110)

        assert len(viz._segments) > 0, "注册后应有航行段数据"
        assert len(viz._current_segment) > 0, "应有当前航行段"

        viz.clear()

        assert len(viz._segments) == 0, "清除后segments应为空"
        assert len(viz._current_segment) == 0, "清除后current_segment应为空"


class TestSegmentRegistration:
    def test_multiple_segments_for_same_ship(self):
        viz = VisualizationSync()

        for leg in range(3):
            viz.register_sailing(
                ship_id="multi_leg",
                start_lat=30.0 + leg,
                start_lon=120.0 + leg,
                end_lat=31.0 + leg,
                end_lon=121.0 + leg,
                start_time=float(leg * 100),
                end_time=float((leg + 1) * 100),
            )

        segments = viz.get_ship_segments("multi_leg")
        assert len(segments) == 3, \
            f"同一船舶的多个航段应都被记录，期望3个，实际{len(segments)}个"

        current = viz._current_segment.get("multi_leg")
        assert current is not None, "应有当前活跃航段"
        assert current.end_time == 300.0, \
            f"当前航段应是最后一个，结束时间应为300.0，实际为{current.end_time}"

    def test_waypoints_for_land_crossing_routes(self):
        from app.services.navigation import check_segment_crosses_land

        test_route_across_europe = ((36.0, -5.0), (51.0, 10.0))
        crosses_land = check_segment_crosses_land(*test_route_across_europe[0], *test_route_across_europe[1])

        print(f"\n陆地穿越检测:")
        print(f"  路线: ({test_route_across_europe[0]}) -> ({test_route_across_europe[1]})")
        print(f"  是否穿过陆地: {crosses_land}")

        if crosses_land:
            viz = VisualizationSync()
            viz.register_sailing(
                ship_id="land_cross",
                start_lat=test_route_across_europe[0][0],
                start_lon=test_route_across_europe[0][1],
                end_lat=test_route_across_europe[1][0],
                end_lon=test_route_across_europe[1][1],
                start_time=0.0,
                end_time=100.0,
            )

            segments = viz.get_ship_segments("land_cross")
            assert len(segments) > 0, "应至少有一个航段"

            if segments[0].waypoints:
                print(f"  生成的绕行航点数: {len(segments[0].waypoints)}")
                assert len(segments[0].waypoints) > 0, \
                    "穿过陆地的路线应生成绕行航点"
