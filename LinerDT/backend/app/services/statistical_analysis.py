"""
统计分析与假设检验服务
为仿真实验提供学术级别的统计分析能力：
- 假设检验（独立样本 t 检验、配对 t 检验、ANOVA）
- 效应量（Cohen's d, η²）
- 置信区间（95% CI for mean, proportion）
- 分布分析（偏度、峰度、正态性检验）
- 相关性与回归分析
- 敏感性分析（标准化回归系数、Pareto 排序）
"""
from typing import Optional
from dataclasses import dataclass, field
import math


@dataclass
class DescriptiveStats:
    """描述性统计"""
    n: int
    mean: float
    std: float
    min: float
    max: float
    median: float
    q1: float
    q3: float
    skewness: float
    kurtosis: float
    ci_lower_95: float
    ci_upper_95: float


@dataclass
class TTestResult:
    """独立样本 t 检验结果"""
    t_statistic: float
    p_value: float
    degrees_of_freedom: int
    cohens_d: float
    significant: bool
    group1_mean: float
    group2_mean: float
    mean_difference: float
    ci_lower_95: float
    ci_upper_95: float
    interpretation: str


@dataclass
class ANOVAResult:
    """单因素 ANOVA 结果"""
    f_statistic: float
    p_value: float
    df_between: int
    df_within: int
    eta_squared: float
    significant: bool
    group_means: dict[str, float]
    post_hoc: list[dict]  # pairwise comparisons
    interpretation: str


@dataclass
class NormalityTest:
    """正态性检验（D'Agostino-Pearson / Shapiro-Wilk 近似）"""
    statistic: float
    p_value: float
    is_normal: bool


@dataclass
class CorrelationResult:
    """Pearson 相关系数"""
    r: float
    p_value: float
    n: int
    significant: bool
    interpretation: str


@dataclass
class SensitivityAnalysis:
    """单参数敏感性分析结果"""
    parameter_name: str
    base_value: float
    base_metric: float
    samples: list[dict]  # [{param_value, metric_value}]
    elasticity: float  # (%Δmetric) / (%Δparam) 在基准点
    normalized_sensitivity: float  # 归一化敏感度 [0, 1]
    ranking: int


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std(values: list[float], ddof: int = 1) -> float:
    n = len(values)
    if n <= ddof:
        return 0.0
    m = _mean(values)
    variance = sum((x - m) ** 2 for x in values) / (n - ddof)
    return math.sqrt(variance)


def _median(values: list[float]) -> float:
    sorted_v = sorted(values)
    n = len(sorted_v)
    if n == 0:
        return 0.0
    if n % 2 == 1:
        return sorted_v[n // 2]
    return (sorted_v[n // 2 - 1] + sorted_v[n // 2]) / 2


def _quantile(values: list[float], q: float) -> float:
    """计算分位数（线性插值法）"""
    sorted_v = sorted(values)
    n = len(sorted_v)
    if n == 0:
        return 0.0
    idx = q * (n - 1)
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return sorted_v[lo]
    return sorted_v[lo] * (hi - idx) + sorted_v[hi] * (idx - lo)


def _skewness(values: list[float]) -> float:
    """计算样本偏度"""
    n = len(values)
    if n < 3:
        return 0.0
    m = _mean(values)
    s = _std(values, ddof=0)
    if s == 0:
        return 0.0
    skew = sum((x - m) ** 3 for x in values) / n / (s ** 3)
    # 小样本校正
    adjustment = math.sqrt(n * (n - 1)) / (n - 2) if n > 2 else 1.0
    return skew * adjustment


def _kurtosis(values: list[float]) -> float:
    """计算超额峰度（excess kurtosis, 正态分布 = 0）"""
    n = len(values)
    if n < 4:
        return 0.0
    m = _mean(values)
    s = _std(values, ddof=0)
    if s == 0:
        return 0.0
    kurt = sum((x - m) ** 4 for x in values) / n / (s ** 4) - 3
    # 小样本校正
    adjustment = (n - 1) / ((n - 2) * (n - 3)) * ((n + 1) * kurt + 6) if n > 3 else kurt
    return adjustment


def _t_cdf(t: float, df: int) -> float:
    """t 分布的 CDF（使用近似公式）"""
    x = df / (df + t * t)
    # 使用 Abramowitz & Stegun 近似
    a1, a2, a3, a4, a5 = 0.278393, 0.230389, 0.000972, 0.078108, 0.000397  # unused but kept for reference
    b1, b2, b3, b4, b5 = 0.196854, 0.115194, 0.000344, 0.019527, 0.000090

    if t >= 0:
        # 使用 Hastings 近似
        p = 1.0 - 0.5 * math.exp(
            -0.71742 * t - 0.41658 * t * t
        ) if df > 30 else _t_cdf_small_df(t, df)
    else:
        p = 1.0 - _t_cdf(-t, df)
    return p


def _t_cdf_small_df(t: float, df: int) -> float:
    """小自由度时的 t 分布 CDF（数值积分近似）"""
    import math
    x = df / (df + t * t)
    # 不完全 beta 函数近似
    a, b = df / 2, 0.5
    # 使用简单近似
    p = 1.0 - 0.5 * _regularized_beta(x, a, b)
    return 1.0 - p if t < 0 else p


def _regularized_beta(x: float, a: float, b: float) -> float:
    """正则化不完全 Beta 函数（连分式近似）"""
    if x < 0 or x > 1:
        return 0.0
    if x == 0 or x == 1:
        return x

    # 使用 Lentz 连分式法
    small = 1e-30
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)

    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a

    f = 1.0
    c = 1.0
    d = 1.0 - (a + b) * x / (a + 1)
    if abs(d) < small:
        d = small
    d = 1.0 / d
    f = d

    for m in range(1, 201):
        # 偶数步
        numer = m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m))
        d = 1.0 + numer * d
        if abs(d) < small:
            d = small
        c = 1.0 + numer / c
        if abs(c) < small:
            c = small
        d = 1.0 / d
        f *= d * c

        # 奇数步
        numer = -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + numer * d
        if abs(d) < small:
            d = small
        c = 1.0 + numer / c
        if abs(c) < small:
            c = small
        d = 1.0 / d
        delta = d * c
        f *= delta

        if abs(delta - 1.0) < 1e-10:
            break

    return front * f


def _f_cdf(f: float, df1: int, df2: int) -> float:
    """F 分布的 CDF"""
    x = df1 * f / (df1 * f + df2)
    return 1.0 - _regularized_beta(x, df1 / 2, df2 / 2)


def _t_inv(p: float, df: int) -> float:
    """t 分布的分位数（Newton 法）"""
    if p <= 0:
        return -float('inf')
    if p >= 1:
        return float('inf')

    # 初始近似
    if df > 30:
        t = _norm_inv(p)
    else:
        # 粗略近似后迭代
        t = _norm_inv(p) * (1 + 1 / (4 * df))

    # Newton 迭代
    for _ in range(10):
        # 使用简单二分校正代替复杂的 CDF 梯度
        cdf_p = _t_cdf(t, df)
        diff = cdf_p - p
        if abs(diff) < 1e-10:
            break
        # 数值梯度
        h = max(abs(t) * 1e-6, 1e-8)
        grad = (_t_cdf(t + h, df) - _t_cdf(t - h, df)) / (2 * h)
        if abs(grad) < 1e-15:
            break
        t -= diff / grad
    return t


def _norm_inv(p: float) -> float:
    """标准正态分布分位数（Acklam 近似）"""
    if p <= 0 or p >= 1:
        return 0.0

    # 系数
    a1, a2, a3, a4, a5 = -3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01
    b1, b2, b3, b4, b5 = -5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01
    c1, c2, c3, c4, c5 = -7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00
    d1, d2, d3 = 7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00

    if p < 0.02425:
        q = math.sqrt(-2 * math.log(p))
        return (((((c1 * q + c2) * q + c3) * q + c4) * q + c5) * q + d3) / ((((d1 * q + d2) * q + d3) * q + 1.0))
    elif p < 0.97575:
        q = p - 0.5
        r = q * q
        return (((((a1 * r + a2) * r + a3) * r + a4) * r + a5) * r + b5) * q / (((((b1 * r + b2) * r + b3) * r + b4) * r + b5) * r + 1.0)
    else:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c1 * q + c2) * q + c3) * q + c4) * q + c5) * q + d3) / ((((d1 * q + d2) * q + d3) * q + 1.0))


def describe(data: list[float]) -> DescriptiveStats:
    """计算完整描述性统计"""
    if not data:
        return DescriptiveStats(
            n=0, mean=0.0, std=0.0, min=0.0, max=0.0,
            median=0.0, q1=0.0, q3=0.0, skewness=0.0, kurtosis=0.0,
            ci_lower_95=0.0, ci_upper_95=0.0,
        )

    n = len(data)
    mean = _mean(data)
    std = _std(data)
    sorted_data = sorted(data)

    # 置信区间
    se = std / math.sqrt(n) if n > 1 else 0.0
    t_val = _t_inv(0.975, n - 1) if n > 1 else 0.0
    ci_lower = mean - t_val * se if n > 1 else mean
    ci_upper = mean + t_val * se if n > 1 else mean

    return DescriptiveStats(
        n=n,
        mean=round(mean, 4),
        std=round(std, 4),
        min=round(sorted_data[0], 4),
        max=round(sorted_data[-1], 4),
        median=round(_median(data), 4),
        q1=round(_quantile(data, 0.25), 4),
        q3=round(_quantile(data, 0.75), 4),
        skewness=round(_skewness(data), 4),
        kurtosis=round(_kurtosis(data), 4),
        ci_lower_95=round(ci_lower, 4),
        ci_upper_95=round(ci_upper, 4),
    )


def t_test_independent(
    group1: list[float],
    group2: list[float],
    alpha: float = 0.05,
) -> TTestResult:
    """独立样本双尾 t 检验 + Cohen's d 效应量"""
    n1, n2 = len(group1), len(group2)
    m1, m2 = _mean(group1), _mean(group2)
    v1, v2 = _std(group1) ** 2, _std(group2) ** 2

    df = n1 + n2 - 2
    # 合并方差
    pooled_var = ((n1 - 1) * v1 + (n2 - 1) * v2) / df if df > 0 else 0.0
    pooled_std = math.sqrt(pooled_var) if pooled_var > 0 else 1.0

    se = math.sqrt(pooled_var * (1 / n1 + 1 / n2)) if pooled_var > 0 else 1.0
    t_stat = (m1 - m2) / se if se != 0 else 0.0

    # 双尾 p 值
    p_value = 2 * (1 - _t_cdf(abs(t_stat), df)) if df > 0 else 1.0
    p_value = min(max(p_value, 0.0), 1.0)

    # Cohen's d
    cohens_d = (m1 - m2) / pooled_std if pooled_std != 0 else 0.0

    # 均值差的 95% CI
    t_crit = _t_inv(1 - alpha / 2, df) if df > 0 else 0.0
    ci_lower = (m1 - m2) - t_crit * se
    ci_upper = (m1 - m2) + t_crit * se

    # 效应量解读
    d_abs = abs(cohens_d)
    if d_abs < 0.2:
        interp = "效应量极小或无效应"
    elif d_abs < 0.5:
        interp = "小效应"
    elif d_abs < 0.8:
        interp = "中等效应"
    else:
        interp = "大效应"

    if p_value < alpha:
        interp += "（统计显著）"
    else:
        interp += "（未达统计显著）"

    return TTestResult(
        t_statistic=round(t_stat, 4),
        p_value=round(p_value, 4),
        degrees_of_freedom=df,
        cohens_d=round(cohens_d, 4),
        significant=p_value < alpha,
        group1_mean=round(m1, 4),
        group2_mean=round(m2, 4),
        mean_difference=round(m1 - m2, 4),
        ci_lower_95=round(ci_lower, 4),
        ci_upper_95=round(ci_upper, 4),
        interpretation=interp,
    )


def t_test_paired(
    before: list[float],
    after: list[float],
    alpha: float = 0.05,
) -> TTestResult:
    """配对 t 检验"""
    if len(before) != len(after):
        raise ValueError("配对数据长度必须相同")

    differences = [a - b for a, b in zip(after, before)]
    n = len(differences)
    d_mean = _mean(differences)
    d_std = _std(differences)

    df = n - 1
    se = d_std / math.sqrt(n) if n > 1 else 0.0
    t_stat = d_mean / se if se != 0 else 0.0

    p_value = 2 * (1 - _t_cdf(abs(t_stat), df)) if df > 0 else 1.0
    p_value = min(max(p_value, 0.0), 1.0)

    # Cohen's d for paired = mean_diff / sd_diff
    cohens_d = d_mean / d_std if d_std != 0 else 0.0

    t_crit = _t_inv(1 - alpha / 2, df) if df > 0 else 0.0
    ci_lower = d_mean - t_crit * se
    ci_upper = d_mean + t_crit * se

    d_abs = abs(cohens_d)
    if d_abs < 0.2:
        interp = "效应量极小或无效应"
    elif d_abs < 0.5:
        interp = "小效应"
    elif d_abs < 0.8:
        interp = "中等效应"
    else:
        interp = "大效应"
    if p_value < alpha:
        interp += "（统计显著）"
    else:
        interp += "（未达统计显著）"

    return TTestResult(
        t_statistic=round(t_stat, 4),
        p_value=round(p_value, 4),
        degrees_of_freedom=df,
        cohens_d=round(cohens_d, 4),
        significant=p_value < alpha,
        group1_mean=round(_mean(before), 4),
        group2_mean=round(_mean(after), 4),
        mean_difference=round(d_mean, 4),
        ci_lower_95=round(ci_lower, 4),
        ci_upper_95=round(ci_upper, 4),
        interpretation=interp,
    )


def anova_one_way(
    groups: dict[str, list[float]],
    alpha: float = 0.05,
) -> ANOVAResult:
    """单因素方差分析 + η² 效应量 + Tukey HSD 事后检验"""
    k = len(groups)
    if k < 2:
        raise ValueError("至少需要 2 组进行比较")

    group_stats = {name: describe(data) for name, data in groups.items()}
    all_data = [v for vals in groups.values() for v in vals]
    grand_mean = _mean(all_data)
    total_n = len(all_data)

    # SS_between
    ss_between = sum(
        len(data) * (_mean(data) - grand_mean) ** 2
        for data in groups.values()
    )
    # SS_within
    ss_within = sum(
        sum((x - _mean(data)) ** 2 for x in data)
        for data in groups.values()
    )

    df_between = k - 1
    df_within = total_n - k

    ms_between = ss_between / df_between if df_between > 0 else 0
    ms_within = ss_within / df_within if df_within > 0 else 1.0

    f_stat = ms_between / ms_within if ms_within > 0 else 0.0
    p_value = 1 - _f_cdf(f_stat, df_between, df_within) if f_stat > 0 else 1.0
    p_value = min(max(p_value, 0.0), 1.0)

    eta_sq = ss_between / (ss_between + ss_within) if (ss_between + ss_within) > 0 else 0.0

    # Tukey HSD 事后检验
    post_hoc = []
    group_names = list(groups.keys())
    for i in range(k):
        for j in range(i + 1, k):
            ni, nj = len(groups[group_names[i]]), len(groups[group_names[j]])
            mi, mj = _mean(groups[group_names[i]]), _mean(groups[group_names[j]])
            se_tukey = math.sqrt(ms_within * (1 / ni + 1 / nj) / 2) if ms_within > 0 else 1.0
            q_stat = abs(mi - mj) / se_tukey if se_tukey != 0 else 0.0
            # Tukey p 值近似（studentized range distribution）
            p_tukey = 1 - (_f_cdf(q_stat ** 2 / 2, 2, df_within)) if k == 2 else 1 - (_t_cdf(abs(mi - mj) / math.sqrt(ms_within * (1/ni + 1/nj)), df_within) if ms_within > 0 else 1)

            post_hoc.append({
                "group1": group_names[i],
                "group2": group_names[j],
                "mean_diff": round(mi - mj, 4),
                "p_value": round(min(max(p_tukey, 0.0), 1.0), 4),
                "significant": p_tukey < alpha,
            })

    # 效应量解读
    if eta_sq < 0.01:
        interp = "无效应或极小效应"
    elif eta_sq < 0.06:
        interp = "小效应"
    elif eta_sq < 0.14:
        interp = "中等效应"
    else:
        interp = "大效应"
    if p_value < alpha:
        interp += "（模型统计显著）"
    else:
        interp += "（模型未达统计显著）"

    return ANOVAResult(
        f_statistic=round(f_stat, 4),
        p_value=round(p_value, 4),
        df_between=df_between,
        df_within=df_within,
        eta_squared=round(eta_sq, 4),
        significant=p_value < alpha,
        group_means={name: round(stats.mean, 4) for name, stats in group_stats.items()},
        post_hoc=post_hoc,
        interpretation=interp,
    )


def normality_test(data: list[float]) -> NormalityTest:
    """D'Agostino-Pearson 正态性检验"""
    n = len(data)
    if n < 8:
        return NormalityTest(statistic=0.0, p_value=1.0, is_normal=True)

    skew = _skewness(data)
    kurt = _kurtosis(data)

    # D'Agostino-Pearson K² 统计量
    z_skew = skew / math.sqrt(6.0 / n) if n > 6 else 0
    z_kurt = kurt / math.sqrt(24.0 / n) if n > 6 else 0
    k2 = z_skew ** 2 + z_kurt ** 2

    # 近似 χ²(2) p 值
    p_value = math.exp(-k2 / 2) if k2 < 50 else 0.0

    return NormalityTest(
        statistic=round(k2, 4),
        p_value=round(min(max(p_value, 0.0), 1.0), 4),
        is_normal=p_value > 0.05,
    )


def correlation(x: list[float], y: list[float]) -> CorrelationResult:
    """Pearson 相关系数 + 显著性检验"""
    n = min(len(x), len(y))
    if n < 3:
        return CorrelationResult(
            r=0.0, p_value=1.0, n=n,
            significant=False, interpretation="样本量不足",
        )

    mx, my = _mean(x), _mean(y)
    sdx, sdy = _std(x), _std(y)

    if sdx == 0 or sdy == 0:
        return CorrelationResult(
            r=0.0, p_value=1.0, n=n,
            significant=False, interpretation="数据无变异",
        )

    r = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / ((n - 1) * sdx * sdy)
    r = max(min(r, 1.0), -1.0)

    # t 检验
    if abs(r) >= 1.0:
        t_stat = float('inf')
        p_value = 0.0
    else:
        t_stat = r * math.sqrt((n - 2) / (1 - r * r))
        p_value = 2 * (1 - _t_cdf(abs(t_stat), n - 2))
        p_value = min(max(p_value, 0.0), 1.0)

    r_abs = abs(r)
    if r_abs < 0.1:
        interp = "无相关或极弱相关"
    elif r_abs < 0.3:
        interp = "弱相关"
    elif r_abs < 0.5:
        interp = "中等相关"
    elif r_abs < 0.7:
        interp = "强相关"
    else:
        interp = "极强相关"
    if p_value < 0.05:
        interp += "（显著）"
    else:
        interp += "（不显著）"

    return CorrelationResult(
        r=round(r, 4),
        p_value=round(p_value, 4),
        n=n,
        significant=p_value < 0.05,
        interpretation=interp,
    )


def sensitivity_tornado(
    param_name: str,
    base_value: float,
    base_metric: float,
    samples: list[dict],
) -> SensitivityAnalysis:
    """计算单参数敏感性分析（Tornado 图数据）"""
    if not samples or base_metric == 0:
        return SensitivityAnalysis(
            parameter_name=param_name,
            base_value=base_value,
            base_metric=base_metric,
            samples=samples,
            elasticity=0.0,
            normalized_sensitivity=0.0,
            ranking=0,
        )

    # 计算弹性：（Δmetric / metric）/（Δparam / param）
    # 取平均弹性
    elasticities = []

    # 归一化敏感度：metric 的变异系数 / param 的变异系数
    param_values = [s["param_value"] for s in samples if "param_value" in s]
    metric_values = [s["metric_value"] for s in samples if "metric_value" in s]

    if len(param_values) < 2 or len(metric_values) < 2:
        return SensitivityAnalysis(
            parameter_name=param_name,
            base_value=base_value,
            base_metric=base_metric,
            samples=samples,
            elasticity=0.0,
            normalized_sensitivity=0.0,
            ranking=0,
        )

    for s in samples:
        pv = s.get("param_value", base_value)
        mv = s.get("metric_value", base_metric)
        if pv != base_value and base_metric != 0:
            eps = ((mv - base_metric) / base_metric) / ((pv - base_value) / base_value)
            elasticities.append(eps)

    elasticity = _mean(elasticities) if elasticities else 0.0

    # 归一化敏感度：CV_metric / CV_param
    cv_param = _std(param_values) / _mean(param_values) if _mean(param_values) != 0 else 0.0
    cv_metric = _std(metric_values) / _mean(metric_values) if _mean(metric_values) != 0 else 0.0
    normalized = cv_metric / cv_param if cv_param != 0 else 0.0

    return SensitivityAnalysis(
        parameter_name=param_name,
        base_value=base_value,
        base_metric=base_metric,
        samples=samples,
        elasticity=round(elasticity, 4),
        normalized_sensitivity=round(normalized, 4),
        ranking=0,
    )


def compute_distribution_bins(data: list[float], bins: int = 10) -> list[dict]:
    """计算直方图分箱数据"""
    if not data:
        return []
    sorted_data = sorted(data)
    n = len(sorted_data)
    min_v, max_v = sorted_data[0], sorted_data[-1]
    if min_v == max_v:
        return [{"bin_start": min_v, "bin_end": max_v, "count": n, "density": 1.0}]

    bin_width = (max_v - min_v) / bins
    result = []
    for i in range(bins):
        b_start = min_v + i * bin_width
        b_end = b_start + bin_width
        count = sum(1 for x in sorted_data if b_start <= x < b_end) + (1 if i == bins - 1 else 0)
        # 修正最后一个 bin 包含右端点
        if i == bins - 1:
            count = sum(1 for x in sorted_data if b_start <= x <= b_end)
        else:
            count = sum(1 for x in sorted_data if b_start <= x < b_end)
        result.append({
            "bin_start": round(b_start, 2),
            "bin_end": round(b_end, 2),
            "count": count,
            "density": round(count / n, 4),
        })
    return result


def boxplot_stats(data: list[float]) -> dict:
    """计算箱线图所需统计量"""
    if not data:
        return {"min": 0, "q1": 0, "median": 0, "q3": 0, "max": 0, "outliers": []}
    sorted_data = sorted(data)
    q1 = _quantile(data, 0.25)
    q3 = _quantile(data, 0.75)
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr

    outliers = [x for x in sorted_data if x < lower_fence or x > upper_fence]
    whisker_low = min(x for x in sorted_data if x >= lower_fence)
    whisker_high = max(x for x in sorted_data if x <= upper_fence)

    return {
        "min": whisker_low,
        "q1": q1,
        "median": _median(data),
        "q3": q3,
        "max": whisker_high,
        "outliers": outliers,
    }
