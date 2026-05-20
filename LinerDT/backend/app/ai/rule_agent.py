from typing import Optional, Dict, Any
from .base_agent import BaseAIAgent, DecisionContext, AIDecision, DecisionType
from .decision_rules import get_decision_rule_service


def _get_param(rule_id: str, param_key: str, default: float) -> float:
    """从动态规则服务获取参数值，失败时返回默认值。"""
    try:
        return get_decision_rule_service().get_param(rule_id, param_key, default)
    except Exception:
        return default


class RuleBasedAIAgent(BaseAIAgent):
    def __init__(self, name: str = "RuleBasedAI"):
        super().__init__(name)
        self.cii_warning_threshold = 1.15
        self.cii_critical_threshold = 1.35
        self.delay_tolerance_hours = 12.0
        self.max_speed_over_economic = 1.0
        self.speed_adjustment_cooldown = 24.0
        self._last_speed_adjustment: Dict[str, float] = {}

    def _read_thresholds(self):
        """从动态规则刷新阈值。"""
        self.cii_warning_threshold = _get_param("cii_thresholds", "cii_warning", self.cii_warning_threshold)
        self.cii_critical_threshold = _get_param("cii_thresholds", "cii_critical", self.cii_critical_threshold)
        self.delay_tolerance_hours = _get_param("delay_tolerance", "tolerance_hours", self.delay_tolerance_hours)
        self.speed_adjustment_cooldown = _get_param("speed_cooldown", "cooldown_hours", self.speed_adjustment_cooldown)
        self.max_speed_over_economic = _get_param("cii_thresholds", "eco_speed_over_economic", self.max_speed_over_economic)

    def evaluate_speed(
        self,
        context: DecisionContext,
        target_arrival_time: Optional[float] = None
    ) -> Optional[AIDecision]:
        self._read_thresholds()  # 每次评估前刷新动态规则
        current_speed = context.current_speed
        economic_speed = context.economic_speed
        cii_ratio = context.cii_ratio
        delay = context.cumulative_delay

        suggested_speed = None
        reason = ""
        confidence = 0.8

        if cii_ratio >= self.cii_critical_threshold:
            suggested_speed = economic_speed
            reason = (
                f"CII比率{cii_ratio:.2f}已达到D级临界值({self.cii_critical_threshold})，"
                f"降至经济航速{economic_speed}节以减少排放"
            )
            confidence = 0.95

        elif cii_ratio >= self.cii_warning_threshold:
            if delay > self.delay_tolerance_hours:
                suggested_speed = min(
                    economic_speed + self.max_speed_over_economic,
                    context.design_speed * 0.9
                )
                reason = (
                    f"CII比率{cii_ratio:.2f}偏高，但存在严重延误({delay:.1f}h)，"
                    f"允许轻微超经济航速加速赶班"
                )
                confidence = 0.75
            else:
                suggested_speed = economic_speed * 0.95
                reason = (
                    f"CII比率{cii_ratio:.2f}偏高但无严重延误，"
                    f"微调至经济航速的95%({economic_speed * 0.95:.1f}节)"
                )
                confidence = 0.85

        elif target_arrival_time is not None:
            time_needed = self._estimate_arrival_time(context)
            if time_needed > target_arrival_time:
                max_allowed = min(
                    economic_speed + self.max_speed_over_economic,
                    context.design_speed * 0.9
                )
                suggested_speed = max_allowed
                reason = (
                    f"目标到港时间{target_arrival_time}h，当前速度需{time_needed:.1f}h，"
                    f"提速至{max_allowed:.1f}节赶班"
                )
                confidence = 0.7
            elif time_needed < target_arrival_time * 0.8:
                suggested_speed = economic_speed * 0.9
                reason = (
                    f"提前到达{time_needed:.1f}h vs 目标{target_arrival_time}h，"
                    f"减速至{economic_speed * 0.9:.1f}节以节省燃油"
                )
                confidence = 0.65

        if suggested_speed is not None and abs(suggested_speed - current_speed) > 0.5:
            last_adjustment_time = self._last_speed_adjustment.get(context.ship_id, -999)
            if context.sim_time - last_adjustment_time < self.speed_adjustment_cooldown:
                return None

            self._last_speed_adjustment[context.ship_id] = context.sim_time

            return AIDecision(
                decision_type=DecisionType.SPEED_ADJUSTMENT,
                ship_id=context.ship_id,
                suggested_action="adjust_speed",
                suggested_value=suggested_speed,
                reason=reason,
                confidence=confidence,
                context={
                    "current_speed": current_speed,
                    "economic_speed": economic_speed,
                    "cii_ratio": cii_ratio,
                    "cumulative_delay": delay,
                }
            )

        return None

    def evaluate_port_timing(
        self,
        context: DecisionContext,
        available_ports: list[str]
    ) -> Optional[AIDecision]:
        if len(available_ports) <= 1:
            return None

        best_port = None
        best_score = float('-inf')
        reason = ""

        for port_id in available_ports:
            score = self._score_port(context, port_id)
            if score > best_score:
                best_score = score
                best_port = port_id

        if best_port and best_port != context.next_port:
            return AIDecision(
                decision_type=DecisionType.PORT_SELECTION,
                ship_id=context.ship_id,
                suggested_action="change_next_port",
                suggested_value=best_port,
                reason=f"港口{best_port}综合评分({best_score:.1f})优于当前{best_port}",
                confidence=0.7,
                context={
                    "available_ports": available_ports,
                    "scores": {p: self._score_port(context, p) for p in available_ports}
                }
            )

        return None

    def _score_port(self, context: DecisionContext, port_id: str) -> float:
        score = 100.0

        if hasattr(context, 'port_queues'):
            queue_length = context.port_queues.get(port_id, 0)
            score -= queue_length * 10

        if hasattr(context, 'port_berth_available'):
            if context.port_berth_available.get(port_id, False):
                score += 20

        return score

    def _estimate_arrival_time(self, context: DecisionContext) -> float:
        if context.current_port and context.next_port:
            from app.services.navigation import haversine
            from app.scheduler.scheduler import get_model

            model = get_model()
            next_port = model.get_port(context.next_port)

            if next_port and context.lat and context.lon:
                distance = haversine(context.lat, context.lon, next_port.lat, next_port.lon)
                return distance / context.current_speed

        return 0.0


class CIIAwareAIAgent(RuleBasedAIAgent):
    def __init__(self, name: str = "CIIAwareAI"):
        super().__init__(name)
        self.cii_target_rating = "B"
        self.cii_rating_thresholds = {
            "A": 0.098,
            "B": 0.115,
            "C": 0.132,
            "D": 0.155,
            "E": 0.178,
        }

    def get_cii_rating(self, cii_value: float) -> str:
        for rating, threshold in sorted(self.cii_rating_thresholds.items(), key=lambda x: x[1]):
            if cii_value <= threshold:
                return rating
        return "E"

    def evaluate_speed(self, context: DecisionContext, target_arrival_time: Optional[float] = None) -> Optional[AIDecision]:
        self._read_thresholds()  # 刷新动态规则
        current_rating = self.get_cii_rating(context.cii_ratio * context.cii_ratio)
        target_rating = self.cii_target_rating

        if current_rating > target_rating:
            rating_diff = ord(current_rating) - ord(target_rating)
            speed_reduction = min(0.1 * rating_diff, 0.25)

            suggested_speed = context.economic_speed * (1 - speed_reduction)

            return AIDecision(
                decision_type=DecisionType.SPEED_ADJUSTMENT,
                ship_id=context.ship_id,
                suggested_action="reduce_speed_for_cii",
                suggested_value=suggested_speed,
                reason=(
                    f"CII评级{current_rating}低于目标{target_rating}，"
                    f"降速{speed_reduction*100:.0f}%至{suggested_speed:.1f}节"
                ),
                confidence=0.9,
                context={
                    "current_rating": current_rating,
                    "target_rating": target_rating,
                    "cii_value": context.cii_ratio,
                    "speed_reduction": speed_reduction,
                }
            )

        return super().evaluate_speed(context, target_arrival_time)


class BalancedAgent(RuleBasedAIAgent):
    """多目标均衡代理 — 综合考量延误、碳排放、燃油成本和港口效率。"""

    def __init__(self, name: str = "BalancedAI"):
        super().__init__(name)
        # 决策权重
        self.weights = {
            "delay": 0.40,
            "cii": 0.20,
            "fuel": 0.20,
            "port": 0.20,
        }
        self._read_balanced_thresholds()  # 初始化时即从规则加载

    def _read_balanced_thresholds(self):
        self._read_thresholds()
        self.weights["delay"] = _get_param("delay_tolerance", "delay_weight", self.weights["delay"])
        self.weights["cii"] = _get_param("delay_tolerance", "cii_weight", self.weights["cii"])
        self.weights["fuel"] = _get_param("delay_tolerance", "fuel_weight", self.weights["fuel"])
        self.weights["port"] = _get_param("delay_tolerance", "port_weight", self.weights["port"])
        self.delay_critical = _get_param("speed_priority", "delay_critical", 48.0)
        self.delay_warning = _get_param("speed_priority", "delay_warning", 24.0)
        self.speed_boost_critical = _get_param("speed_priority", "speed_boost_critical", 1.5)
        self.speed_boost_warning = _get_param("speed_priority", "speed_boost_warning", 1.0)
        self.max_speed_pct = _get_param("speed_priority", "max_speed_pct", 0.92)

    def evaluate_speed(
        self,
        context: DecisionContext,
        target_arrival_time: Optional[float] = None
    ) -> Optional[AIDecision]:
        self._read_balanced_thresholds()  # 刷新动态规则
        current_speed = context.current_speed
        economic_speed = context.economic_speed
        cii_ratio = context.cii_ratio
        delay = context.cumulative_delay

        suggested_speed = None
        reason = ""
        confidence = 0.8

        # 计算各维度得分
        delay_score = min(delay / self.delay_critical, 1.0)
        cii_score = max(0, (cii_ratio - 1.0) / 0.5)
        composite_score = (
            self.weights["delay"] * delay_score +
            self.weights["cii"] * cii_score
        )

        # 决策逻辑：综合评分导向
        if delay >= self.delay_critical:
            # 严重延误：优先赶班
            if cii_ratio >= self.cii_critical_threshold:
                # CII也严重时，适度妥协
                suggested_speed = min(current_speed * 1.05, context.design_speed * self.max_speed_pct)
                reason = (
                    f"严重延误{delay:.0f}h但CII={cii_ratio:.2f}偏高，"
                    f"轻微提速至{suggested_speed:.1f}节，兼顾减排与赶班"
                )
                confidence = 0.75
            else:
                suggested_speed = min(current_speed + self.speed_boost_critical, context.design_speed * self.max_speed_pct)
                reason = (
                    f"严重延误{delay:.0f}h，CII评级正常，"
                    f"提速至{suggested_speed:.1f}节赶班"
                )
                confidence = 0.85

        elif delay >= self.delay_warning:
            # 中度延误 + CII检查
            if cii_ratio >= self.cii_warning_threshold:
                suggested_speed = economic_speed * 1.0
                reason = (
                    f"延误{delay:.0f}h与CII={cii_ratio:.2f}均偏高，"
                    f"保持经济航速{economic_speed}节，平衡两者"
                )
                confidence = 0.75
            else:
                suggested_speed = min(current_speed + self.speed_boost_warning, context.design_speed * self.max_speed_pct)
                reason = (
                    f"中度延误{delay:.0f}h，CII正常，"
                    f"适度提速至{suggested_speed:.1f}节"
                )
                confidence = 0.8

        elif cii_ratio >= self.cii_critical_threshold:
            # CII严重超标
            suggested_speed = economic_speed * 0.95
            reason = (
                f"CII={cii_ratio:.2f}偏高，延误{delay:.0f}h尚可接受，"
                f"降速至{economic_speed * 0.95:.1f}节优化碳效率"
            )
            confidence = 0.85

        elif cii_ratio >= self.cii_warning_threshold and delay < 12:
            # CII警告但无延误
            suggested_speed = economic_speed * 0.95
            reason = (
                f"CII={cii_ratio:.2f}偏高，无严重延误，"
                f"微降速至{economic_speed * 0.95:.1f}节"
            )
            confidence = 0.8

        elif target_arrival_time is not None:
            time_needed = self._estimate_arrival_time(context)
            if time_needed > target_arrival_time:
                max_allowed = min(economic_speed + self.speed_boost_warning, context.design_speed * self.max_speed_pct)
                suggested_speed = max_allowed
                reason = f"目标到港时间紧张，提速至{max_allowed:.1f}节赶班"
                confidence = 0.7

        if suggested_speed is not None and abs(suggested_speed - current_speed) > 0.5:
            last_adjustment_time = self._last_speed_adjustment.get(context.ship_id, -999)
            if context.sim_time - last_adjustment_time < self.speed_adjustment_cooldown:
                return None
            self._last_speed_adjustment[context.ship_id] = context.sim_time

            return AIDecision(
                decision_type=DecisionType.SPEED_ADJUSTMENT,
                ship_id=context.ship_id,
                suggested_action="adjust_speed",
                suggested_value=suggested_speed,
                reason=reason,
                confidence=confidence,
                context={
                    "current_speed": current_speed,
                    "economic_speed": economic_speed,
                    "cii_ratio": cii_ratio,
                    "cumulative_delay": delay,
                    "composite_score": round(composite_score, 3),
                }
            )

        return None
