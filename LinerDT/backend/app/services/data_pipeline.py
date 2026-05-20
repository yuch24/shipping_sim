"""Data Pipeline — 数据集管理、清洗与导入仿真"""

import json
import os
import csv
import io
from typing import Any
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


# ── 预置数据集 ──────────────────────────────────────────────

def get_builtin_datasets() -> list[dict]:
    """返回预置数据集列表"""
    return [
        {
            "id": "ports",
            "name": "全球港口坐标",
            "description": "9 个 AEU 航线港口",
            "rows": 9,
            "source": "builtin",
            "fields": ["ID", "名称", "国家", "纬度", "经度", "泊位数", "起重机数"],
        },
        {
            "id": "ships",
            "name": "AEU 航线船舶",
            "description": "COSCO 系列集装箱船",
            "rows": 9,
            "source": "builtin",
            "fields": ["ID", "名称", "容量(TEU)", "设计航速(kn)", "载重吨", "建造年份"],
        },
        {
            "id": "routes",
            "name": "航线距离矩阵",
            "description": "港口间航行距离",
            "rows": 81,
            "source": "builtin",
            "fields": ["起始港", "目的港", "距离(nm)", "航行时间(h)"],
        },
    ]


def load_builtin_dataset(dataset_id: str) -> dict:
    """加载预置数据集内容"""
    if dataset_id == "ports":
        path = os.path.join(DATA_DIR, "ports.json")
        with open(path, encoding="utf-8") as f:
            ports = json.load(f)
        return {
            "id": "ports",
            "name": "全球港口坐标",
            "columns": ["unique_id", "name", "country", "lat", "lon", "berth_count", "crane_count"],
            "rows": [
                [p.get(k) for k in ["unique_id", "name", "country", "lat", "lon", "berth_count", "crane_count"]]
                for p in ports
            ],
        }

    if dataset_id == "ships":
        path = os.path.join(DATA_DIR, "ships.json")
        with open(path, encoding="utf-8") as f:
            ships = json.load(f)
        return {
            "id": "ships",
            "name": "AEU 航线船舶",
            "columns": ["unique_id", "name", "capacity_teu", "speed", "dwt", "year_built"],
            "rows": [
                [s.get(k) for k in ["unique_id", "name", "capacity_teu", "speed", "dwt", "year_built"]]
                for s in ships
            ],
        }

    if dataset_id == "routes":
        ports_path = os.path.join(DATA_DIR, "ports.json")
        with open(ports_path, encoding="utf-8") as f:
            ports_list = json.load(f)
        rows = []
        for p1 in ports_list:
            for p2 in ports_list:
                if p1["unique_id"] != p2["unique_id"]:
                    rows.append([p1["unique_id"], p2["unique_id"], 0, 0])
        return {
            "id": "routes",
            "name": "航线距离矩阵",
            "columns": ["from_port", "to_port", "distance_nm", "sailing_hours"],
            "rows": rows,
        }

    return {"id": dataset_id, "name": "未知数据集", "columns": [], "rows": []}


# ── 数据导入仿真 ────────────────────────────────────────────

def import_dataset_to_simulation(
    dataset_id: str,
    model: Any,
) -> dict:
    """将预置数据集导入仿真模型

    Args:
        dataset_id: 数据集 ID
        model: SimulationModel 实例

    Returns:
        导入结果报告
    """
    if dataset_id == "ports":
        # 重新加载港口数据
        path = os.path.join(DATA_DIR, "ports.json")
        with open(path, encoding="utf-8") as f:
            ports_data = json.load(f)
        model.ports.clear()
        from app.models.ship import Port
        for p in ports_data:
            port = Port(**p)
            model.ports[port.unique_id] = port
        return {"success": True, "message": f"已导入 {len(ports_data)} 个港口", "count": len(ports_data)}

    if dataset_id == "ships":
        path = os.path.join(DATA_DIR, "ships.json")
        with open(path, encoding="utf-8") as f:
            ships_data = json.load(f)
        model.ships.clear()
        from app.models.ship import Ship
        for s in ships_data:
            ship = Ship(**s)
            model.ships[ship.unique_id] = ship
        return {"success": True, "message": f"已导入 {len(ships_data)} 艘船舶", "count": len(ships_data)}

    return {"success": False, "message": f"未知数据集: {dataset_id}"}


# ── CSV 导入 ────────────────────────────────────────────────

def parse_csv(content: str) -> dict:
    """解析 CSV 文本内容"""
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    if not rows:
        return {"columns": [], "rows": [], "total": 0}
    return {"columns": rows[0], "rows": rows[1:], "total": len(rows) - 1}
