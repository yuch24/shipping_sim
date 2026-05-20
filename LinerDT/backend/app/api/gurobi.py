import asyncio
import csv
import os
import subprocess
import json

import sys

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/api/gurobi", tags=["gurobi"])

PYTHON_EXE = os.environ.get(
    "PYTHON_EXE_FOR_GUROBI",
    sys.executable,
)

IP_MODEL_BASE = os.environ.get(
    "IP_MODEL_BASE_PATH",
    r"D:\A_lessonwork\shipping_simulation\Shipping_Integer_Programming_Model",
)
IP_DATA_DIR = os.path.join(IP_MODEL_BASE, "data")
IP_OUTPUT_DIR = os.path.join(IP_MODEL_BASE, "output")
IP_SRC_DIR = os.path.join(IP_MODEL_BASE, "src")


class OrderItem(BaseModel):
    orderID: str
    originPort: str
    destPort: str
    revenuePerTEU: float
    volumeTEU: float
    routeID: str
    deadline: float


class UploadOrdersRequest(BaseModel):
    orders: List[OrderItem]
    week: int


@router.post("/upload-orders")
async def upload_orders(req: UploadOrdersRequest):
    orders_path = os.path.join(IP_DATA_DIR, "orders.csv")
    os.makedirs(IP_DATA_DIR, exist_ok=True)

    with open(orders_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "orderID",
                "originPort",
                "destPort",
                "revenuePerTEU",
                "volumeTEU",
                "routeID",
                "deadline",
            ]
        )
        for o in req.orders:
            deadline_days = o.deadline / 24.0
            writer.writerow(
                [
                    o.orderID,
                    o.originPort,
                    o.destPort,
                    o.revenuePerTEU,
                    o.volumeTEU,
                    o.routeID,
                    f"{deadline_days:.2f}",
                ]
            )

    return {"status": "ok", "count": len(req.orders), "week": req.week}


@router.post("/solve")
async def solve_optimization(req: UploadOrdersRequest):
    upload_resp = await upload_orders(req)
    if upload_resp["status"] != "ok":
        raise HTTPException(status_code=500, detail="Failed to save orders")

    delta_matrix_path = os.path.join(IP_OUTPUT_DIR, "delta_matrix_final.csv")
    feasibility_path = os.path.join(IP_OUTPUT_DIR, "feasibility.csv")
    for f in [delta_matrix_path, feasibility_path]:
        if os.path.exists(f):
            os.remove(f)

    env = os.environ.copy()
    env["IP_MODEL_BASE_PATH"] = IP_MODEL_BASE

    gen_script = os.path.join(IP_SRC_DIR, "generate_delta_matrix.py")
    solve_script = os.path.join(IP_SRC_DIR, "solve_container_allocation.py")

    try:
        proc_gen = await asyncio.create_subprocess_exec(
            PYTHON_EXE,
            gen_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout_gen, stderr_gen = await proc_gen.communicate()
        if proc_gen.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"generate_delta_matrix failed: {stderr_gen.decode(errors='replace')}",
            )

        proc_solve = await asyncio.create_subprocess_exec(
            PYTHON_EXE,
            solve_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout_solve, stderr_solve = await proc_solve.communicate()
        if proc_solve.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"solve_container_allocation failed: {stderr_solve.decode(errors='replace')}",
            )
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Script not found: {e}")

    planned_path = os.path.join(IP_OUTPUT_DIR, "planned_orders.csv")
    if not os.path.exists(planned_path):
        raise HTTPException(status_code=500, detail="planned_orders.csv not generated")

    planned_orders = []
    with open(planned_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            deadline_hours = float(row["deadline"]) * 24.0
            planned_orders.append(
                {
                    "orderID": row["orderID"],
                    "originPort": row["originPort"],
                    "destPort": row["destPort"],
                    "revenuePerTEU": float(row["revenuePerTEU"]),
                    "volumeTEU": float(row["volumeTEU"]),
                    "routeID": row["routeID"],
                    "deadline": deadline_hours,
                }
            )

    return {"status": "ok", "planned_orders": planned_orders, "week": req.week}
