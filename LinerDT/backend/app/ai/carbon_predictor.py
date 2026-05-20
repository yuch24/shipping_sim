from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import math
import threading


@dataclass
class EmissionPrediction:
    predicted_total_co2: float
    confidence_interval: Tuple[float, float]
    days_covered: int
    trend: str
    peak_emission_day: Optional[int] = None
    estimated_rating: Optional[str] = None


@dataclass
class ShipEmissionProfile:
    ship_id: str
    ship_name: str
    capacity_teu: int
    base_daily_consumption: float
    historical_daily_emissions: List[float]
    average_speed: float

    def get_trend(self) -> str:
        if len(self.historical_daily_emissions) < 7:
            return "insufficient_data"

        recent_week = self.historical_daily_emissions[-7:]
        previous_week = self.historical_daily_emissions[-14:-7] if len(self.historical_daily_emissions) >= 14 else recent_week

        recent_avg = sum(recent_week) / len(recent_week)
        previous_avg = sum(previous_week) / len(previous_week)

        if previous_avg == 0:
            return "stable"

        change_pct = ((recent_avg - previous_avg) / previous_avg) * 100

        if change_pct > 10:
            return "increasing"
        elif change_pct < -10:
            return "decreasing"
        else:
            return "stable"

    def predict_next_30_days(self) -> EmissionPrediction:
        if len(self.historical_daily_emissions) < 3:
            return EmissionPrediction(
                predicted_total_co2=0.0,
                confidence_interval=(0.0, 0.0),
                days_covered=30,
                trend="insufficient_data",
            )

        recent_emissions = self.historical_daily_emissions[-min(14, len(self.historical_daily_emissions)):]
        avg_daily = sum(recent_emissions) / len(recent_emissions)
        variance = sum((e - avg_daily) ** 2 for e in recent_emissions) / len(recent_emissions)
        std_dev = math.sqrt(variance) if variance > 0 else avg_daily * 0.1

        trend = self.get_trend()
        if trend == "increasing":
            daily_growth = 0.02
            predicted = [avg_daily * (1 + daily_growth * i) for i in range(1, 31)]
        elif trend == "decreasing":
            daily_reduction = 0.02
            predicted = [avg_daily * (1 - daily_reduction * i) for i in range(1, 31)]
        else:
            predicted = [avg_daily] * 30

        total_co2 = sum(predicted)

        confidence_multiplier = 1.96
        margin = std_dev * confidence_multiplier * math.sqrt(30)
        confidence_interval = (
            max(0, total_co2 - margin),
            total_co2 + margin
        )

        peak_day = None
        if trend == "increasing":
            peak_day = 30

        estimated_rating = self._estimate_cii_rating(total_co2 / 30)

        return EmissionPrediction(
            predicted_total_co2=total_co2,
            confidence_interval=confidence_interval,
            days_covered=30,
            trend=trend,
            peak_emission_day=peak_day,
            estimated_rating=estimated_rating,
        )

    def _estimate_cii_rating(self, daily_avg_co2: float) -> str:
        annual_co2 = daily_avg_co2 * 365
        estimated_cii = annual_co2 / (self.capacity_teu * 150000)
        reference = 0.115

        cii_ratio = estimated_cii / reference if reference > 0 else 1.0

        if cii_ratio <= 0.85:
            return "A"
        elif cii_ratio <= 1.00:
            return "B"
        elif cii_ratio <= 1.15:
            return "C"
        elif cii_ratio <= 1.35:
            return "D"
        else:
            return "E"

    def get_efficiency_score(self) -> float:
        if len(self.historical_daily_emissions) < 3:
            return 0.0

        recent_emissions = self.historical_daily_emissions[-7:]
        avg_daily = sum(recent_emissions) / len(recent_emissions)

        expected_daily = (self.average_speed / 22.0) ** 3 * self.base_daily_consumption * 3.114 / 24

        if expected_daily == 0:
            return 0.0

        efficiency_ratio = expected_daily / avg_daily if avg_daily > 0 else 0.0

        return min(1.0, efficiency_ratio)


class CarbonPredictor:
    def __init__(self):
        self.fleet_profiles: Dict[str, ShipEmissionProfile] = {}

    def update_profile(
        self,
        ship_id: str,
        ship_name: str,
        capacity_teu: int,
        base_daily_consumption: float,
        current_speed: float,
        daily_co2: float,
    ) -> None:
        if ship_id not in self.fleet_profiles:
            self.fleet_profiles[ship_id] = ShipEmissionProfile(
                ship_id=ship_id,
                ship_name=ship_name,
                capacity_teu=capacity_teu,
                base_daily_consumption=base_daily_consumption,
                historical_daily_emissions=[],
                average_speed=current_speed,
            )

        profile = self.fleet_profiles[ship_id]
        profile.historical_daily_emissions.append(daily_co2)
        if len(profile.historical_daily_emissions) > 90:
            profile.historical_daily_emissions.pop(0)

        profile.average_speed = (
            profile.average_speed * 0.7 + current_speed * 0.3
        )

    def predict_ship(self, ship_id: str) -> Optional[EmissionPrediction]:
        if ship_id not in self.fleet_profiles:
            return None
        return self.fleet_profiles[ship_id].predict_next_30_days()

    def predict_fleet(self) -> Dict[str, EmissionPrediction]:
        predictions = {}
        for ship_id in self.fleet_profiles:
            pred = self.predict_ship(ship_id)
            if pred:
                predictions[ship_id] = pred
        return predictions

    def get_fleet_summary(self) -> Dict[str, Any]:
        if not self.fleet_profiles:
            return {
                "total_ships": 0,
                "average_efficiency": 0.0,
                "predictions_available": False,
            }

        predictions = self.predict_fleet()

        total_predicted_co2 = sum(p.predicted_total_co2 for p in predictions.values())

        ratings_count = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0}
        for pred in predictions.values():
            if pred.estimated_rating:
                ratings_count[pred.estimated_rating] = ratings_count.get(pred.estimated_rating, 0) + 1

        avg_efficiency = sum(
            profile.get_efficiency_score()
            for profile in self.fleet_profiles.values()
        ) / len(self.fleet_profiles)

        return {
            "total_ships": len(self.fleet_profiles),
            "total_predicted_co2_30d": total_predicted_co2,
            "ratings_distribution": ratings_count,
            "average_efficiency_score": avg_efficiency,
            "predictions_available": True,
            "fleet_trend": self._get_fleet_trend(),
        }

    def _get_fleet_trend(self) -> str:
        trends = [p.get_trend() for p in self.fleet_profiles.values()]
        if not trends:
            return "unknown"

        increasing = trends.count("increasing")
        decreasing = trends.count("decreasing")
        stable = trends.count("stable")

        if increasing > decreasing and increasing > stable:
            return "worsening"
        elif decreasing > increasing and decreasing > stable:
            return "improving"
        else:
            return "stable"

    def get_optimization_suggestions(self) -> List[Dict[str, any]]:
        suggestions = []

        for ship_id, profile in self.fleet_profiles.items():
            pred = profile.predict_next_30_days()

            if pred.estimated_rating in ["D", "E"]:
                suggestions.append({
                    "ship_id": ship_id,
                    "ship_name": profile.ship_name,
                    "priority": "high" if pred.estimated_rating == "E" else "medium",
                    "current_rating": pred.estimated_rating,
                    "predicted_co2_30d": pred.predicted_total_co2,
                    "suggestion": f"建议降低航速或优化航线以改善 CII 评级",
                    "expected_improvement": "1-2 个等级" if pred.estimated_rating == "E" else "1 个等级",
                })

        suggestions.sort(key=lambda x: 0 if x["priority"] == "high" else 1)

        return suggestions


_carbon_predictor_lock: threading.Lock = threading.Lock()
_predictor: Optional[CarbonPredictor] = None


def get_carbon_predictor() -> CarbonPredictor:
    global _predictor
    if _predictor is None:
        with _carbon_predictor_lock:
            if _predictor is None:
                _predictor = CarbonPredictor()
    return _predictor
