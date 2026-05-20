from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from enum import Enum
import threading


class ExplanationLevel(Enum):
    BRIEF = "brief"
    STANDARD = "standard"
    DETAILED = "detailed"


@dataclass
class DecisionExplanation:
    decision_type: str
    ship_id: str
    summary: str
    reasoning: List[str]
    impact: Dict[str, Any]
    alternatives_considered: List[str]
    recommendation: str
    confidence_label: str


class DecisionInterpreter:
    SPEED_IMPACT = {
        "increase": "提速 {speed} 节",
        "decrease": "降速 {speed} 节",
        "maintain": "保持当前航速 {speed} 节",
    }

    def __init__(self):
        self.explanation_cache: Dict[str, List[DecisionExplanation]] = {}

    def interpret_speed_decision(
        self,
        ship_id: str,
        ship_name: str,
        current_speed: float,
        suggested_speed: float,
        cii_ratio: float,
        cii_rating: str,
        cumulative_delay: float,
        reason: str,
        confidence: float,
        level: ExplanationLevel = ExplanationLevel.STANDARD,
    ) -> DecisionExplanation:
        speed_change = suggested_speed - current_speed
        abs_change = abs(speed_change)

        summary_parts = []
        reasoning = []
        alternatives = []
        impact = {}

        # 综合考量：延误 + CII + 航速
        if cumulative_delay > 24:
            if cii_ratio >= 1.35:
                summary_parts.append(f"存在 {cumulative_delay:.1f}h 延误且碳排放评级 {cii_rating}，需权衡降碳与准班")
                reasoning.append(f"CII 比率 {cii_ratio:.2f} 偏高（评级 {cii_rating}），同时存在 {cumulative_delay:.1f}h 延误")
                reasoning.append("建议优先控制碳排放，接受一定延误")
                impact["delay_impact"] = f"预计延误增加 {min(abs_change * 2, 12):.0f}h"
            else:
                summary_parts.append(f"存在 {cumulative_delay:.1f}h 延误，碳排放评级 {cii_rating} 处于正常范围")
                reasoning.append(f"优先追赶班期，在下一港评估能否恢复正常")
                impact["delay_recovery"] = f"预计可追回 {min(cumulative_delay * 0.4, 8):.1f}h"
        else:
            if cii_ratio >= 1.35:
                summary_parts.append(f"碳排放评级 {cii_rating}，建议适度降速优化碳效率")
                reasoning.append(f"CII 比率 {cii_ratio:.2f} 偏高，当前延误 {cumulative_delay:.1f}h 尚可接受")
                impact["fuel_savings"] = f"约 {abs_change * 3:.0f}% 油耗降低"
            else:
                summary_parts.append("运营状态正常，维持当前航速策略")
                reasoning.append(f"CII 比率 {cii_ratio:.2f}，延误 {cumulative_delay:.1f}h，均在正常范围")
                impact["stability"] = "当前策略可持续"

        if abs_change > 0.5:
            if speed_change > 0:
                summary_parts.append(f"建议提速 {abs_change:.1f} 节")
            else:
                summary_parts.append(f"建议降速 {abs_change:.1f} 节")

        summary = f"船舶 {ship_name}: {'; '.join(summary_parts)}"

        confidence_label = (
            "高" if confidence >= 0.9
            else "中" if confidence >= 0.7
            else "低"
        )

        recommendation = self._generate_recommendation(
            cii_ratio, cii_rating, cumulative_delay, speed_change
        )

        return DecisionExplanation(
            decision_type="speed_adjustment",
            ship_id=ship_id,
            summary=summary,
            reasoning=reasoning,
            impact=impact,
            alternatives_considered=alternatives,
            recommendation=recommendation,
            confidence_label=confidence_label,
        )

    def interpret_port_decision(
        self,
        ship_id: str,
        ship_name: str,
        current_port: str,
        suggested_port: str,
        queue_difference: int,
        reason: str,
        confidence: float,
    ) -> DecisionExplanation:
        reasoning = [
            f"当前选择: {current_port}",
            f"建议选择: {suggested_port}",
            f"队列差异: {suggested_port} 队列比 {current_port} 短 {queue_difference} 艘",
        ]

        impact = {
            "estimated_wait_savings": f"{queue_difference * 4:.0f} 小时",
            "fuel_impact": "基本持平",
        }

        alternatives = [
            f"继续前往 {current_port} → 预计等待时间更长",
            f"考虑第三选择 → 需评估额外航程成本",
        ]

        summary = (
            f"船舶 {ship_name}: "
            f"{suggested_port} 排队船只较少，建议调整挂靠顺序"
        )

        recommendation = (
            f"建议提前通知船代调整挂港计划，"
            f"预计可节省 {queue_difference * 4:.0f} 小时在港等待时间"
        )

        confidence_label = (
            "高" if confidence >= 0.85
            else "中" if confidence >= 0.7
            else "低"
        )

        return DecisionExplanation(
            decision_type="port_selection",
            ship_id=ship_id,
            summary=summary,
            reasoning=reasoning,
            impact=impact,
            alternatives_considered=alternatives,
            recommendation=recommendation,
            confidence_label=confidence_label,
        )

    def _generate_recommendation(
        self,
        cii_ratio: float,
        cii_rating: str,
        cumulative_delay: float,
        speed_change: float,
    ) -> str:
        recommendations = []

        # 综合推荐：优先考虑延误，其次CII
        if cumulative_delay > 48:
            recommendations.append(f"⚠️ 累计延误 {cumulative_delay:.1f}h，建议优先赶班")
            if speed_change > 0:
                recommendations.append(f"提速 {abs(speed_change):.1f} 节后预计可逐步追回延误")
        elif cumulative_delay > 24:
            recommendations.append(f"⚡ 存在 {cumulative_delay:.1f}h 延误，视情况适度提速")
        elif cii_ratio >= 1.35:
            recommendations.append(f"⚠️ CII 比率 {cii_ratio:.2f}（评级 {cii_rating}），建议适度降速")
            if speed_change < 0:
                recommendations.append("降速将改善碳效率，但需关注对班期的影响")
        else:
            recommendations.append("✓ 运营状态良好，维持当前航速策略")

        return "\n".join(recommendations)

    def format_explanation(
        self,
        explanation: DecisionExplanation,
        level: ExplanationLevel = ExplanationLevel.STANDARD,
    ) -> str:
        lines = [f"📋 {explanation.summary}"]

        if level == ExplanationLevel.BRIEF:
            return lines[0]

        lines.append(f"\n🔍 决策依据:")
        for r in explanation.reasoning:
            lines.append(f"  • {r}")

        if level == ExplanationLevel.DETAILED:
            lines.append(f"\n📊 影响预估:")
            for key, value in explanation.impact.items():
                lines.append(f"  • {key}: {value}")

            lines.append(f"\n🔄 备选方案:")
            for alt in explanation.alternatives_considered:
                lines.append(f"  • {alt}")

        lines.append(f"\n💡 建议: {explanation.recommendation}")
        lines.append(f"\n📶 置信度: {explanation.confidence_label}")

        return "\n".join(lines)


_interpreter_lock: threading.Lock = threading.Lock()
_interpreter: Optional[DecisionInterpreter] = None


def get_decision_interpreter() -> DecisionInterpreter:
    global _interpreter
    if _interpreter is None:
        with _interpreter_lock:
            if _interpreter is None:
                _interpreter = DecisionInterpreter()
    return _interpreter
