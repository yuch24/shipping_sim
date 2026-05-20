"""
可配置概率分布系统。

提供 8 种分布类型，支持 JSON 序列化/反序列化，
替代 UncertaintyEngine 中硬编码的 random.gauss/uniform 调用。
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional
import random
import math


class DistType(str, Enum):
    NORMAL = "normal"
    UNIFORM = "uniform"
    EXPONENTIAL = "exponential"
    TRIANGULAR = "triangular"
    LOGNORMAL = "lognormal"
    WEIBULL = "weibull"
    BERNOULLI = "bernoulli"
    CONSTANT = "constant"


class Distribution(ABC):
    """分布基类。所有分布实现必须支持 sample() 和 JSON 序列化。"""

    @abstractmethod
    def sample(self) -> float:
        ...

    @abstractmethod
    def to_dict(self) -> dict:
        ...

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> "Distribution":
        ...


class NormalDist(Distribution):
    """正态分布 N(mean, std²)，可选截断至 [min, max]。"""

    def __init__(self, mean: float = 0.0, std: float = 1.0,
                 min_val: Optional[float] = None, max_val: Optional[float] = None):
        self.mean = mean
        self.std = std
        self.min_val = min_val
        self.max_val = max_val

    def sample(self) -> float:
        v = random.gauss(self.mean, self.std)
        if self.min_val is not None:
            v = max(self.min_val, v)
        if self.max_val is not None:
            v = min(self.max_val, v)
        return v

    def to_dict(self) -> dict:
        d: dict = {"type": DistType.NORMAL, "mean": self.mean, "std": self.std}
        if self.min_val is not None:
            d["min"] = self.min_val
        if self.max_val is not None:
            d["max"] = self.max_val
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "NormalDist":
        return cls(data["mean"], data["std"],
                   min_val=data.get("min"), max_val=data.get("max"))


class UniformDist(Distribution):
    """均匀分布 U(low, high)。"""

    def __init__(self, low: float = 0.0, high: float = 1.0):
        self.low = low
        self.high = high

    def sample(self) -> float:
        return random.uniform(self.low, self.high)

    def to_dict(self) -> dict:
        return {"type": DistType.UNIFORM, "low": self.low, "high": self.high}

    @classmethod
    def from_dict(cls, data: dict) -> "UniformDist":
        return cls(data["low"], data["high"])


class ExponentialDist(Distribution):
    """指数分布 Exp(λ)，mean = 1/λ。"""

    def __init__(self, lambd: float = 1.0):
        self.lambd = lambd

    def sample(self) -> float:
        return random.expovariate(self.lambd)

    def to_dict(self) -> dict:
        return {"type": DistType.EXPONENTIAL, "lambd": self.lambd}

    @classmethod
    def from_dict(cls, data: dict) -> "ExponentialDist":
        return cls(data["lambd"])


class TriangularDist(Distribution):
    """三角分布 T(low, mode, high)。"""

    def __init__(self, low: float, mode: float, high: float):
        self.low = low
        self.mode = mode
        self.high = high

    def sample(self) -> float:
        return random.triangular(self.low, self.high, self.mode)

    def to_dict(self) -> dict:
        return {"type": DistType.TRIANGULAR, "low": self.low,
                "mode": self.mode, "high": self.high}

    @classmethod
    def from_dict(cls, data: dict) -> "TriangularDist":
        return cls(data["low"], data["mode"], data["high"])


class LogNormalDist(Distribution):
    """对数正态分布 LogNormal(μ, σ²)。"""

    def __init__(self, mu: float = 0.0, sigma: float = 1.0):
        self.mu = mu
        self.sigma = sigma

    def sample(self) -> float:
        return random.lognormvariate(self.mu, self.sigma)

    def to_dict(self) -> dict:
        return {"type": DistType.LOGNORMAL, "mu": self.mu, "sigma": self.sigma}

    @classmethod
    def from_dict(cls, data: dict) -> "LogNormalDist":
        return cls(data["mu"], data["sigma"])


class WeibullDist(Distribution):
    """威布尔分布 Weibull(shape, scale)。"""

    def __init__(self, shape: float = 1.0, scale: float = 1.0):
        self.shape = shape
        self.scale = scale

    def sample(self) -> float:
        return self.scale * math.pow(-math.log(1.0 - random.random()), 1.0 / self.shape)
        # Note: random.weibullvariate(scale, shape) exists but uses shape/scale swap
        # Manual implementation is cleaner

    def to_dict(self) -> dict:
        return {"type": DistType.WEIBULL, "shape": self.shape, "scale": self.scale}

    @classmethod
    def from_dict(cls, data: dict) -> "WeibullDist":
        return cls(data["shape"], data["scale"])


class BernoulliDist(Distribution):
    """伯努利分布 Bernoulli(p)，以概率 p 返回 1.0，否则返回 0.0。"""

    def __init__(self, prob: float = 0.5):
        self.prob = prob

    def sample(self) -> float:
        return 1.0 if random.random() < self.prob else 0.0

    def to_dict(self) -> dict:
        return {"type": DistType.BERNOULLI, "prob": self.prob}

    @classmethod
    def from_dict(cls, data: dict) -> "BernoulliDist":
        return cls(data["prob"])


class ConstantDist(Distribution):
    """常数分布，始终返回固定值。"""

    def __init__(self, value: float = 0.0):
        self.value = value

    def sample(self) -> float:
        return self.value

    def to_dict(self) -> dict:
        return {"type": DistType.CONSTANT, "value": self.value}

    @classmethod
    def from_dict(cls, data: dict) -> "ConstantDist":
        return cls(data["value"])


# ─── 注册表 ─────────────────────────────────────

DISTRIBUTION_REGISTRY: dict[DistType, type[Distribution]] = {
    DistType.NORMAL: NormalDist,
    DistType.UNIFORM: UniformDist,
    DistType.EXPONENTIAL: ExponentialDist,
    DistType.TRIANGULAR: TriangularDist,
    DistType.LOGNORMAL: LogNormalDist,
    DistType.WEIBULL: WeibullDist,
    DistType.BERNOULLI: BernoulliDist,
    DistType.CONSTANT: ConstantDist,
}


def distribution_from_dict(data: dict) -> Distribution:
    """从字典反序列化为 Distribution 对象。"""
    dtype = DistType(data["type"])
    cls = DISTRIBUTION_REGISTRY[dtype]
    return cls.from_dict(data)


def get_distribution_schema() -> list[dict]:
    """返回所有分布的 schema（用于前端动态表单）。"""
    return [
        {
            "type": dt.value,
            "label": _dist_label(dt),
            "params": _dist_params(dt),
        }
        for dt in DistType
    ]


def _dist_label(dt: DistType) -> str:
    labels = {
        DistType.NORMAL: "正态分布 N(μ, σ²)",
        DistType.UNIFORM: "均匀分布 U(min, max)",
        DistType.EXPONENTIAL: "指数分布 Exp(λ)",
        DistType.TRIANGULAR: "三角分布 T(min, mode, max)",
        DistType.LOGNORMAL: "对数正态分布 LogN(μ, σ²)",
        DistType.WEIBULL: "威布尔分布 W(shape, scale)",
        DistType.BERNOULLI: "伯努利分布 B(p)",
        DistType.CONSTANT: "常数 Constant(v)",
    }
    return labels.get(dt, dt.value)


def _dist_params(dt: DistType) -> list[dict]:
    """每种分布的参数列表，供前端表单自动生成。"""
    params = {
        DistType.NORMAL: [
            {"name": "mean", "label": "均值 μ", "type": "float", "default": 0.0},
            {"name": "std", "label": "标准差 σ", "type": "float", "default": 1.0, "min": 0},
            {"name": "min", "label": "下限（可选）", "type": "float", "optional": True},
            {"name": "max", "label": "上限（可选）", "type": "float", "optional": True},
        ],
        DistType.UNIFORM: [
            {"name": "low", "label": "下限", "type": "float", "default": 0.0},
            {"name": "high", "label": "上限", "type": "float", "default": 1.0},
        ],
        DistType.EXPONENTIAL: [
            {"name": "lambd", "label": "λ (率参数)", "type": "float", "default": 1.0, "min": 0},
        ],
        DistType.TRIANGULAR: [
            {"name": "low", "label": "下限", "type": "float", "default": 0.0},
            {"name": "mode", "label": "众数", "type": "float", "default": 0.5},
            {"name": "high", "label": "上限", "type": "float", "default": 1.0},
        ],
        DistType.LOGNORMAL: [
            {"name": "mu", "label": "μ", "type": "float", "default": 0.0},
            {"name": "sigma", "label": "σ", "type": "float", "default": 1.0, "min": 0},
        ],
        DistType.WEIBULL: [
            {"name": "shape", "label": "形状参数 k", "type": "float", "default": 1.0, "min": 0},
            {"name": "scale", "label": "尺度参数 λ", "type": "float", "default": 1.0, "min": 0},
        ],
        DistType.BERNOULLI: [
            {"name": "prob", "label": "概率 p", "type": "float", "default": 0.5, "min": 0, "max": 1},
        ],
        DistType.CONSTANT: [
            {"name": "value", "label": "常数值", "type": "float", "default": 0.0},
        ],
    }
    return params.get(dt, [])
