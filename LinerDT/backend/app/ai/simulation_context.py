"""
仿真上下文构建器 — 让 LLM 拥有仿真的"第一人称视角"。

每次 LLM 调用前，自动构建一个结构化的仿真状态摘要，注入到 system prompt 中。
LLM 无需频繁调用 tools 查询基础状态，可以直接基于上下文进行推理。
"""

from typing import Optional, List, Dict, Any
import json


class SimulationContext:
    """仿真上下文 — 包含 LLM 需要的所有关键状态信息。"""

    def __init__(self, model):
        self.model = model

    def build(self, user_message: str = "") -> str:
        """构建完整的上下文文本，注入到 system prompt。"""
        parts = []

        # 1. 仿真时间
        parts.append(self._time_context())

        # 2. 船队概览（含各船状态与CII等关键指标）
        parts.append(self._fleet_overview())

        # 3. KPI 摘要
        parts.append(self._kpi_summary())

        # 4. 港口状态
        parts.append(self._port_summary())

        # 5. 异常与告警
        parts.append(self._anomalies())

        # 6. 最近事件
        parts.append(self._recent_events())

        return "\n\n".join(p for p in parts if p)

    def _time_context(self) -> str:
        t = self.model.current_time
        day = int(t // 24)
        hour = t % 24
        running = "运行中" if self.model.is_running else "已暂停"
        speed = self.model.speed
        return f"[仿真状态] 第 {day} 天 {hour:.0f} 小时 | {running} | 速度倍率: {speed}x"

    def _fleet_overview(self) -> str:
        ships = self.model.get_all_ships()
        if not ships:
            return "[船队] 无船舶数据"

        sailing = 0
        berthing = 0
        arriving = 0
        waiting = 0
        idle = 0

        for s in ships.values():
            st = str(s.get("state", "IDLE"))
            if st == "SAILING":
                sailing += 1
            elif st in ("BERTHING", "Berthing"):
                berthing += 1
            elif st in ("ARRIVING", "Arriving"):
                arriving += 1
            elif st in ("DEPARTING", "Departing"):
                berthing += 1
            else:
                idle += 1

        # 统计等待中的船（在港口队列中）
        ports = self.model.get_all_ports()
        waiting = sum(p.get("queue_length", 0) for p in ports.values())

        return (
            f"[船队概览] 共 {len(ships)} 艘船 | "
            f"航行中: {sailing} | 靠泊中: {berthing} | "
            f"到达中: {arriving} | 等待泊位: {waiting}"
        )

    def _kpi_summary(self) -> str:
        try:
            from app.services.kpi_calculator import get_kpi_calculator
            kpi = get_kpi_calculator()
            dashboard = kpi.get_dashboard()
        except Exception:
            return "[KPI] 数据暂不可用"

        if not dashboard:
            return "[KPI] 数据暂不可用"

        on_time = dashboard.get("on_time_rate", 0)
        avg_delay = dashboard.get("avg_delay", 0)
        co2 = dashboard.get("total_co2", 0)

        return (
            f"[KPI] 准班率: {on_time*100:.1f}% | "
            f"平均延误: {avg_delay:.1f}h | "
            f"累计碳排放: {co2:.0f} 吨"
        )

    def _port_summary(self) -> str:
        ports = self.model.get_all_ports()
        if not ports:
            return ""

        congested = []
        free = []

        for pid, p in ports.items():
            q = p.get("queue_length", 0)
            available = p.get("available_berths", 0)
            name = p.get("name", pid)
            if q > 0 or available == 0:
                congested.append(f"{name}({pid}) 队列{q} 可用泊位{available}")
            else:
                free.append(name)

        parts = []
        if congested:
            parts.append(f"[拥堵港口] {'; '.join(congested)}")
        parts.append(f"[畅通港口] {', '.join(free) if free else '无'}")

        return "\n".join(parts)

    def _anomalies(self) -> str:
        """检测异常情况：高延误、港口拥堵、CII超标等。"""
        issues = []

        # 检查船舶延误
        ships = self.model.get_all_ships()
        for sid, s in ships.items():
            delay = s.get("cumulative_delay", 0)
            name = s.get("name", sid)
            if delay > 48:
                issues.append(f"⚠️ {name}({sid}) 累计延误 {delay:.0f}h（严重）")
            elif delay > 24:
                issues.append(f"⚡ {name}({sid}) 累计延误 {delay:.0f}h（注意）")

            cii_ratio = s.get("cii_ratio", 1.0)
            cii_rating = s.get("cii_rating", "B")
            if cii_rating == "E":
                issues.append(f"{name}({sid}) CII={cii_ratio:.2f} (E级)")
            elif cii_rating == "D":
                issues.append(f"{name}({sid}) CII={cii_ratio:.2f} (D级)")

        # 检查港口拥堵
        ports = self.model.get_all_ports()
        for pid, p in ports.items():
            q = p.get("queue_length", 0)
            name = p.get("name", pid)
            if q >= 3:
                issues.append(f"🔴 {name}({pid}) 排队 {q} 艘（严重拥堵）")
            elif q >= 2:
                issues.append(f"🟡 {name}({pid}) 排队 {q} 艘（轻微拥堵）")

        if not issues:
            return "[异常检测] 未发现显著异常"

        return "[异常检测]\n" + "\n".join(issues)

    def _recent_events(self, max_events: int = 8) -> str:
        """收集所有船舶的最近决策日志事件。"""
        ships = self.model.get_all_ships()
        all_events = []

        for sid, agent in self.model._agents.items():
            from app.scheduler.scheduler import ShipAgent
            if not isinstance(agent, ShipAgent):
                continue
            for entry in agent.decision_log[-3:]:
                all_events.append({
                    "time": entry.get("sim_time", 0),
                    "ship": agent.name,
                    "event": entry.get("event", ""),
                    "reason": entry.get("reason", ""),
                })

        all_events.sort(key=lambda e: e["time"], reverse=True)
        recent = all_events[:max_events]

        if not recent:
            return ""

        lines = ["[最近事件]"]
        for e in recent:
            day = int(e["time"] // 24)
            hour = e["time"] % 24
            lines.append(f"  D{day}H{hour:.0f} | {e['ship']} | {e['reason'][:80]}")

        return "\n".join(lines)

    def build_detailed_ship_context(self, ship_id: str) -> str:
        """为特定船舶构建详细上下文。"""
        agent = self.model.get_agent(ship_id)
        if not agent:
            return f"未找到船舶 {ship_id}"

        from app.scheduler.scheduler import ShipAgent
        if not isinstance(agent, ShipAgent):
            return f"{ship_id} 不是船舶"

        route = self.model.get_route_for_ship(ship_id)
        route_str = " → ".join(route) if route else "无航线"

        decision_summary = ""
        if agent.decision_log:
            recent = agent.decision_log[-5:]
            decision_summary = "\n最近决策:\n" + "\n".join(
                f"  D{int(d['sim_time']//24)}H{d['sim_time']%24:.0f}: {d.get('reason', '')[:100]}"
                for d in recent
            )

        carbon = agent.get_carbon_stats()
        cii_ratio = agent._get_cii_ratio()
        cii_rating = agent._cii_rating

        return f"""[船舶详情] {agent.name} ({ship_id})
航速: 当前 {agent.current_speed}节 | 经济 {agent.economic_speed}节 | 设计 {agent.design_speed}节
位置: ({agent.lat:.2f}, {agent.lon:.2f})
状态: {agent.state} | 当前港: {agent.current_port or '无'} | 下一港: {agent.next_port or '无'}
航线: {route_str}
延误: 累计 {agent.cumulative_delay:.1f}h
CII: 比率 {cii_ratio:.2f} | 评级 {cii_rating}
碳排放: 总计 {carbon['total_co2_tons']:.1f}吨 | 里程 {carbon['total_distance_nm']:.0f}NM
燃油: {agent._current_fuel_type} | 排放率 {carbon['emission_rate_per_hour']:.1f} t/h
运力: {agent.capacity_teu} TEU | 装载率 {agent.load_factor*100:.0f}%
{decision_summary}"""

    def build_detailed_port_context(self, port_id: str) -> str:
        """为特定港口构建详细上下文。"""
        port = self.model.get_port(port_id)
        if not port:
            return f"未找到港口 {port_id}"

        from app.scheduler.scheduler import PortAgent
        if not isinstance(port, PortAgent):
            return f"{port_id} 不是港口"

        # 查找在此港口的船舶
        ships_at_port = []
        ships_en_route = []
        for sid, agent in self.model._agents.items():
            from app.scheduler.scheduler import ShipAgent
            if not isinstance(agent, ShipAgent):
                continue
            if agent.current_port == port_id:
                ships_at_port.append(f"{agent.name}({sid})")
            if agent.next_port == port_id:
                eta = ""
                if agent.schedule_time:
                    eta = f" ETA:D{int(agent.schedule_time//24)}H{agent.schedule_time%24:.0f}"
                ships_en_route.append(f"{agent.name}({sid}){eta}")

        arrival_stats = ""
        if port.arrival_history:
            delays = [a.get("delay", 0) for a in port.arrival_history[-10:]]
            avg_delay = sum(delays) / len(delays) if delays else 0
            arrival_stats = f"\n历史延误: 近 {len(delays)} 次平均 {avg_delay:.1f}h"

        return f"""[港口详情] {port.name} ({port_id})
坐标: ({port.lat:.2f}, {port.lon:.2f})
泊位: {port.berth_count} 个 | 可用: {port.available_berths} | 占用: {len(port.occupied_berths)}
排队: {port.queue_length} 艘 {port.waiting_queue}
靠泊船舶: {', '.join(ships_at_port) if ships_at_port else '无'}
在途船舶: {', '.join(ships_en_route) if ships_en_route else '无'}{arrival_stats}"""


def get_simulation_context(model) -> SimulationContext:
    """获取仿真上下文构建器。"""
    return SimulationContext(model)
