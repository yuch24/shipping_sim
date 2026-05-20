import pytest
from fastapi.testclient import TestClient
from app.main import app


class TestAPIHealth:
    """API 基础端点测试"""

    def setup_method(self):
        self.client = TestClient(app)

    def test_health_check(self):
        """GET /api/health 应返回正常状态"""
        response = self.client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "app" in data
        assert data["app"] == "LinerDT"

    def test_kpi_dashboard(self):
        """GET /api/kpi/dashboard 应返回 KPI 数据"""
        response = self.client.get("/api/kpi/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "on_time_rate" in data
        assert "carbon_total" in data

    def test_kpi_trend(self):
        """GET /api/kpi/trend 应返回趋势数据"""
        response = self.client.get("/api/kpi/trend")
        assert response.status_code == 200
        data = response.json()
        assert "trend" in data

    def test_cors_headers(self):
        """带 Origin 头的请求应包含 CORS 头"""
        response = self.client.get("/api/health", headers={"Origin": "http://localhost:3000"})
        origin = response.headers.get("access-control-allow-origin") or \
                 response.headers.get("Access-Control-Allow-Origin")
        assert origin is not None

    def test_unknown_route_returns_404(self):
        """未知路由应返回 404"""
        response = self.client.get("/api/nonexistent")
        assert response.status_code == 404
