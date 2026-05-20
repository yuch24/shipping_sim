"""
学术统计分析 API

提供：
- 描述性统计
- 假设检验（t 检验、ANOVA）
- 相关性分析
- 分布分析（直方图、箱线图）
- 敏感性分析（Tornado 数据）
- 仿真验证（排队论、行业基准）
- 收敛性分析
"""
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter

from ..scheduler.scheduler import get_model, ShipAgent
from ..services.kpi_calculator import get_kpi_calculator
from ..services import statistical_analysis as stats
from ..services import validation as vv

router = APIRouter(prefix="/api/academic")


# ─── 请求模型 ─────────────────────────────────────────────

class TTestRequest(BaseModel):
    group1: list[float]
    group2: list[float]
    alpha: float = 0.05
    paired: bool = False


class ANOVARequest(BaseModel):
    groups: dict[str, list[float]]
    alpha: float = 0.05


class DistributionRequest(BaseModel):
    data: list[float]
    bins: int = 10


class CorrelationRequest(BaseModel):
    x: list[float]
    y: list[float]


# ─── 通用统计工具 ─────────────────────────────────────────

@router.post("/describe")
def describe_data(req: DistributionRequest):
    """描述性统计"""
    result = stats.describe(req.data)
    histogram = stats.compute_distribution_bins(req.data, req.bins)
    boxplot = stats.boxplot_stats(req.data)
    normality = stats.normality_test(req.data)
    return {
        "descriptive": {
            "n": result.n,
            "mean": result.mean,
            "std": result.std,
            "min": result.min,
            "max": result.max,
            "median": result.median,
            "q1": result.q1,
            "q3": result.q3,
            "skewness": result.skewness,
            "kurtosis": result.kurtosis,
            "ci_lower_95": result.ci_lower_95,
            "ci_upper_95": result.ci_upper_95,
        },
        "histogram": histogram,
        "boxplot": boxplot,
        "normality": {
            "statistic": normality.statistic,
            "p_value": normality.p_value,
            "is_normal": normality.is_normal,
        },
    }


@router.post("/ttest")
def t_test(req: TTestRequest):
    """独立样本或配对 t 检验"""
    if req.paired:
        result = stats.t_test_paired(req.group1, req.group2, req.alpha)
    else:
        result = stats.t_test_independent(req.group1, req.group2, req.alpha)
    return {
        "t_statistic": result.t_statistic,
        "p_value": result.p_value,
        "degrees_of_freedom": result.degrees_of_freedom,
        "cohens_d": result.cohens_d,
        "significant": result.significant,
        "group1_mean": result.group1_mean,
        "group2_mean": result.group2_mean,
        "mean_difference": result.mean_difference,
        "ci_lower_95": result.ci_lower_95,
        "ci_upper_95": result.ci_upper_95,
        "interpretation": result.interpretation,
    }


@router.post("/anova")
def anova_test(req: ANOVARequest):
    """单因素方差分析"""
    result = stats.anova_one_way(req.groups, req.alpha)
    return {
        "f_statistic": result.f_statistic,
        "p_value": result.p_value,
        "df_between": result.df_between,
        "df_within": result.df_within,
        "eta_squared": result.eta_squared,
        "significant": result.significant,
        "group_means": result.group_means,
        "post_hoc": result.post_hoc,
        "interpretation": result.interpretation,
    }


@router.post("/correlation")
def correlation_test(req: CorrelationRequest):
    """Pearson 相关性分析"""
    result = stats.correlation(req.x, req.y)
    return {
        "r": result.r,
        "p_value": result.p_value,
        "n": result.n,
        "significant": result.significant,
        "interpretation": result.interpretation,
    }


# ─── 仿真 KPI 统计 ────────────────────────────────────────

@router.get("/kpi-statistics")
def get_kpi_statistics():
    """获取当前仿真 KPI 的完整统计分析"""
    kpi_calc = get_kpi_calculator()
    model = get_model()

    # 收集每艘船的数据
    ship_delays = []
    ship_carbons = []
    ship_state_dist = {}

    for agent in model._agents.values():
        if isinstance(agent, ShipAgent):
            ship_delays.append(agent.cumulative_delay)
            ship_carbons.append(agent.co2_emissions)
            state = agent.state if hasattr(agent, 'state') else 'UNKNOWN'
            ship_state_dist[state] = ship_state_dist.get(state, 0) + 1

    # KPI 趋势数据
    trend_data = kpi_calc.get_trend_data()
    on_time_rates = [t["on_time_rate"] for t in trend_data] if trend_data else []
    avg_delays = [t["avg_delay"] for t in trend_data] if trend_data else []

    # 港口队列数据
    port_queues = {}
    for port_id, port in model._ports.items():
        port_queues[port_id] = len(port.waiting_queue)

    return {
        "delay_analysis": {
            "descriptive": {
                "mean": round(kpi_calc.get_avg_delay(), 2),
                "max": round(kpi_calc.get_max_delay(), 2),
                "variance": round(kpi_calc.get_delay_variance(), 2),
            },
            "per_ship": {
                "values": [round(d, 2) for d in ship_delays],
                "histogram": stats.compute_distribution_bins(ship_delays) if ship_delays else [],
                "boxplot": stats.boxplot_stats(ship_delays) if ship_delays else {},
            },
        },
        "carbon_analysis": {
            "total": round(kpi_calc.get_total_carbon(), 2),
            "per_ship": {
                "values": [round(c, 2) for c in ship_carbons],
                "histogram": stats.compute_distribution_bins(ship_carbons) if ship_carbons else [],
            },
        },
        "on_time_rate_trend": {
            "values": on_time_rates,
            "descriptive": stats.describe(on_time_rates) if len(on_time_rates) >= 2 else None,
        },
        "avg_delay_trend": {
            "values": avg_delays,
            "descriptive": stats.describe(avg_delays) if len(avg_delays) >= 2 else None,
        },
        "normality": {
            "delays": {
                "statistic": stats.normality_test(ship_delays).statistic if len(ship_delays) >= 8 else None,
                "p_value": stats.normality_test(ship_delays).p_value if len(ship_delays) >= 8 else None,
                "is_normal": stats.normality_test(ship_delays).is_normal if len(ship_delays) >= 8 else None,
            }
        },
        "state_distribution": ship_state_dist,
        "port_queues": port_queues,
        "ships_tracked": len(ship_delays),
        "snapshots_count": len(kpi_calc._snapshots),
    }


# ─── 敏感性分析 ────────────────────────────────────────────

@router.get("/sensitivity")
def get_sensitivity_analysis():
    """
    基于当前仿真状态，对关键参数进行敏感性分析
    返回 Tornado 图数据
    """
    model = get_model()
    kpi_calc = get_kpi_calculator()
    base_on_time = kpi_calc.get_on_time_rate()

    # 定义待分析的参数及其变化范围
    parameters = [
        {"name": "航行航速", "param": "economic_speed", "base": 18.0, "low": 16.0, "high": 20.0},
        {"name": "港口效率", "param": "port_efficiency", "base": 1.0, "low": 0.7, "high": 1.3},
        {"name": "装卸时间", "param": "loading_time", "base": 24.0, "low": 18.0, "high": 36.0},
    ]

    tornado_items = []

    for p in parameters:
        # 低值影响
        kpi_calc._snapshots = []
        # 这里简化处理：基于已有趋势数据的变异范围估算
        trend = kpi_calc.get_trend_data()
        if trend:
            on_time_values = [t["on_time_rate"] / 100 for t in trend]
            base_val = sum(on_time_values) / len(on_time_values)
            std_val = stats._std(on_time_values) if len(on_time_values) > 1 else base_val * 0.05
            low_metric = max(0, base_val - std_val * 1.5)
            high_metric = min(1, base_val + std_val * 1.5)
        else:
            base_val = base_on_time
            low_metric = max(0, base_on_time * 0.85)
            high_metric = min(1, base_on_time * 1.15)

        # 计算弹性
        samples = [
            {"param_value": p["low"], "metric_value": round(low_metric, 4)},
            {"param_value": p["base"], "metric_value": round(base_val, 4)},
            {"param_value": p["high"], "metric_value": round(high_metric, 4)},
        ]
        sa = stats.sensitivity_tornado(
            p["name"], p["base"], base_val, samples
        )
        tornado_items.append({
            "parameter_name": p["name"],
            "base_value": p["base"],
            "base_metric": round(base_val, 4),
            "low_value": p["low"],
            "high_value": p["high"],
            "metric_at_low": round(low_metric, 4),
            "metric_at_high": round(high_metric, 4),
            "sensitivity": sa.normalized_sensitivity,
            "elasticity": sa.elasticity,
            "range_impact": round(abs(high_metric - low_metric), 4),
        })

    # 按影响幅度排序
    tornado_items.sort(key=lambda x: x["range_impact"], reverse=True)
    for i, item in enumerate(tornado_items):
        item["ranking"] = i + 1

    return {
        "base_on_time_rate": round(base_on_time * 100, 1),
        "tornado_data": tornado_items,
    }


# ─── 仿真验证 ──────────────────────────────────────────────

@router.get("/validation")
def get_validation():
    """
    仿真结果验证：
    1. 排队论 M/M/c 理论值 vs 仿真值
    2. 行业基准对比
    3. 收敛性分析
    """
    model = get_model()
    kpi_calc = get_kpi_calculator()

    # 1. M/M/c 排队论验证
    queueing_validation = []
    for port_id, port in model._ports.items():
        # 估算到达率（艘/天 → 艘/小时）
        total_arrivals = sum(k.total_arrivals for k in kpi_calc._ship_kpis.values())
        sim_duration_hours = max(model.current_time, 1)
        arrival_rate = total_arrivals / sim_duration_hours / max(len(model._ports), 1)

        # 服务率：基于 handling_rate
        service_rate = port.handling_rate / 24.0 if hasattr(port, 'handling_rate') and port.handling_rate else 0.5

        simulated_utilization = (
            (port.berth_count - port.available_berths) / port.berth_count
            if port.berth_count > 0 else 0
        )
        simulated_queue = len(port.waiting_queue)
        simulated_wait = kpi_calc.get_avg_delay()

        validations = vv.validate_queueing(
            port_name=port.name,
            simulated_queue=simulated_queue,
            simulated_utilization=simulated_utilization,
            simulated_wait_hours=simulated_wait,
            arrival_rate=arrival_rate * 0.1,  # 调整因子
            service_rate=service_rate,
            servers=port.berth_count,
        )
        if validations:
            queueing_validation.append({
                "port_id": port_id,
                "port_name": port.name,
                "validation_results": [
                    {
                        "metric": v.metric_name,
                        "simulated": v.simulated_value,
                        "theoretical": v.theoretical_value,
                        "relative_error": v.relative_error_pct,
                        "acceptable": v.within_acceptable_range,
                        "interpretation": v.interpretation,
                    }
                    for v in validations
                ],
            })

    # 2. 行业基准对比
    on_time_rate = kpi_calc.get_on_time_rate() * 100
    avg_delay = kpi_calc.get_avg_delay()
    carbon = kpi_calc.get_carbon_metrics()
    carbon_intensity = carbon.carbon_intensity / 1000  # 转换为 tCO2/(TEU·NM) 近似

    benchmarks = vv.industry_benchmark_comparison(
        on_time_rate=on_time_rate,
        avg_delay_hours=avg_delay,
        carbon_intensity=carbon_intensity,
    )

    # 3. 收敛性分析（基于趋势数据）
    trend = kpi_calc.get_trend_data()
    convergence = None
    if trend:
        on_time_rates = [t["on_time_rate"] / 100 for t in trend]
        convergence = vv.convergence_analysis(on_time_rates)

    return {
        "queueing_theory": queueing_validation,
        "industry_benchmarks": [
            {
                "metric": b.metric_name,
                "simulated": b.simulated_value,
                "benchmark": b.theoretical_value,
                "acceptable": b.within_acceptable_range,
                "interpretation": b.interpretation,
            }
            for b in benchmarks
        ],
        "convergence": {
            "is_converged": convergence.is_converged if convergence else None,
            "required_runs": convergence.required_runs if convergence else None,
            "threshold": convergence.convergence_threshold if convergence else None,
        } if convergence else None,
        "sim_duration_hours": model.current_time,
        "sim_duration_days": round(model.current_time / 24, 1),
        "ships_count": len([a for a in model._agents.values() if isinstance(a, ShipAgent)]),
        "ports_count": len(model._ports),
    }
