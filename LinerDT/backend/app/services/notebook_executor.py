"""Notebook Execution — Python 脚本安全执行沙箱

在隔离环境中执行用户提交的 Python 脚本。
支持两种模式：
1. Pyodide 模式：浏览器端执行（前端）
2. 后端沙箱模式：subprocess 隔离执行

当前实现后端沙箱模式，提供仿真上下文 API。
"""

import ast
import io
import sys
import json
import types
import textwrap
import contextlib
from typing import Any

# ── AST 安全检查：禁止危险操作 ──────────────────────────────

FORBIDDEN_MODULES = {"os", "subprocess", "sys", "shutil", "ctypes", "socket", "requests", "http", "urllib"}
FORBIDDEN_BUILTINS = {"__import__", "open", "exec", "eval", "compile", "globals", "locals", "getattr", "setattr", "delattr"}

def _validate_script_safety(script: str) -> str | None:
    """AST-based安全校验，返回错误信息或None（安全）"""
    try:
        tree = ast.parse(script)
    except SyntaxError as e:
        return f"语法错误: {e.msg} (第 {e.lineno} 行)"

    for node in ast.walk(tree):
        # 禁止导入危险模块
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = node.names[0].name.split(".")[0]
            if module in FORBIDDEN_MODULES:
                return f"安全策略禁止导入模块: {module}"

        # 禁止调用危险内置函数
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_BUILTINS:
                return f"安全策略禁止使用: {node.func.id}()"

    return None

# ── 可用仿真上下文方法 ─────────────────────────────────────

def _build_sim_context(model: Any) -> dict:
    """构建可在脚本中使用的仿真上下文"""
    if model is None:
        return {"error": "仿真模型未初始化"}

    return {
        "get_time": lambda: getattr(model, "current_time", 0),
        "get_ships": lambda: [
            {
                "unique_id": s.unique_id,
                "name": s.name,
                "state": getattr(s, "state", "UNKNOWN"),
                "current_speed": getattr(s, "current_speed", 0),
                "lat": getattr(s, "lat", None),
                "lon": getattr(s, "lon", None),
                "current_port": getattr(s, "current_port", None),
                "next_port": getattr(s, "next_port", None),
                "co2_emissions": getattr(s, "co2_emissions", 0),
                "delay": getattr(s, "delay", 0),
                "cii_rating": getattr(s, "cii_rating", None),
                "capacity_teu": getattr(s, "capacity_teu", 0),
            }
            for s in getattr(model, "ships", {}).values()
        ],
        "get_ports": lambda: [
            {
                "unique_id": p.unique_id,
                "name": p.name,
                "queue_length": getattr(p, "queue_length", 0),
                "available_berths": getattr(p, "available_berths", 0),
                "berth_count": getattr(p, "berth_count", 4),
            }
            for p in getattr(model, "ports", {}).values()
        ],
        "get_kpi": lambda: {
            "total_ships": len(getattr(model, "ships", {})),
            "sailing_ships": sum(
                1 for s in getattr(model, "ships", {}).values()
                if getattr(s, "state", "") == "SAILING"
            ),
            "total_co2": sum(
                getattr(s, "co2_emissions", 0) for s in getattr(model, "ships", {}).values()
            ),
        },
    }


# ── 沙箱执行 ────────────────────────────────────────────────

def execute_script(script: str, model: Any = None) -> dict:
    """安全执行 Python 脚本

    返回:
        {
            "status": "success" | "error",
            "output": str,       # print 输出
            "result": Any,       # 最后一个表达式的值
            "error": str | None, # 错误信息
            "plots": [],         # 图表 base64 列表（未来支持）
        }
    """
    output_capture = io.StringIO()
    error_buf = io.StringIO()

    # 构建仿真上下文
    sim_context = _build_sim_context(model)

    # 注入可用库
    allowed_imports = {
        "math": __import__("math"),
        "json": __import__("json"),
        "random": __import__("random"),
        "collections": __import__("collections"),
        "datetime": __import__("datetime"),
        "statistics": __import__("statistics"),
    }

    try:
        import numpy as _np
        allowed_imports["numpy"] = _np
    except ImportError:
        pass

    # 构建执行命名空间
    namespace = {
        **allowed_imports,
        "sim_context": types.SimpleNamespace(**sim_context),
        "print": lambda *args, **kwargs: print(*args, file=output_capture, **kwargs),
    }

    # AST 安全检查
    safety_error = _validate_script_safety(script)
    if safety_error:
        return {
            "status": "error",
            "output": "",
            "error": safety_error,
            "result": None,
        }

    try:
        # 先编译检查语法
        compiled = compile(textwrap.dedent(script), "<script>", "exec")

        # 执行
        exec(compiled, namespace)
        output = output_capture.getvalue()

        return {
            "status": "success",
            "output": output,
            "result": None,
            "error": None,
        }
    except SyntaxError as e:
        return {
            "status": "error",
            "output": output_capture.getvalue(),
            "error": f"语法错误: {e.msg} (第 {e.lineno} 行)",
            "result": None,
        }
    except Exception as e:
        return {
            "status": "error",
            "output": output_capture.getvalue(),
            "error": f"运行时错误: {type(e).__name__}: {e}",
            "result": None,
        }


# ── 脚本模板 ────────────────────────────────────────────────

def get_templates() -> list[dict]:
    """返回预置脚本模板"""
    return [
        {
            "id": "basic_analysis",
            "name": "基础分析",
            "description": "获取仿真状态并做基本统计分析",
            "code": textwrap.dedent("""\
                # LinerDT 基础分析脚本
                # 使用 sim_context 对象访问仿真状态

                # 获取当前仿真时间
                current_time = sim_context.get_time()
                print(f"当前仿真时间: Day {current_time // 24 + 1}, Hour {current_time % 24:.0f}")

                # 获取所有船舶
                ships = sim_context.get_ships()
                print(f"船舶总数: {len(ships)}")

                # 状态分布
                states = {}
                for s in ships:
                    st = s['state']
                    states[st] = states.get(st, 0) + 1
                print(f"\\n状态分布:")
                for st, count in sorted(states.items()):
                    bar = '█' * count
                    print(f"  {st:12s}: {bar} {count}")

                # 平均航速
                speeds = [s['current_speed'] for s in ships if s['current_speed'] > 0]
                if speeds:
                    avg = sum(speeds) / len(speeds)
                    print(f"\\n平均航速: {avg:.2f} kn")
                    print(f"最大航速: {max(speeds):.2f} kn")
                    print(f"最小航速: {min(speeds):.2f} kn")

                # 延误分析
                delays = [s.get('delay', 0) for s in ships]
                if delays:
                    print(f"\\n延误统计:")
                    print(f"  平均延误: {sum(delays)/len(delays):.1f} h")
                    print(f"  最大延误: {max(delays):.1f} h")
                    delayed = sum(1 for d in delays if d > 4)
                    print(f"  延误>4h船舶: {delayed} 艘")

                print(f"\\n=== 分析完成 ===")
            """),
        },
        {
            "id": "kpi_report",
            "name": "KPI 报告",
            "description": "生成当前仿真状态的 KPI 摘要",
            "code": textwrap.dedent("""\
                # LinerDT KPI 报告生成
                import statistics

                ships = sim_context.get_ships()
                ports = sim_context.get_ports()

                # 准班率
                delays = [s.get('delay', 0) for s in ships]
                on_time = sum(1 for d in delays if d <= 4)
                on_time_rate = (on_time / len(delays) * 100) if delays else 0

                # 碳排放
                total_co2 = sim_context.get_kpi()['total_co2']

                # 港口拥堵
                congested = [p for p in ports if p['queue_length'] > 2]

                print("=" * 50)
                print("  LinerDT 仿真 KPI 报告")
                print("=" * 50)
                print(f"\\n📊 准班率: {on_time_rate:.1f}%")
                print(f"   (准时 {on_time}/{len(delays)} 艘)")
                print(f"\\n🌡️  碳排放总量: {total_co2:.1f} t")
                print(f"\\n🚢 港口状态:")
                for p in ports:
                    flag = "🔴" if p['queue_length'] > 2 else "🟢"
                    print(f"  {flag} {p['name']:12s}: 队列 {p['queue_length']}, "
                          f"泊位 {p['available_berths']}/{p['berth_count']}")

                print(f"\\n{'=' * 50}")
            """),
        },
        {
            "id": "monte_carlo",
            "name": "蒙特卡洛模拟",
            "description": "用 Python 实现简单的蒙特卡洛模拟",
            "code": textwrap.dedent("""\
                # 蒙特卡洛模拟示例
                # 在不确定性下分析延误分布
                import random
                import statistics

                random.seed(42)

                # 从仿真获取基础数据
                ships = sim_context.get_ships()
                base_speeds = [s['current_speed'] for s in ships if s['current_speed'] > 0]

                if not base_speeds:
                    print("没有正在航行的船舶数据")
                    exit()

                # 蒙特卡洛参数
                n_trials = 1000
                speed_uncertainty = 0.15  # ±15%
                delay_uncertainty = 2.0   # ±2h

                results = []
                for _ in range(n_trials):
                    # 对每艘船引入随机扰动
                    perturbed = [s * random.uniform(1 - speed_uncertainty, 1 + speed_uncertainty)
                                for s in base_speeds]
                    avg = sum(perturbed) / len(perturbed)
                    delay = random.gauss(0, delay_uncertainty)
                    results.append(avg + delay)

                print(f"蒙特卡洛分析 ({n_trials} 次)")
                print(f"{'=' * 40}")
                print(f"平均航速: {statistics.mean(results):.2f} kn")
                print(f"标准差:   {statistics.stdev(results):.2f} kn")
                print(f"最小值:   {min(results):.2f} kn")
                print(f"最大值:   {max(results):.2f} kn")

                # 百分位数
                sorted_r = sorted(results)
                print(f"\\n百分位分布:")
                for p in [5, 25, 50, 75, 95]:
                    idx = int(len(sorted_r) * p / 100)
                    print(f"  P{p:02d}: {sorted_r[idx]:.2f} kn")
            """),
        },
    ]
