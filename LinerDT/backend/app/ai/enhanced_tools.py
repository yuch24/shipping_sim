"""
增强工具集 — 仿真分析工具函数。

提供深度分析能力：瓶颈检测、延迟传播预测、船舶诊断、船舶对比、优化建议。
这些工具通过 LLM function calling 暴露给前端对话。
"""

import json
import copy
from typing import Optional, List, Dict, Any
from app.scheduler.scheduler import ShipAgent


def analyze_bottleneck(model) -> str:
    """分析当前仿真的系统瓶颈。"""
    ships = model.get_all_ships()
    ports = model.get_all_ports()

    bottlenecks = []

    # 1. 港口瓶颈：队列最长的港口
    port_congestions = []
    for pid, p in ports.items():
        q = p.get("queue_length", 0)
        berths = p.get("berth_count", 1)
        available = p.get("available_berths", 0)
        name = p.get("name", pid)
        congestion_index = q / max(berths, 1)
        if q > 0 or available == 0:
            port_congestions.append({
                "port": f"{name}({pid})",
                "queue": q,
                "berths": berths,
                "available": available,
                "congestion_index": round(congestion_index, 2),
            })

    port_congestions.sort(key=lambda x: x["congestion_index"], reverse=True)
    for pc in port_congestions[:3]:
        level = "严重" if pc["congestion_index"] >= 1.0 else "中度" if pc["congestion_index"] >= 0.5 else "轻微"
        bottlenecks.append({
            "type": "port_congestion",
            "severity": level,
            "detail": f"{pc['port']}: 队列{pc['queue']}艘，{pc['available']}/{pc['berths']}泊位可用",
            "data": pc,
        })

    # 2. 船舶瓶颈：综合表现最差的船舶
    ship_issues = []
    for sid, s in ships.items():
        delay = s.get("cumulative_delay", 0)
        cii_ratio = s.get("cii_ratio", 1.0)
        cii_rating = s.get("cii_rating", "B")
        name = s.get("name", sid)
        speed = s.get("current_speed", 0)
        economic = s.get("economic_speed", 0)

        severity_score = 0
        issues = []
        if delay > 48:
            severity_score += 3
            issues.append(f"严重延误{delay:.0f}h")
        elif delay > 24:
            severity_score += 1
            issues.append(f"中度延误{delay:.0f}h")

        if cii_rating == "E":
            severity_score += 3
            issues.append(f"CII-E级({cii_ratio:.2f})")
        elif cii_rating == "D":
            severity_score += 2
            issues.append(f"CII-D级({cii_ratio:.2f})")

        if speed > economic and cii_ratio >= 1.15:
            severity_score += 1
            issues.append(f"超经济航速({speed}>{economic}节)")

        if severity_score > 0:
            ship_issues.append({
                "ship": f"{name}({sid})",
                "severity_score": severity_score,
                "issues": issues,
                "delay": delay,
                "cii_ratio": cii_ratio,
                "cii_rating": cii_rating,
            })

    ship_issues.sort(key=lambda x: x["severity_score"], reverse=True)
    for si in ship_issues[:5]:
        sev = "严重" if si["severity_score"] >= 4 else "中度" if si["severity_score"] >= 2 else "轻微"
        bottlenecks.append({
            "type": "ship_issue",
            "severity": sev,
            "detail": f"{si['ship']}: {', '.join(si['issues'])}",
            "data": si,
        })

    result = {
        "sim_time": model.current_time,
        "total_bottlenecks": len(bottlenecks),
        "bottlenecks": bottlenecks,
        "summary": _generate_bottleneck_summary(bottlenecks),
    }
    return json.dumps(result, indent=2, ensure_ascii=False)


def _generate_bottleneck_summary(bottlenecks: list) -> str:
    if not bottlenecks:
        return "当前系统运行正常，未发现明显瓶颈"

    port_issues = [b for b in bottlenecks if b["type"] == "port_congestion"]
    ship_issues = [b for b in bottlenecks if b["type"] == "ship_issue"]

    parts = []
    if port_issues:
        parts.append(f"{len(port_issues)}个港口出现拥堵")
    if ship_issues:
        parts.append(f"{len(ship_issues)}艘船舶需要关注")

    return "；".join(parts) if parts else "系统正常"


def predict_delay_cascade(model, start_port: str, max_depth: int = 3) -> str:
    """预测延误从某个港口开始会如何传播。"""

    ships = model.get_all_ships()
    cascade = []
    affected_ships = set()
    current_port = start_port
    depth = 0

    while depth < max_depth and current_port:
        depth += 1
        ships_thru_port = []

        for sid, agent in model._agents.items():
            if not isinstance(agent, ShipAgent):
                continue
            if sid in affected_ships:
                continue

            # 查船舶的航线
            route = model.get_route_for_ship(sid)
            if current_port in route:
                idx = route.index(current_port)
                if idx + 1 < len(route):
                    next_p = route[idx + 1]
                else:
                    continue

                delay = agent.cumulative_delay
                delay_history = [d for d in agent.delay_history if d.get("port") == current_port]
                port_delay = delay_history[-1].get("port_delay", 0) if delay_history else 0

                ships_thru_port.append({
                    "ship": f"{agent.name}({sid})",
                    "current_delay": delay,
                    "port_delay": port_delay,
                    "next_port": next_p,
                    "cii_rating": agent._cii_rating,
                    "speed": agent.current_speed,
                })

        if not ships_thru_port:
            break

        cascade.append({
            "depth": depth,
            "port": current_port,
            "affected_ships": ships_thru_port,
        })

        for stp in ships_thru_port:
            affected_ships.add(stp["ship"])

        if ships_thru_port:
            current_port = ships_thru_port[0]["next_port"]
        else:
            break

    result = {
        "start_port": start_port,
        "cascade": cascade,
        "total_affected": len(affected_ships),
        "prediction": _generate_cascade_prediction(cascade, start_port),
    }
    return json.dumps(result, indent=2, ensure_ascii=False)


def _generate_cascade_prediction(cascade: list, start_port: str) -> str:
    if not cascade:
        return f"从 {start_port} 未检测到显著的延误传播链"

    total_ships = sum(len(step.get("affected_ships", [])) for step in cascade)
    steps = []
    for step in cascade:
        port = step["port"]
        ships = [s["ship"] for s in step["affected_ships"]]
        steps.append(f"{port} → 影响 {', '.join(ships)}")

    return f"预计延误传播链涉及 {total_ships} 艘船：" + "；".join(steps)


def compare_ships(model, ship_ids: list) -> str:
    """对比多艘船舶的各项指标。"""
    comparison = []

    for sid in ship_ids:
        agent = model.get_agent(sid)
        if not agent:
            continue
        if not isinstance(agent, ShipAgent):
            continue

        carbon = agent.get_carbon_stats()
        comparison.append({
            "ship_id": sid,
            "name": agent.name,
            "state": str(agent.state),
            "current_speed": agent.current_speed,
            "economic_speed": agent.economic_speed,
            "cumulative_delay": agent.cumulative_delay,
            "cii_ratio": round(agent._get_cii_ratio(), 3),
            "cii_rating": agent._cii_rating,
            "co2_tons": round(carbon["total_co2_tons"], 1),
            "distance_nm": round(carbon["total_distance_nm"], 1),
            "fuel_type": agent._current_fuel_type,
            "efficiency": round(carbon["total_co2_tons"] / max(carbon["total_distance_nm"], 1), 4),
        })

    if not comparison:
        return json.dumps({"error": "未找到任何船舶"}, ensure_ascii=False)

    # 排序
    comparison.sort(key=lambda x: x["cii_ratio"], reverse=True)

    result = {
        "count": len(comparison),
        "ships": comparison,
        "summary": _generate_comparison_summary(comparison),
    }
    return json.dumps(result, indent=2, ensure_ascii=False)


def _generate_comparison_summary(comparison: list) -> str:
    if not comparison:
        return "无数据"

    most_delayed = max(comparison, key=lambda x: x["cumulative_delay"])
    least_delayed = min(comparison, key=lambda x: x["cumulative_delay"])
    fastest = max(comparison, key=lambda x: x["current_speed"])
    slowest = min(comparison, key=lambda x: x["current_speed"])

    return (
        f"最延误: {most_delayed['name']}({most_delayed['cumulative_delay']:.0f}h) | "
        f"最准时: {least_delayed['name']}({least_delayed['cumulative_delay']:.0f}h) | "
        f"最快: {fastest['name']}({fastest['current_speed']}节) | "
        f"最慢: {slowest['name']}({slowest['current_speed']}节)"
    )


def diagnose_ship(model, ship_id: str) -> str:
    """对单艘船进行深度诊断，分析所有问题及建议。"""
    agent = model.get_agent(ship_id)
    if not agent:
        return json.dumps({"error": f"未找到船舶 {ship_id}"}, ensure_ascii=False)

    from app.scheduler.scheduler import ShipAgent
    if not isinstance(agent, ShipAgent):
        return json.dumps({"error": f"{ship_id} 不是船舶"}, ensure_ascii=False)

    carbon = agent.get_carbon_stats()
    cii_ratio = agent._get_cii_ratio()
    route = model.get_route_for_ship(ship_id)

    # 诊断项目
    diagnosis_items = []

    # 1. 运营效率（延误 + CII 综合评估）
    cii_rating = agent._cii_rating
    cii_finding = f"CII比率 {cii_ratio:.2f}，评级 {cii_rating}"
    if cii_rating == "E":
        cii_finding += "，超标"
        cii_suggestion = f"建议降至经济航速 {agent.economic_speed} 节"
    elif cii_rating == "D":
        cii_finding += "，偏高"
        cii_suggestion = f"建议关注航速，可降至 {agent.economic_speed} 节"
    elif cii_ratio >= 1.15:
        cii_finding += "，偏高水平"
        cii_suggestion = "航速偏高时考虑适时降速"
    else:
        cii_finding += "，正常"
        cii_suggestion = "保持当前策略"

    delay = agent.cumulative_delay
    delay_finding = f"累计延误 {delay:.0f}h" if delay > 0 else "无延误"
    delay_suggestion = ""
    if delay > 48:
        delay_severity = "critical"
        delay_suggestion = "考虑提速赶班或调整挂港顺序"
    elif delay > 24:
        delay_severity = "warning"
        delay_suggestion = "适当提速，或接受当前延误"
    else:
        delay_severity = "ok" if delay == 0 else "info"

    # 综合运营效率诊断
    cii_delay_score = (cii_rating in ("D", "E")) + (delay > 24)
    ops_severity = "critical" if cii_delay_score >= 2 else "warning" if cii_delay_score >= 1 else "ok"
    ops_suggestions = [s for s in [delay_suggestion, cii_suggestion] if s]
    diagnosis_items.append({
        "category": "运营效率",
        "severity": ops_severity,
        "finding": f"{delay_finding}；{cii_finding}",
        "suggestion": "；".join(ops_suggestions) if ops_suggestions else "运营状态良好",
    })

    # 2. 延误检查（详细）
    delay = agent.cumulative_delay
    if delay > 48:
        diagnosis_items.append({
            "category": "延误",
            "severity": "critical",
            "finding": f"累计延误 {delay:.0f} 小时，严重影响班期",
            "suggestion": "考虑临时提速至设计航速赶班，或调整后续挂港顺序",
        })
    elif delay > 24:
        diagnosis_items.append({
            "category": "延误",
            "severity": "warning",
            "finding": f"累计延误 {delay:.0f} 小时",
            "suggestion": "适当提速，或接受当前延误并通知下游港口",
        })
    elif delay > 0:
        diagnosis_items.append({
            "category": "延误",
            "severity": "info",
            "finding": f"累计延误 {delay:.1f} 小时",
            "suggestion": "轻微延误，在可控范围内",
        })
    else:
        diagnosis_items.append({
            "category": "延误",
            "severity": "ok",
            "finding": "无延误，准班运行",
            "suggestion": "",
        })

    # 3. 航速合理性
    if agent.current_speed > agent.economic_speed + 2 and cii_ratio >= 1.15:
        diagnosis_items.append({
            "category": "航速策略",
            "severity": "warning",
            "finding": f"当前航速 {agent.current_speed} 节，远超经济航速 {agent.economic_speed} 节，且CII偏高",
            "suggestion": f"建议降至 {agent.economic_speed} 节，牺牲少许时间换取碳合规",
        })

    # 4. 燃油类型
    if agent._current_fuel_type == "MGO":
        diagnosis_items.append({
            "category": "燃油",
            "severity": "info",
            "finding": "当前位于 ECA 区域，使用 MGO（CO2因子3.206）",
            "suggestion": "离开 ECA 后将自动切换为 VLSFO（CO2因子3.114）",
        })

    # 5. 航线分析
    if route:
        pos = route.index(agent.current_port) if agent.current_port in route else -1
        remaining = route[pos+1:] if pos >= 0 else route
        diagnosis_items.append({
            "category": "航线",
            "severity": "info",
            "finding": f"当前航线: {' → '.join(route)}",
            "suggestion": f"剩余挂靠: {' → '.join(remaining[:4])}{'...' if len(remaining) > 4 else ''}",
        })

    result = {
        "ship_id": ship_id,
        "ship_name": agent.name,
        "current_time": model.current_time,
        "diagnosis": diagnosis_items,
        "stats": {
            "speed": agent.current_speed,
            "economic_speed": agent.economic_speed,
            "design_speed": agent.design_speed,
            "delay": agent.cumulative_delay,
            "cii_ratio": round(cii_ratio, 3),
            "cii_rating": cii_rating,
            "co2_tons": round(carbon["total_co2_tons"], 1),
            "distance_nm": round(carbon["total_distance_nm"], 1),
            "fuel_type": agent._current_fuel_type,
            "state": str(agent.state),
        },
        "critical_count": sum(1 for d in diagnosis_items if d["severity"] == "critical"),
        "warning_count": sum(1 for d in diagnosis_items if d["severity"] == "warning"),
    }

    return json.dumps(result, indent=2, ensure_ascii=False)


def suggest_optimization(model, target: str = "all") -> str:
    """基于当前仿真状态，自动生成优化建议。"""
    ships = model.get_all_ships()
    suggestions = []

    for sid, agent in model._agents.items():
        if not isinstance(agent, ShipAgent):
            continue

        cii_ratio = agent._get_cii_ratio()
        cii_rating = agent._cii_rating
        delay = agent.cumulative_delay
        speed = agent.current_speed
        economic = agent.economic_speed

        if target != "all" and sid != target:
            continue

        # 航速策略优化（合并CII与延误考虑）
        if cii_rating in ("D", "E"):
            new_speed = max(economic - 1, 12)
            reduction = (1 - new_speed / max(speed, 1)) * 100
            suggestions.append({
                "ship": f"{agent.name}({sid})",
                "priority": "high" if cii_rating == "E" else "medium",
                "category": "航速策略",
                "action": f"降速至 {new_speed} 节",
                "expected_impact": f"碳排放预计减少约 {reduction:.0f}%，CII改善",
                "tradeoff": f"航程时间增加约 {(speed/new_speed - 1)*100:.0f}%",
                "params": {"ship_id": sid, "params": {"current_speed": new_speed}},
            })

        # 延误追赶建议
        if delay > 48:
            new_speed = min(speed + 2, agent.design_speed)
            suggestions.append({
                "ship": f"{agent.name}({sid})",
                "priority": "high",
                "category": "延误恢复",
                "action": f"提速至 {new_speed} 节",
                "expected_impact": f"每24h挽回约 {((new_speed/speed)-1)*24:.1f}h",
                "tradeoff": f"CII可能上升 5-10%",
                "params": {"ship_id": sid, "params": {"current_speed": new_speed}},
            })
        elif delay > 24 and cii_ratio < 1.35:
            new_speed = min(speed + 2, agent.design_speed)
            suggestions.append({
                "ship": f"{agent.name}({sid})",
                "priority": "medium",
                "category": "延误恢复",
                "action": f"提速至 {new_speed} 节",
                "expected_impact": f"每24h挽回约 {((new_speed/speed)-1)*24:.1f}h",
                "tradeoff": f"CII可能上升 5-10%",
                "params": {"ship_id": sid, "params": {"current_speed": new_speed}},
            })

    suggestions.sort(key=lambda s: 0 if s["priority"] == "high" else 1)

    result = {
        "total_suggestions": len(suggestions),
        "suggestions": suggestions,
    }
    return json.dumps(result, indent=2, ensure_ascii=False)
