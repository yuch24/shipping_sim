from fastapi import APIRouter, Query
from typing import Optional

from ..scheduler.scheduler import get_model, ShipAgent
from ..services.kpi_calculator import get_kpi_calculator
from ..ai.carbon_predictor import get_carbon_predictor

router = APIRouter()


@router.get("/carbon/status")
def get_carbon_status():
    """获取碳排放全局状态摘要"""
    model = get_model()
    kpi_calc = get_kpi_calculator()
    predictor = get_carbon_predictor()

    fleet_summary = predictor.get_fleet_summary()
    carbon_metrics = kpi_calc.get_carbon_metrics()

    return {
        "total_emissions": carbon_metrics.total_emissions,
        "per_ship_average": carbon_metrics.per_ship_average,
        "carbon_intensity": carbon_metrics.carbon_intensity,
        "fleet_summary": {
            "total_ships": fleet_summary.get("total_ships", 0),
            "ratings_distribution": fleet_summary.get("ratings_distribution", {}),
            "average_efficiency_score": fleet_summary.get("average_efficiency_score", 0),
            "fleet_trend": fleet_summary.get("fleet_trend", "unknown"),
        },
        "sim_time": model.current_time,
    }


@router.get("/carbon/ship/{ship_id}")
def get_ship_carbon(ship_id: str):
    """获取单艘船舶的碳排放详情"""
    model = get_model()
    predictor = get_carbon_predictor()
    kpi_calc = get_kpi_calculator()

    agent = model._agents.get(ship_id)
    if not agent or not isinstance(agent, ShipAgent):
        return {"error": f"Ship {ship_id} not found"}

    ship_kpi = kpi_calc._ship_kpis.get(ship_id)
    prediction = predictor.predict_ship(ship_id)

    cii_rating = None
    cii_ratio = None
    if hasattr(agent, '_cii_reference') and agent._cii_reference:
        estimated_cii = getattr(agent, 'estimated_annual_cii', None)
        if estimated_cii:
            cii_ratio = estimated_cii / agent._cii_reference
            if cii_ratio <= 0.85:
                cii_rating = "A"
            elif cii_ratio <= 1.00:
                cii_rating = "B"
            elif cii_ratio <= 1.15:
                cii_rating = "C"
            elif cii_ratio <= 1.35:
                cii_rating = "D"
            else:
                cii_rating = "E"

    return {
        "ship_id": ship_id,
        "name": agent.name,
        "state": agent.state,
        "current_speed": agent.current_speed,
        "economic_speed": agent.economic_speed,
        "design_speed": agent.design_speed,
        "cumulative_co2": round(agent.co2_emissions, 1),
        "estimated_annual_cii": round(estimated_cii, 6) if hasattr(agent, 'estimated_annual_cii') and agent.estimated_annual_cii else None,
        "cii_ratio": round(cii_ratio, 4) if cii_ratio else None,
        "cii_rating": cii_rating,
        "prediction": {
            "predicted_total_co2_30d": round(prediction.predicted_total_co2, 1) if prediction else None,
            "trend": prediction.trend if prediction else "unknown",
            "estimated_rating": prediction.estimated_rating if prediction else None,
        } if prediction else None,
        "total_arrivals": ship_kpi.total_arrivals if ship_kpi else 0,
        "total_delay": round(ship_kpi.total_delay_hours, 1) if ship_kpi else 0,
    }


@router.get("/carbon/predictions")
def get_carbon_predictions():
    """获取所有船舶的碳排放预测"""
    predictor = get_carbon_predictor()
    predictions = predictor.predict_fleet()
    suggestions = predictor.get_optimization_suggestions()
    fleet_summary = predictor.get_fleet_summary()

    return {
        "fleet_summary": fleet_summary,
        "predictions": {
            ship_id: {
                "predicted_total_co2_30d": round(pred.predicted_total_co2, 1),
                "confidence_interval": [round(pred.confidence_interval[0], 1), round(pred.confidence_interval[1], 1)],
                "days_covered": pred.days_covered,
                "trend": pred.trend,
                "estimated_rating": pred.estimated_rating,
            }
            for ship_id, pred in predictions.items()
        },
        "optimization_suggestions": suggestions,
    }


@router.get("/carbon/rating")
def get_cii_ratings():
    """获取所有船舶的 CII 评级"""
    model = get_model()
    ratings = {}

    for ship_id, agent in model._agents.items():
        if isinstance(agent, ShipAgent):
            cii_rating = None
            cii_ratio = None
            if hasattr(agent, '_cii_reference') and agent._cii_reference:
                estimated_cii = agent.estimated_annual_cii if hasattr(agent, 'estimated_annual_cii') else None
                if estimated_cii:
                    cii_ratio = estimated_cii / agent._cii_reference
                    if cii_ratio <= 0.85:
                        cii_rating = "A"
                    elif cii_ratio <= 1.00:
                        cii_rating = "B"
                    elif cii_ratio <= 1.15:
                        cii_rating = "C"
                    elif cii_ratio <= 1.35:
                        cii_rating = "D"
                    else:
                        cii_rating = "E"

            ratings[ship_id] = {
                "name": agent.name,
                "cii_ratio": round(cii_ratio, 4) if cii_ratio else None,
                "cii_rating": cii_rating,
                "cumulative_co2": round(agent.co2_emissions, 1),
            }

    return {"ratings": ratings}


@router.get("/carbon/fuel-cost")
def get_fuel_cost_estimate(
    ship_id: str = Query(None, description="船舶ID"),
):
    """估算燃油成本（模拟数据）"""
    model = get_model()

    if ship_id:
        agent = model._agents.get(ship_id)
        if not agent or not isinstance(agent, ShipAgent):
            return {"error": f"Ship {ship_id} not found"}
        ships = [(ship_id, agent)]
    else:
        ships = [(sid, a) for sid, a in model._agents.items() if isinstance(a, ShipAgent)]

    total_cost = 0
    ship_costs = []
    for sid, agent in ships:
        fuel_kg = agent.co2_emissions / 3.114  # 反向估算燃油消耗量
        cost = fuel_kg * 500 / 1000  # VLSFO ~$500/ton
        total_cost += cost
        ship_costs.append({
            "ship_id": sid,
            "name": agent.name,
            "estimated_fuel_tonnes": round(fuel_kg / 1000, 1),
            "estimated_cost_usd": round(cost, 0),
        })

    return {
        "total_estimated_cost_usd": round(total_cost, 0),
        "fuel_price_per_ton_usd": 500,
        "ships": ship_costs,
    }
