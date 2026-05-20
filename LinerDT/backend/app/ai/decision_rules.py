"""
可编辑决策规则系统

存储和管理 AI 决策规则，支持运行时编辑和持久化（JSON 文件）。
每个规则包含可配置参数，替代原先硬编码的阈值。
"""

import json
import os
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

RULES_FILE = os.path.join(os.path.dirname(__file__), "..", "..", ".ai_rules.json")


class RuleParam(BaseModel):
    """规则参数描述"""
    key: str
    label: str
    value: float
    min: float = 0.0
    max: float = 100.0
    step: float = 0.01


class DecisionRule(BaseModel):
    """一条可编辑的决策规则"""
    id: str
    name: str
    description: str
    category: str  # speed_optimization | cii_protection | port_timing
    enabled: bool = True
    params: Dict[str, RuleParam] = {}


# ======== 默认规则定义 ========

def _default_rules() -> list[DecisionRule]:
    return [
        DecisionRule(
            id="speed_priority",
            name="航速优先级",
            description="综合延误和CII指标决定航速调整策略",
            category="speed_optimization",
            enabled=True,
            params={
                "delay_critical": RuleParam(key="delay_critical", label="严重延误阈值(小时)", value=48.0, min=12, max=120, step=1),
                "delay_warning": RuleParam(key="delay_warning", label="中度延误阈值(小时)", value=24.0, min=6, max=72, step=1),
                "speed_boost_critical": RuleParam(key="speed_boost_critical", label="严重延误提速(节)", value=1.5, min=0, max=5, step=0.1),
                "speed_boost_warning": RuleParam(key="speed_boost_warning", label="中度延误提速(节)", value=1.0, min=0, max=5, step=0.1),
                "max_speed_pct": RuleParam(key="max_speed_pct", label="最大航速比例", value=0.92, min=0.7, max=1.0, step=0.01),
            },
        ),
        DecisionRule(
            id="cii_thresholds",
            name="CII排放阈值",
            description="碳排放强度评级阈值和响应策略",
            category="cii_protection",
            enabled=True,
            params={
                "cii_critical": RuleParam(key="cii_critical", label="CII临界阈值(D级/E级)", value=1.35, min=1.0, max=2.0, step=0.01),
                "cii_warning": RuleParam(key="cii_warning", label="CII警告阈值(C级/D级)", value=1.15, min=1.0, max=2.0, step=0.01),
                "cii_reduce_speed_pct": RuleParam(key="cii_reduce_speed_pct", label="CII超标降速比例", value=0.95, min=0.7, max=1.0, step=0.01),
                "eco_speed_over_economic": RuleParam(key="eco_speed_over_economic", label="CII警告时超经济航速(节)", value=1.0, min=0, max=5, step=0.1),
            },
        ),
        DecisionRule(
            id="speed_cooldown",
            name="航速调整冷却",
            description="两次航速调整之间的最短间隔",
            category="speed_optimization",
            enabled=True,
            params={
                "cooldown_hours": RuleParam(key="cooldown_hours", label="冷却时间(小时)", value=24.0, min=0, max=168, step=1),
                "speed_change_min": RuleParam(key="speed_change_min", label="最小调整幅度(节)", value=0.5, min=0.1, max=3.0, step=0.1),
            },
        ),
        DecisionRule(
            id="delay_tolerance",
            name="延误容忍度",
            description="延误容忍阈值，影响航速调整策略",
            category="speed_optimization",
            enabled=True,
            params={
                "tolerance_hours": RuleParam(key="tolerance_hours", label="容忍延误(小时)", value=12.0, min=0, max=72, step=1),
                "delay_weight": RuleParam(key="delay_weight", label="延误权重", value=0.40, min=0, max=1.0, step=0.05),
                "cii_weight": RuleParam(key="cii_weight", label="CII权重", value=0.20, min=0, max=1.0, step=0.05),
                "fuel_weight": RuleParam(key="fuel_weight", label="燃油权重", value=0.20, min=0, max=1.0, step=0.05),
                "port_weight": RuleParam(key="port_weight", label="港口权重", value=0.20, min=0, max=1.0, step=0.05),
            },
        ),
        DecisionRule(
            id="port_timing",
            name="港口调度策略",
            description="港口选择评分策略（备用港口推荐）",
            category="port_timing",
            enabled=False,
            params={
                "queue_penalty": RuleParam(key="queue_penalty", label="排队惩罚分/艘", value=10.0, min=0, max=50, step=1),
                "berth_bonus": RuleParam(key="berth_bonus", label="可用泊位奖励分", value=20.0, min=0, max=100, step=1),
                "congestion_threshold": RuleParam(key="congestion_threshold", label="拥堵阈值(艘)", value=3.0, min=0, max=10, step=1),
            },
        ),
        DecisionRule(
            id="fuel_switch",
            name="ECA燃油切换",
            description="ECA区域自动燃油切换策略",
            category="cii_protection",
            enabled=True,
            params={
                "vlsfo_co2_factor": RuleParam(key="vlsfo_co2_factor", label="VLSFO CO₂因子", value=3.114, min=2.0, max=5.0, step=0.001),
                "mgo_co2_factor": RuleParam(key="mgo_co2_factor", label="MGO CO₂因子", value=3.206, min=2.0, max=5.0, step=0.001),
            },
        ),
    ]


class DecisionRuleService:
    """决策规则服务 — 单例，管理规则的加载/保存。"""

    def __init__(self):
        self._rules: Dict[str, DecisionRule] = {}
        self._load()

    def _load(self) -> None:
        """从 JSON 文件加载规则，文件不存在则使用默认值。"""
        if os.path.exists(RULES_FILE):
            try:
                with open(RULES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    rule = DecisionRule(**item)
                    self._rules[rule.id] = rule
                logger.info(f"已加载 {len(self._rules)} 条决策规则")
                return
            except Exception as e:
                logger.warning(f"加载规则文件失败，使用默认规则: {e}")

        # 使用默认规则
        for rule in _default_rules():
            self._rules[rule.id] = rule
        self._save()

    def _save(self) -> None:
        """保存规则到 JSON 文件。"""
        try:
            data = [rule.model_dump() for rule in self._rules.values()]
            with open(RULES_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存规则文件失败: {e}")

    def get_all_rules(self) -> list[DecisionRule]:
        return list(self._rules.values())

    def get_rules_by_category(self, category: str) -> list[DecisionRule]:
        return [r for r in self._rules.values() if r.category == category]

    def get_rule(self, rule_id: str) -> Optional[DecisionRule]:
        return self._rules.get(rule_id)

    def get_param(self, rule_id: str, param_key: str, default: float = 0.0) -> float:
        """便捷方法：获取指定规则的某个参数值。"""
        rule = self._rules.get(rule_id)
        if rule and rule.enabled and param_key in rule.params:
            return rule.params[param_key].value
        return default

    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> Optional[DecisionRule]:
        """更新规则（参数值、启用状态等）。"""
        rule = self._rules.get(rule_id)
        if not rule:
            return None

        if "enabled" in updates:
            rule.enabled = bool(updates["enabled"])

        if "params" in updates:
            for key, value in updates["params"].items():
                if key in rule.params:
                    rule.params[key].value = float(value)

        self._save()
        return rule

    def reset_to_defaults(self) -> list[DecisionRule]:
        """重置所有规则为默认值。"""
        self._rules = {}
        for rule in _default_rules():
            self._rules[rule.id] = rule
        self._save()
        return self.get_all_rules()


# 全局单例
_service: Optional[DecisionRuleService] = None


def get_decision_rule_service() -> DecisionRuleService:
    global _service
    if _service is None:
        _service = DecisionRuleService()
    return _service
