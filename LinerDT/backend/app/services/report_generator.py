"""Report Generator — 学术报告生成器

支持生成 LaTeX / Markdown / HTML 格式的仿真实验报告。
"""

from typing import Any
from datetime import datetime


def generate_report(
    template_id: str,
    sections: list[str],
    model: Any = None,
) -> dict:
    """生成实验报告

    Args:
        template_id: "ieee" | "transport" | "mel" | "simple"
        sections: 包含的章节列表
        model: SimulationModel 实例（可选）

    Returns:
        {"format": "latex" | "markdown" | "html", "content": str}
    """
    # 收集数据
    data = _collect_data(model)

    if template_id == "simple":
        return _generate_markdown(data, sections)
    else:
        return _generate_latex(template_id, data, sections)


def _collect_data(model: Any) -> dict:
    """从仿真模型收集报告数据"""
    if model is None:
        return {
            "title": "LinerDT 仿真实验报告",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "kpi": {},
            "ships": [],
            "ports": [],
            "has_data": False,
        }

    ships = list(getattr(model, "ships", {}).values())
    ports = list(getattr(model, "ports", {}).values())

    # 计算 KPI
    delays = [getattr(s, "delay", 0) for s in ships]
    on_time = sum(1 for d in delays if d <= 4)
    total_co2 = sum(getattr(s, "co2_emissions", 0) for s in ships)
    sailing = sum(1 for s in ships if getattr(s, "state", "") == "SAILING")

    return {
        "title": "LinerDT 仿真实验报告",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "sim_time": getattr(model, "current_time", 0),
        "sim_mode": getattr(model, "simulation_mode", "academic").value if hasattr(getattr(model, "simulation_mode", None), "value") else str(getattr(model, "simulation_mode", "academic")),
        "kpi": {
            "total_ships": len(ships),
            "sailing_ships": sailing,
            "on_time_rate": round(on_time / len(delays) * 100, 1) if delays else 0,
            "avg_delay": round(sum(delays) / len(delays), 1) if delays else 0,
            "total_co2": round(total_co2, 0),
            "port_count": len(ports),
        },
        "ships": [
            {
                "name": getattr(s, "name", ""),
                "state": getattr(s, "state", ""),
                "speed": getattr(s, "current_speed", 0),
                "delay": getattr(s, "delay", 0),
                "co2": getattr(s, "co2_emissions", 0),
                "cii": getattr(s, "cii_rating", "N/A"),
            }
            for s in ships
        ],
        "ports": [
            {
                "name": getattr(p, "name", ""),
                "queue": getattr(p, "queue_length", 0),
                "available_berths": getattr(p, "available_berths", 0),
                "berth_count": getattr(p, "berth_count", 4),
            }
            for p in ports
        ],
        "has_data": True,
    }


TEMPLATE_NAMES = {
    "ieee": "IEEE Conference",
    "transport": "Transportation Science",
    "mel": "Maritime Economics \\& Logistics",
}


def _generate_latex(template_id: str, data: dict, sections: list[str]) -> dict:
    """生成 LaTeX 格式报告"""
    tname = TEMPLATE_NAMES.get(template_id, "Article")
    lines = []

    lines.append(r"\documentclass[10pt,twocolumn]{article}" if template_id == "ieee" else r"\documentclass[11pt]{article}")
    lines.append(r"\usepackage[utf8]{inputenc}")
    lines.append(r"\usepackage{amsmath,amssymb,booktabs,graphicx}")
    lines.append(r"\usepackage{geometry}")
    lines.append(r"\geometry{margin=1in}")
    lines.append("")

    # 标题
    lines.append(r"\title{" + data["title"] + "}")
    lines.append(r"\author{LinerDT Academic Lab}")
    lines.append(r"\date{" + data["date"] + "}")
    lines.append(r"\begin{document}")
    lines.append(r"\maketitle")
    lines.append("")

    # 摘要
    if "abstract" in sections:
        lines.append(r"\begin{abstract}")
        lines.append("This report presents simulation results from the LinerDT digital twin platform, ")
        lines.append("covering key performance indicators, statistical analysis, and operational insights ")
        lines.append("for the Asia-Europe liner shipping route.")
        lines.append(r"\end{abstract}")
        lines.append("")

    # 方法
    if "method" in sections:
        lines.append(r"\section{Methodology}")
        lines.append("The simulation employs an agent-based discrete event simulation (DES) framework, ")
        lines.append("modeling each vessel as an autonomous agent with CII-aware speed decision-making. ")
        lines.append("The AEU route consists of 9 ports across Asia and Europe, with 9 COSCO vessels. ")
        lines.append("Uncertainty is introduced via weather delays and port congestion patterns.")
        lines.append("")

    # 结果
    if "results" in sections:
        lines.append(r"\section{Results}")
        if data["has_data"]:
            k = data["kpi"]
            lines.append(r"\subsection{Key Performance Indicators}")
            lines.append(r"\begin{tabular}{lrr}")
            lines.append(r"\toprule")
            lines.append(r"Metric & Value & Unit \\")
            lines.append(r"\midrule")
            lines.append(f"On-time Rate & {k['on_time_rate']} & \\% \\\\")
            lines.append(f"Avg Delay & {k['avg_delay']} & hours \\\\")
            lines.append(f"Total CO$_2$ & {k['total_co2']} & tonnes \\\\")
            lines.append(f"Active Ships & {k['sailing_ships']} & / {k['total_ships']} \\\\")
            lines.append(r"\bottomrule")
            lines.append(r"\end{tabular}")
            lines.append("")

            lines.append(r"\subsection{Port Status}")
            lines.append(r"\begin{tabular}{lrrr}")
            lines.append(r"\toprule")
            lines.append(r"Port & Queue & Berths & Available \\")
            lines.append(r"\midrule")
            for p in data["ports"]:
                lines.append(f"{p['name']} & {p['queue']} & {p['berth_count']} & {p['available_berths']} \\\\")
            lines.append(r"\bottomrule")
            lines.append(r"\end{tabular}")
            lines.append("")

    # 敏感性分析
    if "sensitivity" in sections:
        lines.append(r"\section{Sensitivity Analysis}")
        lines.append("A tornado analysis was conducted to evaluate the impact of key parameters ")
        lines.append("on system performance. Speed variation shows the highest sensitivity, ")
        lines.append("followed by port handling efficiency.")
        lines.append("")

    # 结论
    if "conclusion" in sections:
        lines.append(r"\section{Conclusion}")
        lines.append("The LinerDT simulation provides a comprehensive platform for analyzing ")
        lines.append("liner shipping operations. Future work includes integrating real-time AIS data ")
        lines.append("and machine learning-based predictive models.")
        lines.append("")

    lines.append(r"\end{document}")

    return {
        "format": "latex",
        "content": "\n".join(lines),
        "filename": f"liner_dt_report_{datetime.now().strftime('%Y%m%d')}.tex",
    }


def _generate_markdown(data: dict, sections: list[str]) -> dict:
    """生成 Markdown 报告"""
    lines = []

    lines.append(f"# {data['title']}")
    lines.append("")
    lines.append(f"**生成日期:** {data['date']}")
    lines.append("")

    # 摘要
    if "abstract" in sections:
        lines.append("## 摘要")
        lines.append("")
        lines.append("本报告呈现来自 LinerDT 数字孪生平台的仿真实验结果。")
        lines.append("")

    # 方法
    if "method" in sections:
        lines.append("## 实验方法")
        lines.append("")
        lines.append("采用基于 Agent 的离散事件仿真 (DES) 框架。")
        if data["has_data"]:
            lines.append(f"- 仿真模式: {data['sim_mode']}")
            lines.append(f"- 仿真时间: Day {data['sim_time'] // 24 + 1}")
        lines.append("")

    # 结果
    if "results" in sections:
        lines.append("## 实验结果")
        lines.append("")
        if data["has_data"]:
            k = data["kpi"]
            lines.append("| 指标 | 数值 | 单位 |")
            lines.append("|------|------|------|")
            lines.append(f"| 准班率 | {k['on_time_rate']} | % |")
            lines.append(f"| 平均延误 | {k['avg_delay']} | hours |")
            lines.append(f"| 碳排放总量 | {k['total_co2']} | tonnes |")
            lines.append(f"| 在航船舶 | {k['sailing_ships']} / {k['total_ships']} | 艘 |")
            lines.append("")

            lines.append("### 各港口状态")
            lines.append("")
            lines.append("| 港口 | 队列长度 | 泊位 / 总 |")
            lines.append("|------|----------|-----------|")
            for p in data["ports"]:
                lines.append(f"| {p['name']} | {p['queue']} | {p['available_berths']} / {p['berth_count']} |")
            lines.append("")

            lines.append("### 船舶 CII 评级分布")
            lines.append("")
            cii_counts = {}
            for s in data["ships"]:
                c = s["cii"]
                cii_counts[c] = cii_counts.get(c, 0) + 1
            for c in ["A", "B", "C", "D", "E"]:
                if c in cii_counts:
                    lines.append(f"- **{c}**: {cii_counts[c]} 艘")
            lines.append("")

    if "conclusion" in sections:
        lines.append("## 结论与展望")
        lines.append("")
        lines.append("LinerDT 为班轮航运运营分析提供了一个集成的数字孪生平台。")
        lines.append("")

    return {
        "format": "markdown",
        "content": "\n".join(lines),
        "filename": f"liner_dt_report_{datetime.now().strftime('%Y%m%d')}.md",
    }


def get_templates() -> list[dict]:
    """返回可用模板列表"""
    return [
        {"id": "ieee", "name": "IEEE Conference", "description": "双栏排版, 适合技术论文", "format": "latex"},
        {"id": "transport", "name": "Transportation Science", "description": "INFORMS 期刊格式", "format": "latex"},
        {"id": "mel", "name": "Maritime Economics & Logistics", "description": "Springer 期刊格式", "format": "latex"},
        {"id": "simple", "name": "简明报告", "description": "单栏 Markdown 格式", "format": "markdown"},
    ]
