"""
仿真验证与校核（V&V）模块

提供以下学术验证能力：
1. 稳态仿真 vs M/M/c 排队论理论值对比
2. 收敛性分析（Monte Carlo 所需运行次数）
3. 模型假设检验
4. 与经典文献/行业基准对比
"""
from typing import Optional
from dataclasses import dataclass
import math


@dataclass
class QueueingTheoryPrediction:
    """M/M/c 排队论理论预测"""
    model: str
    port_name: str
    arrival_rate: float       # λ (per hour)
    service_rate: float       # μ (per hour)
    servers: int              # c
    theoretical_utilization: float   # ρ = λ / (c*μ)
    theoretical_avg_queue: float     # Lq
    theoretical_avg_wait: float      # Wq (hours)
    theoretical_prob_blocking: float # Probability all servers busy


@dataclass
class ValidationResult:
    """仿真 vs 理论对比结果"""
    metric_name: str
    simulated_value: float
    theoretical_value: float
    absolute_error: float
    relative_error_pct: float
    within_acceptable_range: bool
    interpretation: str


@dataclass
class ConvergenceAnalysis:
    """收敛性分析结果"""
    metric_name: str
    required_runs: int       # 达到稳定所需最少运行次数
    running_mean: list[float]
    running_std: list[float]
    convergence_threshold: float
    is_converged: bool


def mmc_queue_theory(
    arrival_rate: float,     # λ: 平均到达率（艘/小时）
    service_rate: float,     # μ: 平均服务率（艘/小时/泊位）
    servers: int,            # c: 泊位数量
) -> dict:
    """
    M/M/c 排队论模型计算

    - 泊位利用率为 ρ = λ / (c * μ)
    - 要求 ρ < 1 系统才稳定

    使用 Erlang C 公式计算排队概率和平均队列长度。
    """
    if servers <= 0 or service_rate <= 0:
        return {"error": "参数无效"}

    rho = arrival_rate / (servers * service_rate)
    if rho >= 1:
        return {
            "utilization": rho,
            "avg_queue": float('inf'),
            "avg_wait_hours": float('inf'),
            "prob_blocking": 1.0,
            "note": "系统不稳定（ρ ≥ 1），队列理论无限增长",
        }

    # Erlang C 公式：P(>0) = 所有泊位繁忙的概率
    # 先计算 P0（系统空闲概率）
    sum_term = sum(
        (servers * rho) ** n / math.factorial(n)
        for n in range(servers)
    )
    erlang_c_num = (servers * rho) ** servers / math.factorial(servers) / (1 - rho)
    erlang_c_denom = sum_term + erlang_c_num
    p_blocking = erlang_c_num / erlang_c_denom if erlang_c_denom > 0 else 0.0

    # Little's Law: Lq = (ρ * P_blocking) / (1 - ρ)
    avg_queue = (rho * p_blocking) / (1 - rho) if rho < 1 else float('inf')

    # Wq = Lq / λ
    avg_wait = avg_queue / arrival_rate if arrival_rate > 0 else 0.0

    return {
        "utilization": round(rho, 4),
        "avg_queue": round(avg_queue, 4),
        "avg_wait_hours": round(avg_wait, 4),
        "prob_blocking": round(p_blocking, 4),
        "erlang_c_prob": round(p_blocking, 4),
    }


def validate_queueing(
    port_name: str,
    simulated_queue: float,
    simulated_utilization: float,
    simulated_wait_hours: float,
    arrival_rate: float,
    service_rate: float,
    servers: int,
    tolerance_pct: float = 15.0,
) -> list[ValidationResult]:
    """
    仿真结果 vs M/M/c 排队论理论值验证

    tolerance_pct: 允许的相对误差百分比（默认 15%）
    """
    theory = mmc_queue_theory(arrival_rate, service_rate, servers)
    if "error" in theory:
        return []

    results = []

    # 验证泊位利用率
    if theory["utilization"] > 0:
        util_error = abs(simulated_utilization - theory["utilization"]) / theory["utilization"] * 100
        results.append(ValidationResult(
            metric_name="泊位利用率",
            simulated_value=round(simulated_utilization, 4),
            theoretical_value=round(theory["utilization"], 4),
            absolute_error=round(abs(simulated_utilization - theory["utilization"]), 4),
            relative_error_pct=round(util_error, 2),
            within_acceptable_range=util_error <= tolerance_pct,
            interpretation=(
                f"误差 {util_error:.1f}%，在{'可接受' if util_error <= tolerance_pct else '超出'}范围（±{tolerance_pct}%）内"
            ),
        ))

    # 验证平均队列长度
    if theory["avg_queue"] != float('inf') and theory["avg_queue"] > 0:
        queue_error = abs(simulated_queue - theory["avg_queue"]) / theory["avg_queue"] * 100
        results.append(ValidationResult(
            metric_name="平均队列长度",
            simulated_value=round(simulated_queue, 4),
            theoretical_value=round(theory["avg_queue"], 4),
            absolute_error=round(abs(simulated_queue - theory["avg_queue"]), 4),
            relative_error_pct=round(queue_error, 2),
            within_acceptable_range=queue_error <= tolerance_pct * 2,  # 队列误差容限更大
            interpretation=(
                f"误差 {queue_error:.1f}%，在{'可接受' if queue_error <= tolerance_pct * 2 else '超出'}范围内"
            ),
        ))

    # 验证平均等待时间
    if theory["avg_wait_hours"] != float('inf') and theory["avg_wait_hours"] > 0:
        wait_error = abs(simulated_wait_hours - theory["avg_wait_hours"]) / theory["avg_wait_hours"] * 100
        results.append(ValidationResult(
            metric_name="平均等待时间",
            simulated_value=round(simulated_wait_hours, 4),
            theoretical_value=round(theory["avg_wait_hours"], 4),
            absolute_error=round(abs(simulated_wait_hours - theory["avg_wait_hours"]), 4),
            relative_error_pct=round(wait_error, 2),
            within_acceptable_range=wait_error <= tolerance_pct * 2,
            interpretation=(
                f"误差 {wait_error:.1f}%，在{'可接受' if wait_error <= tolerance_pct * 2 else '超出'}范围内"
            ),
        ))

    return results


def convergence_analysis(
    cumulative_means: list[float],
    threshold: float = 0.01,
    window: int = 10,
) -> ConvergenceAnalysis:
    """
    收敛性分析：评估序列（如 Monte Carlo 运行均值）是否收敛

    通过滑动窗口检查 running mean 的相对变化是否小于阈值来判断是否收敛。
    """
    if not cumulative_means:
        return ConvergenceAnalysis(
            metric_name="", required_runs=0,
            running_mean=[], running_std=[],
            convergence_threshold=threshold, is_converged=False,
        )

    n = len(cumulative_means)
    running_means = []
    running_stds = []
    required_runs = n
    is_converged = False

    for i in range(1, n + 1):
        window_data = cumulative_means[:i]
        running_means.append(sum(window_data) / i)

        if i > 1:
            variance = sum((x - running_means[-1]) ** 2 for x in window_data) / (i - 1)
            running_stds.append(math.sqrt(variance) if variance > 0 else 0.0)
        else:
            running_stds.append(0.0)

        # 检查收敛：最近 window 个点的相对变化率
        if i >= window + 5:
            recent = running_means[-window:]
            max_change = max(abs(recent[j] - recent[j - 1]) / abs(recent[j - 1] + 1e-10) for j in range(1, window))
            if max_change < threshold and not is_converged:
                required_runs = i
                is_converged = True

    return ConvergenceAnalysis(
        metric_name="running_mean",
        required_runs=required_runs,
        running_mean=[round(m, 4) for m in running_means],
        running_std=[round(s, 4) for s in running_stds],
        convergence_threshold=threshold,
        is_converged=is_converged,
    )


def industry_benchmark_comparison(
    on_time_rate: float,
    avg_delay_hours: float,
    carbon_intensity: float,
) -> list[ValidationResult]:
    """
    与行业基准对比验证

    参考基准（来源：Sea-Intelligence Global Liner Reliability 2024, UNCTAD 2024）：
    - 准班率行业均值 ≈ 55%（2024年） ± 10pp
    - 平均延误 ≈ 24-48 小时
    - 碳强度 AEU 航线 ≈ 0.10-0.15 tCO2/(TEU·NM)
    """
    results = []

    # 准班率
    benchmark_on_time = 55.0  # Sea-Intelligence 2024 全球均值
    ot_error = abs(on_time_rate - benchmark_on_time)
    results.append(ValidationResult(
        metric_name="准班率（vs 行业基准）",
        simulated_value=round(on_time_rate, 1),
        theoretical_value=benchmark_on_time,
        absolute_error=round(ot_error, 1),
        relative_error_pct=round(ot_error / benchmark_on_time * 100, 1),
        within_acceptable_range=ot_error <= 20,
        interpretation=(
            f"2024年全球班轮准班率均值约 {benchmark_on_time}%，"
            f"仿真值 {on_time_rate:.1f}%，偏差 {ot_error:.1f}pp"
        ),
    ))

    # 平均延误
    benchmark_delay_low, benchmark_delay_high = 24.0, 48.0
    if benchmark_delay_low <= avg_delay_hours <= benchmark_delay_high:
        delay_interp = "在行业典型范围（24-48h）内"
    elif avg_delay_hours < benchmark_delay_low:
        delay_interp = f"低于行业低端（{benchmark_delay_low}h），可能过于乐观"
    else:
        delay_interp = f"高于行业高端（{benchmark_delay_high}h），系统拥堵水平偏高"
    results.append(ValidationResult(
        metric_name="平均延误（vs 行业基准）",
        simulated_value=round(avg_delay_hours, 1),
        theoretical_value=benchmark_delay_high,
        absolute_error=round(max(0, avg_delay_hours - benchmark_delay_high), 1),
        relative_error_pct=0.0,
        within_acceptable_range=benchmark_delay_low <= avg_delay_hours <= benchmark_delay_high,
        interpretation=delay_interp,
    ))

    # 碳强度（航次平均）
    benchmark_cii_low, benchmark_cii_high = 0.10, 0.15
    if benchmark_cii_low <= carbon_intensity <= benchmark_cii_high:
        cii_interp = "在行业典型范围（0.10-0.15）内"
    elif carbon_intensity < benchmark_cii_low:
        cii_interp = "低于行业低端，效率较好"
    else:
        cii_interp = "高于行业高端，碳强度偏高"

    results.append(ValidationResult(
        metric_name="碳强度（vs 行业基准）",
        simulated_value=round(carbon_intensity, 4),
        theoretical_value=benchmark_cii_high,
        absolute_error=round(max(0, carbon_intensity - benchmark_cii_high), 4),
        relative_error_pct=(
            round(max(0, carbon_intensity - benchmark_cii_high) / benchmark_cii_high * 100, 1)
            if benchmark_cii_high > 0 else 0.0
        ),
        within_acceptable_range=benchmark_cii_low <= carbon_intensity <= benchmark_cii_high,
        interpretation=cii_interp,
    ))

    return results
