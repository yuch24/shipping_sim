import math
from typing import Any, Dict, List, Optional

import gurobipy as gp
from gurobipy import GRB

from .transit_calculator import TransitCalculator

ROUTES_CONFIG: Dict[str, Dict[str, Any]] = {
    "AEU1": {
        "capacity": 21413,
        "ports": [
            "CNTAO",
            "CNSHA",
            "CNNGB",
            "CNXMN",
            "CNYTN",
            "SGSIN",
            "GBFXT",
            "BEZEE",
            "PLGDY",
            "DEWVN",
            "SGSIN",
            "CNYTN",
            "CNTAO",
        ],
    },
    "AEU2": {
        "capacity": 16000,
        "ports": [
            "CNNGB",
            "CNSHA",
            "CNYTN",
            "SGSIN",
            "MAPTM",
            "FRDKK",
            "GBSOU",
            "FRLEH",
            "MYPKG",
            "CNNGB",
        ],
    },
    "AEU3": {
        "capacity": 19100,
        "ports": [
            "CNTXG",
            "CNDLC",
            "CNTAO",
            "CNSHA",
            "CNNGB",
            "SGSIN",
            "NLRTM",
            "DEHAM",
            "BEANR",
            "CNSHA",
            "CNTXG",
        ],
    },
}

GAMMA = {0: 1.0, 1: 0.3, 2: 0.15, 3: 0.05}
HORIZON_WEEKS = 4
REJECTION_COST_PER_TEU = 5000
DELAY_PENALTY_PER_WEEK = 200

PORT_COST = {
    "CNTAO": 150,
    "CNSHA": 150,
    "CNNGB": 150,
    "CNXMN": 150,
    "CNYTN": 150,
    "CNTXG": 150,
    "CNDLC": 150,
    "SGSIN": 200,
    "MYPKG": 200,
    "MAPTM": 220,
    "GBFXT": 300,
    "BEZEE": 300,
    "PLGDY": 300,
    "DEWVN": 300,
    "FRDKK": 300,
    "GBSOU": 300,
    "FRLEH": 300,
    "NLRTM": 300,
    "DEHAM": 300,
    "BEANR": 300,
}


def _is_route_feasible(origin: str, dest: str, ports: List[str]) -> bool:
    try:
        oi = ports.index(origin)
    except ValueError:
        return False
    n = len(ports)
    for i in range(oi + 1, oi + n):
        if ports[i % n] == dest:
            return True
    return False


def solve_rolling(
    transit_calc: TransitCalculator,
    current_abs_week: int,
    new_orders: List[Dict[str, Any]],
    committed_snapshot: Optional[List[Dict[str, Any]]] = None,
    horizon: int = HORIZON_WEEKS,
) -> Dict[str, Any]:
    committed: Dict[str, Dict[int, float]] = {}
    if committed_snapshot:
        for s in committed_snapshot:
            r = s["routeID"]
            w = int(s["absWeek"])
            v = float(s["allocatedVolume"])
            committed.setdefault(r, {})[w] = committed[r].get(w, 0) + v

    # ---- 订单可行性分析 ----
    order_feas: List[Dict[str, Any]] = []
    for o in new_orders:
        feas = {}
        for rid, cfg in ROUTES_CONFIG.items():
            if not _is_route_feasible(o["originPort"], o["destPort"], cfg["ports"]):
                continue
            transit = transit_calc.get_transit_hours(
                rid, o["originPort"], o["destPort"]
            )
            if transit is None:
                continue
            deadline = float(o["deadline"])
            wait_time = max(0.0, deadline - transit)
            max_dw = int(wait_time // 168)
            feas[rid] = {
                "transit_hours": transit,
                "max_delay_weeks": max_dw,
                "deadline_infeasible": transit > deadline,
            }
        order_feas.append({"order": o, "feasible_routes": feas})

    # ---- 构建模型 ----
    m = gp.Model("RollingAllocation")
    m.setParam("OutputFlag", 0)

    x_vars: Dict[tuple, gp.Var] = {}
    y_vars: Dict[str, gp.Var] = {}

    for of in order_feas:
        o = of["order"]
        oid = o["orderID"]
        vol = float(o["volumeTEU"])
        rev = float(o["revenuePerTEU"])

        y_vars[oid] = m.addVar(lb=0, ub=vol, vtype=GRB.CONTINUOUS, name=f"y_{oid}")

        for rid, info in of["feasible_routes"].items():
            if info["deadline_infeasible"]:
                continue
            max_w = min(
                current_abs_week + info["max_delay_weeks"],
                current_abs_week + horizon - 1,
            )
            for w in range(current_abs_week, max_w + 1):
                vkey = (oid, rid, w)
                x_vars[vkey] = m.addVar(
                    lb=0, ub=vol, vtype=GRB.CONTINUOUS, name=f"x_{oid}_{rid}_{w}"
                )

    # 需求约束
    for of in order_feas:
        oid = of["order"]["orderID"]
        vol = float(of["order"]["volumeTEU"])
        terms = [y_vars[oid]]
        for (oid2, rid, w), var in x_vars.items():
            if oid2 == oid:
                terms.append(var)
        m.addConstr(gp.quicksum(terms) == vol, name=f"demand_{oid}")

    # 舱容约束
    for rid in ROUTES_CONFIG:
        cap = float(ROUTES_CONFIG[rid]["capacity"])
        for w in range(current_abs_week, current_abs_week + horizon):
            terms = []
            for (oid3, rid2, w2), var in x_vars.items():
                if rid2 == rid and w2 == w:
                    terms.append(var)
            if not terms:
                continue
            delta = w - current_abs_week
            gamma = GAMMA.get(delta, 0.0)
            committed_vol = committed.get(rid, {}).get(w, 0.0)
            available = max(0.0, gamma * (cap - committed_vol))
            m.addConstr(gp.quicksum(terms) <= available, name=f"cap_{rid}_{w}")

    # 目标函数
    obj_terms = []
    for (oid, rid, w), var in x_vars.items():
        of = next(f for f in order_feas if f["order"]["orderID"] == oid)
        rev = float(of["order"]["revenuePerTEU"])
        origin = of["order"]["originPort"]
        dest = of["order"]["destPort"]
        load_cost = PORT_COST.get(origin, 150)
        discharge_cost = PORT_COST.get(dest, 300)
        profit_per_teu = rev - load_cost - discharge_cost
        delay_penalty = (w - current_abs_week) * DELAY_PENALTY_PER_WEEK
        obj_terms.append((profit_per_teu - delay_penalty) * var)

    for oid, var in y_vars.items():
        obj_terms.append(-REJECTION_COST_PER_TEU * var)

    m.setObjective(gp.quicksum(obj_terms), GRB.MAXIMIZE)
    m.optimize()

    if m.status not in (GRB.OPTIMAL, GRB.SUBOPTIMAL):
        return {"status": "failed", "gurobi_status": m.status, "allocation_plans": []}

    # ---- 提取结果 ----
    plans: List[Dict[str, Any]] = []
    for (oid, rid, w), var in x_vars.items():
        allocated = var.X
        if allocated <= 0.5:
            continue
        of = next(f for f in order_feas if f["order"]["orderID"] == oid)
        transit = of["feasible_routes"][rid]["transit_hours"]
        plans.append(
            {
                "orderID": oid,
                "targetRoute": rid,
                "targetAbsWeek": w,
                "allocatedVolume": round(allocated, 1),
                "transitHours": transit,
            }
        )

    rejected: List[Dict[str, Any]] = []
    for oid, var in y_vars.items():
        if var.X > 0.5:
            of = next(f for f in order_feas if f["order"]["orderID"] == oid)
            rejected.append({"orderID": oid, "rejectedTEU": round(var.X, 1)})

    return {
        "status": "ok",
        "objective": m.objVal,
        "allocation_plans": plans,
        "rejected_orders": rejected,
        "current_abs_week": current_abs_week,
    }
