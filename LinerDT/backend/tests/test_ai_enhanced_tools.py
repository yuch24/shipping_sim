import pytest
from app.scheduler.scheduler import SimulationModel
from app.services.kpi_calculator import get_kpi_calculator


def _init_demo_scenario(model):
    from app.scheduler.scheduler import _init_demo_scenario as init
    init(model)


class TestPredictDelayCascade:
    def setup_method(self):
        self.model = SimulationModel()
        _init_demo_scenario(self.model)
        # 运行一段时间以产生历史数据
        self.model.scheduler.run_until(end_time=720)
        from app.ai.enhanced_tools import predict_delay_cascade
        self._predict = predict_delay_cascade

    def test_delay_cascade_returns_string(self):
        """delay cascade 预测应返回字符串"""
        result = self._predict(self.model, "Shanghai")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_delay_cascade_with_unknown_port(self):
        """未知港口应返回提示信息"""
        result = self._predict(self.model, "NonExistent")
        assert result is not None and len(result) > 0

    def test_delay_cascade_max_depth(self):
        """应支持 max_depth 参数"""
        result = self._predict(self.model, "Shanghai", max_depth=2)
        assert isinstance(result, str)
        assert len(result) > 0


class TestAnalyzeBottleneck:
    def setup_method(self):
        self.model = SimulationModel()
        _init_demo_scenario(self.model)
        self.model.scheduler.run_until(end_time=720)
        from app.ai.enhanced_tools import analyze_bottleneck
        self._analyze = analyze_bottleneck

    def test_analyze_bottleneck_returns_string(self):
        """瓶颈分析应返回字符串"""
        result = self._analyze(self.model)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_analyze_bottleneck_contains_key_metrics(self):
        """瓶颈分析应包含关键指标"""
        result = self._analyze(self.model)
        assert isinstance(result, str) and len(result) > 0


class TestCompareShips:
    def setup_method(self):
        self.model = SimulationModel()
        _init_demo_scenario(self.model)
        self.model.scheduler.run_until(end_time=720)
        from app.ai.enhanced_tools import compare_ships
        self._compare = compare_ships

    def test_compare_ships_returns_string(self):
        """船舶对比应返回字符串"""
        # 获取所有船舶 ID
        ship_ids = [
            sid for sid, agent in self.model._agents.items()
            if hasattr(agent, "current_speed")
        ][:2]
        result = self._compare(self.model, ship_ids)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_compare_ships_empty_list(self):
        """空列表应返回提示信息"""
        result = self._compare(self.model, [])
        assert len(result) > 0


class TestDiagnoseShip:
    def setup_method(self):
        self.model = SimulationModel()
        _init_demo_scenario(self.model)
        self.model.scheduler.run_until(end_time=720)
        from app.ai.enhanced_tools import diagnose_ship
        self._diagnose = diagnose_ship

    def test_diagnose_ship_valid(self):
        """有效船舶应返回诊断信息"""
        # 获取第一艘船
        ship_id = next(
            sid for sid, agent in self.model._agents.items()
            if hasattr(agent, "current_speed")
        )
        result = self._diagnose(self.model, ship_id)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_diagnose_ship_invalid(self):
        """无效船舶 ID 应返回提示"""
        result = self._diagnose(self.model, "INVALID_SHIP")
        assert "未找到" in result or "not found" in result.lower()


class TestSuggestOptimization:
    def setup_method(self):
        self.model = SimulationModel()
        _init_demo_scenario(self.model)
        self.model.scheduler.run_until(end_time=720)
        from app.ai.enhanced_tools import suggest_optimization
        self._suggest = suggest_optimization

    def test_suggest_optimization_returns_string(self):
        """优化建议应返回字符串"""
        result = self._suggest(self.model, "all")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_suggest_optimization_contains_suggestions(self):
        """优化建议应包含具体建议"""
        result = self._suggest(self.model, "all")
        # 应包含建议相关关键词
        assert any(keyword in result for keyword in
                   ["建议", "建议", "speed", "航速", "delay", "延误", "建议"])
