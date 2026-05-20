"""Academic Lab API — 学术实验室统一后端接口

为 Academic Lab 底部面板提供数据、OR、ML、Notebook、Report 的 API。
"""

import os
import uuid
import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.services import data_pipeline
from app.services import or_solver
from app.services import ml_pipeline
from app.services import notebook_executor
from app.services import report_generator
from app.scheduler.scheduler import get_model

router = APIRouter(prefix="/api/academic-lab", tags=["Academic Lab"])


# ── 数据模型 ────────────────────────────────────────────────

class SolveRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    model_id: str
    params: dict = {}


class TrainRequest(BaseModel):
    task_id: str


class ExecuteRequest(BaseModel):
    script: str


class ReportRequest(BaseModel):
    template_id: str
    sections: list[str] = []


# ── Data Lab ────────────────────────────────────────────────

@router.get("/datasets")
def list_datasets():
    """获取预置数据集列表"""
    return {"datasets": data_pipeline.get_builtin_datasets()}


@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: str):
    """获取数据集内容"""
    try:
        return data_pipeline.load_builtin_dataset(dataset_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"数据集 {dataset_id} 未找到")


@router.post("/datasets/{dataset_id}/import")
def import_dataset(dataset_id: str):
    """将数据集导入仿真"""
    try:
        model = get_model()
        result = data_pipeline.import_dataset_to_simulation(dataset_id, model)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"导入失败: {str(e)}")


@router.post("/datasets/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """上传 CSV 或 JSON 格式的数据集文件"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".csv", ".json", ".xlsx", ".xls"):
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}，请上传 CSV 或 JSON 文件")

    content = await file.read()
    try:
        decoded = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            decoded = content.decode("gbk")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="文件编码不支持，请使用 UTF-8 或 GBK 编码")

    if ext == ".json":
        try:
            data = json.loads(decoded)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"JSON 解析失败: {e}")

        if isinstance(data, dict):
            rows = [[str(k), str(v)] for k, v in data.items()]
            cols = ["key", "value"]
        elif isinstance(data, list) and data:
            cols = list(data[0].keys()) if isinstance(data[0], dict) else [f"col_{i}" for i in range(len(data[0]))]
            rows = [
                [str(v) for v in (item.values() if isinstance(item, dict) else item)]
                for item in data
            ]
        else:
            rows, cols = [], []

        result = {
            "id": f"upload_{uuid.uuid4().hex[:8]}",
            "name": file.filename,
            "columns": cols,
            "rows": rows,
            "total": len(rows),
        }
    else:
        parsed = data_pipeline.parse_csv(decoded)
        result = {
            "id": f"upload_{uuid.uuid4().hex[:8]}",
            "name": file.filename,
            "columns": parsed["columns"],
            "rows": parsed["rows"],
            "total": parsed["total"],
        }

    # 存入临时内存缓存（作为数据集列表项）
    if not hasattr(upload_dataset, "_uploaded"):
        upload_dataset._uploaded = {}
    upload_dataset._uploaded[result["id"]] = result

    return {
        "success": True,
        "dataset": result,
        "message": f"解析成功，共 {result['total']} 行，{len(result['columns'])} 列",
    }


@router.get("/datasets/uploaded")
def list_uploaded():
    """列出本次会话中上传的数据集"""
    items = getattr(upload_dataset, "_uploaded", {})
    return {
        "datasets": [
            {
                "id": did,
                "name": d["name"],
                "rows": d["total"],
                "columns": d["columns"],
            }
            for did, d in items.items()
        ]
    }


# ── OR Lab ──────────────────────────────────────────────────

@router.get("/or/models")
def list_or_models():
    """获取可用运筹学模型列表"""
    return {
        "models": [
            {"id": "fleet", "name": "航线配船 (Fleet Deployment)", "description": "给定航线需求，优化船队配置与航速"},
            {"id": "bap", "name": "泊位分配 (Berth Allocation)", "description": "优化船舶到港后的泊位分配"},
            {"id": "speed", "name": "航速优化 (Slow Steaming)", "description": "在 CII 约束下优化各航段航速"},
        ],
        "solver": or_solver.HAS_GUROBI and "Gurobi" or (or_solver.HAS_SCIPY and "scipy.optimize" or "heuristic"),
    }


@router.post("/or/solve")
def solve_or(req: SolveRequest):
    """求解运筹学模型"""
    result = or_solver.solve(req.model_id, req.params)
    return result


# ── ML Lab ──────────────────────────────────────────────────

@router.get("/ml/tasks")
def list_ml_tasks():
    """获取可用 ML 任务列表"""
    return {"tasks": ml_pipeline.get_task_info()}


@router.post("/ml/train")
def train_model(req: TrainRequest):
    """训练 ML 模型"""
    result = ml_pipeline.train_model(req.task_id)
    return result


# ── Notebook Lab ────────────────────────────────────────────

@router.get("/notebook/templates")
def list_notebook_templates():
    """获取 Notebook 脚本模板"""
    return {"templates": notebook_executor.get_templates()}


@router.post("/notebook/execute")
def execute_notebook(req: ExecuteRequest):
    """执行 Python 脚本"""
    model = get_model()
    result = notebook_executor.execute_script(req.script, model)
    return result


# ── Report Lab ──────────────────────────────────────────────

@router.get("/report/templates")
def list_report_templates():
    """获取报告模板列表"""
    return {"templates": report_generator.get_templates()}


@router.post("/report/generate")
def generate_report(req: ReportRequest):
    """生成实验报告"""
    model = get_model()
    result = report_generator.generate_report(req.template_id, req.sections, model)
    return result
