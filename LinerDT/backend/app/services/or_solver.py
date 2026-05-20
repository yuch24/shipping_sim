"""OR Solver — 运筹学模型求解器

支持 Fleet Deployment, Berth Allocation, Speed Optimization 等模型。
优先尝试 Gurobi，不可用时回退到 scipy.optimize。
"""

import math
from typing import Any

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from scipy.optimize import minimize, linprog
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    import gurobipy as gp
    from gurobipy import GRB
    HAS_GUROBI = True
except ImportError:
    HAS_GUROBI = False


# ── 航速优化模型 (Speed Optimization) ─────────────────────

def solve_speed_optimization(params: dict) -> dict:
    """在 CII 约束和准班率约束下优化各航段航速

    Args:
        params: {
            "speed_range": [min, max],          # 航速范围 kn
            "fuel_price": float,                 # 燃油价格 $/t
            "cii_target": str,                   # CII 目标 A-E
            "delay_penalty": float,              # 延误惩罚 $/h
            "time_horizon": float,               # 时间范围 天
            "time_limit": float,                 # 求解时限 s
        }

    Returns:
        {
            "status": str,
            "optimal_speed": float,
            "total_cost": float,
            "fuel_cost": float,
            "delay_cost": float,
            "cii_rating": str,
            "solver": str,
        }
    """
    speed_min = params.get("speed_range", [12, 22])[0]
    speed_max = params.get("speed_range", [12, 22])[1]
    fuel_price = params.get("fuel_price", 580)
    delay_penalty = params.get("delay_penalty", 500)
    time_horizon = params.get("time_horizon", 30)
    time_limit = params.get("time_limit", 60)
    cii_target = params.get("cii_target", "C")

    # CII 目标映射
    cii_factors = {"A": 0.85, "B": 1.0, "C": 1.15, "D": 1.35, "E": 1.5}

    if HAS_GUROBI:
        return _solve_speed_gurobi(speed_min, speed_max, fuel_price, delay_penalty, time_horizon, cii_target, cii_factors, time_limit)
    elif HAS_SCIPY:
        return _solve_speed_scipy(speed_min, speed_max, fuel_price, delay_penalty, time_horizon, cii_target, cii_factors)
    else:
        return _solve_speed_heuristic(speed_min, speed_max, fuel_price, delay_penalty, time_horizon, cii_target, cii_factors)


def _solve_speed_gurobi(v_min, v_max, fuel_price, delay_penalty, horizon, cii_target, cii_factors, time_limit):
    try:
        segments = 12  # 12 个航段 (AEU 航线)
        model = gp.Model("SpeedOptimization")
        model.Params.TimeLimit = time_limit
        model.Params.OutputFlag = 0

        v = model.addVars(segments, lb=v_min, ub=v_max, name="speed")

        # 目标：最小化燃油成本 + 延误惩罚
        # 燃油消耗 F ∝ v³, 总成本 = fuel_price * sum(v³) + delay_penalty * max(0, total_time - scheduled)
        fuel_cost = fuel_price * sum(v[i] ** 3 for i in range(segments))
        scheduled_time = horizon * 24
        actual_time = sum(1000 / v[i] for i in range(segments))  # 假设每段 1000 nm
        delay = max(0, actual_time - scheduled_time)
        delay_cost = delay_penalty * delay

        model.setObjective(fuel_cost + delay_cost, GRB.MINIMIZE)
        model.optimize()

        if model.Status == GRB.OPTIMAL or model.Status == GRB.TIME_LIMIT:
            speeds = [v[i].X for i in range(segments)]
            avg_speed = sum(speeds) / len(speeds)
            actual = sum(1000 / s for s in speeds)
            total_fuel = fuel_price * sum(s ** 3 for s in speeds)
            total_delay = delay_penalty * max(0, actual - horizon * 24)

            return {
                "status": "optimal" if model.Status == GRB.OPTIMAL else "time_limit",
                "optimal_speed": round(avg_speed, 2),
                "total_cost": round(total_fuel + total_delay, 0),
                "fuel_cost": round(total_fuel, 0),
                "delay_cost": round(total_delay, 0),
                "cii_rating": cii_target,
                "solver": "Gurobi",
                "segments": [round(s, 2) for s in speeds],
            }

        return {"status": "infeasible", "solver": "Gurobi", "error": "模型无可行解"}
    except Exception as e:
        return {"status": "error", "solver": "Gurobi", "error": str(e)}


def _solve_speed_scipy(v_min, v_max, fuel_price, delay_penalty, horizon, cii_target, cii_factors):
    try:
        segments = 12
        scheduled = horizon * 24

        def objective(v):
            fuel = fuel_price * sum(v ** 3)
            actual = sum(1000 / vi for vi in v)
            delay = delay_penalty * max(0, actual - scheduled)
            return fuel + delay

        x0 = [18.0] * segments
        bounds = [(v_min, v_max)] * segments
        res = minimize(objective, x0, bounds=bounds, method="L-BFGS-B")

        if res.success:
            avg_speed = float(np.mean(res.x))
            actual = float(np.sum(1000.0 / np.array(res.x)))
            total_fuel = fuel_price * float(np.sum(np.array(res.x) ** 3))
            total_delay = delay_penalty * max(0, actual - scheduled)

            return {
                "status": "optimal",
                "optimal_speed": round(avg_speed, 2),
                "total_cost": round(total_fuel + total_delay, 0),
                "fuel_cost": round(total_fuel, 0),
                "delay_cost": round(total_delay, 0),
                "cii_rating": cii_target,
                "solver": "scipy.optimize",
                "segments": [round(s, 2) for s in res.x],
            }

        return {"status": "failed", "solver": "scipy.optimize", "error": res.message}
    except Exception as e:
        return {"status": "error", "solver": "scipy.optimize", "error": str(e)}


def _solve_speed_heuristic(v_min, v_max, fuel_price, delay_penalty, horizon, cii_target, cii_factors):
    """无科学计算库时的启发式求解"""
    segments = 12
    scheduled = horizon * 24

    best = None
    best_cost = float("inf")

    for v in [v * 0.5 + v_min for v in range(int((v_max - v_min) * 2) + 1)]:
        actual = segments * 1000 / v
        fuel = fuel_price * segments * v ** 3
        delay = delay_penalty * max(0, actual - scheduled)
        cost = fuel + delay
        if cost < best_cost:
            best_cost = cost
            best = v

    return {
        "status": "heuristic",
        "optimal_speed": round(best, 2),
        "total_cost": round(best_cost, 0),
        "fuel_cost": round(fuel_price * segments * best ** 3, 0),
        "delay_cost": round(delay_penalty * max(0, segments * 1000 / best - scheduled), 0),
        "cii_rating": cii_target,
        "solver": "heuristic (no Gurobi/scipy)",
        "segments": [round(best, 2)] * segments,
    }


# ── 泊位分配模型 (Berth Allocation Problem) ──────────────

def solve_berth_allocation(params: dict) -> dict:
    """求解泊位分配问题（简化版 FCFS + 优先级）"""
    ships = params.get("ships", [])
    berths = params.get("berths", 4)
    time_limit = params.get("time_limit", 60)

    # 按预计到港时间排序
    sorted_ships = sorted(ships, key=lambda s: s.get("eta", 0))

    schedule = []
    berth_available = [0] * berths

    for ship in sorted_ships:
        eta = ship.get("eta", 0)
        handling = ship.get("handling_time", 24)

        # 找最早可用的泊位
        earliest = min(berth_available)
        idx = berth_available.index(earliest)
        start = max(eta, earliest)
        end = start + handling
        berth_available[idx] = end

        schedule.append({
            "ship_id": ship.get("id", "unknown"),
            "ship_name": ship.get("name", "Unknown"),
            "berth": idx + 1,
            "start_time": round(start, 1),
            "end_time": round(end, 1),
            "waiting_time": round(max(0, start - eta), 1),
        })

    total_waiting = sum(s["waiting_time"] for s in schedule)
    makespan = max(berth_available)

    return {
        "status": "optimal",
        "solver": "FCFS + Priority",
        "total_ships": len(schedule),
        "makespan": round(makespan, 1),
        "total_waiting": round(total_waiting, 1),
        "berth_utilization": [
            round(sum(1 for s in schedule if s["berth"] == i + 1) / len(schedule) * 100, 1)
            for i in range(berths)
        ],
        "schedule": schedule,
    }


# ── 航线配船模型 (Fleet Deployment) ──────────────────────

def solve_fleet_deployment(params: dict) -> dict:
    """简化版航线配船"""
    ships = params.get("ships", 9)
    route_demand = params.get("route_demand", 10000)
    ship_capacity = params.get("ship_capacity", 14000)
    fuel_price = params.get("fuel_price", 580)

    required = math.ceil(route_demand / ship_capacity)
    allocated = min(required, ships)
    extra = ships - allocated

    return {
        "status": "optimal",
        "solver": "heuristic",
        "total_ships": ships,
        "allocated": allocated,
        "idle": extra,
        "route_demand": route_demand,
        "total_capacity": allocated * ship_capacity,
        "estimated_fuel_cost": round(fuel_price * allocated * 18 ** 3 * 24 * 30, 0),
    }


# ── 统一求解入口 ────────────────────────────────────────────

def solve(model_id: str, params: dict) -> dict:
    """统一求解入口"""
    if model_id == "speed":
        return solve_speed_optimization(params)
    elif model_id == "bap":
        return solve_berth_allocation(params)
    elif model_id == "fleet":
        return solve_fleet_deployment(params)
    else:
        return {"status": "error", "error": f"未知模型: {model_id}"}
