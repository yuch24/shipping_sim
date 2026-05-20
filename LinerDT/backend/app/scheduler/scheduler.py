from typing import Optional
from enum import Enum
import threading
from .event_queue import EventQueue, Event
from .events import EventType
from ..models.ship import ShipState
from .visualization_sync import get_visualization_sync
from app.services.navigation import (
    haversine,
    calculate_fuel_consumption,
    calculate_hourly_fuel_consumption,
)
from app.services.uncertainty import (
    get_uncertainty_engine,
    UncertaintyEngine,
    reset_uncertainty_engine,
)
from app.services.kpi_calculator import get_kpi_calculator
from app.services.eca import is_in_eca as eca_is_in_eca, FUEL_PROPERTIES, FuelType
from app.ai import get_ai_integration, DecisionContext
from ..schema.parameter_def import ParameterDef, ParamType, param_group
from ..core.tree import (
    ActiveObject,
    Agent as TreeAgent,
    Engine,
    Parameter,
    ParamType as TreeParamType,
    AgentPopulation,
)
from app.data.waypoints_loader import get_waypoints


class SimulationMode(str, Enum):
    ACADEMIC = "academic"
    REAL_TIME = "real_time"


class BaseAgent(TreeAgent):
    """所有仿真 Agent 的基类。继承自 ActiveObject 树节点。"""

    def __init__(self, unique_id: str = None, owner: ActiveObject = None, **kwargs):
        super().__init__(owner=owner)
        self.unique_id = unique_id or self._name

    @classmethod
    def get_parameter_defs(cls) -> list[ParameterDef]:
        """子类可覆盖此方法返回 ParameterDef 列表。"""
        return []

    @property
    def model(self) -> "SimulationModel":
        """向后兼容：model 属性返回引擎的根节点。"""
        engine = self.get_engine()
        if engine:
            model = engine.get_root_agent()
            if model is not None:
                return model
        raise RuntimeError(f"Agent {self.unique_id} 不在一棵有效的仿真树中")

    def handle_event(self, event: Event):
        pass


class BaseModel:
    def __init__(self):
        pass


class EventDrivenScheduler:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.event_queue = EventQueue()

    @property
    def model(self) -> "SimulationModel":
        """向后兼容：通过 engine 获取模型。"""
        root = self.engine.get_root_agent()
        if root is not None:
            return root
        raise RuntimeError("Engine 没有根节点")

    def schedule_event(self, event: Event) -> None:
        self.event_queue.push(event)

    def schedule_event_at(
        self,
        time: float,
        event_type: str,
        target_agent_id: str,
        payload: dict = None,
        source: str = "system",
    ) -> None:
        event = Event(
            time=time,
            event_type=event_type,
            target_agent_id=target_agent_id,
            payload=payload or {},
            source=source,
        )
        self.schedule_event(event)

    def peek_next_event(self) -> Optional[Event]:
        return self.event_queue.peek()

    def get_next_event_time(self) -> Optional[float]:
        event = self.peek_next_event()
        return event.time if event else None

    def step(self) -> bool:
        event = self.event_queue.pop()
        if event is None:
            return False

        self.engine.current_time = event.time

        self.model.update_all_ships()

        target_agent = self.model.get_agent(event.target_agent_id)
        if target_agent and hasattr(target_agent, "handle_event"):
            target_agent.handle_event(event)

        return True

    def run_until(self, end_time: float, max_steps: int = 10000) -> int:
        steps = 0
        while steps < max_steps:
            next_event = self.peek_next_event()
            if next_event is None or next_event.time > end_time:
                break
            self.step()
            steps += 1
        return steps


class ShipAgent(BaseAgent):
    def __init__(
        self,
        unique_id: str = None,
        owner: ActiveObject = None,
        model: "SimulationModel" = None,
        **kwargs,
    ):
        super().__init__(unique_id=unique_id, owner=owner)
        self._display_name = kwargs.get("name", unique_id or "ship")

        # 兼容旧接口：如果传入了 model，挂载到 model 树中
        if model is not None:
            model.embed(self)
        self.state = kwargs.get("state", ShipState.IDLE)
        self.current_speed = kwargs.get("current_speed", 0)
        self.design_speed = kwargs.get("design_speed", 22)
        self.economic_speed = kwargs.get("economic_speed", 18)
        self.capacity_teu = kwargs.get("capacity_teu", 20000)
        self.load_factor = kwargs.get("load_factor", 0.8)
        self.current_port = kwargs.get("current_port", None)
        self.next_port = kwargs.get("next_port", None)
        self.lat = kwargs.get("lat", None)
        self.lon = kwargs.get("lon", None)
        self.co2_emissions = 0.0
        self.base_daily_consumption = kwargs.get("base_daily_consumption", 200)
        self.decision_log = []
        self._route_index = kwargs.get("_route_index", 0)
        self.schedule_time = 0.0
        self.cumulative_delay = 0.0
        self.delay_history = []
        self.cii_reference = 0.115
        self._current_fuel_type = "VLSFO"
        self._sailing_segment_start_time = None
        self._sailing_segment_distance = 0.0
        self._total_distance_nm = 0.0
        self._total_co2_tons = 0.0
        self._cii_window_days = 30
        self._annual_distance_estimate = 150000.0
        self._emission_history = []
        self._distance_history = []
        self._cii_rating = "B"

        # ── 可配置行为参数（Phase 3 提取自硬编码） ──
        self._delay_threshold_hours = 24.0
        """延误超过此阈值触发赶班行为"""
        self._speed_cap_delta = 1.0
        """CII 危险时最大加速值（相对于经济航速）"""
        self._cii_danger_threshold = 1.35
        """CII 危险判定阈值（与 cii_reference 的比值）"""
        self._cumulative_delay_cap = 72.0
        """累计延误上限"""
        self._loading_time_hours = 24.0
        """标准装卸时间"""
        self._cii_rating_thresholds = {"A": 0.85, "B": 1.00, "C": 1.15, "D": 1.35}
        """CII 评级阈值比例"""
        self._decision_log_max = 100
        """决策日志最大条数"""
        self._low_speed_threshold = 0.5
        """低航速判定阈值（与设计航速的比值）"""
        self._low_speed_penalty = 1.3
        """低航速时的燃油效率惩罚系数"""

    @classmethod
    def get_parameter_defs(cls) -> list[ParameterDef]:
        """返回船舶 Agent 的所有可配置参数定义。"""
        return [
            param_group(
                "ship_basic",
                "基本参数",
                [
                    ParameterDef(
                        "name",
                        "名称",
                        ParamType.STRING,
                        default="",
                        description="船舶名称",
                    ),
                    ParameterDef(
                        "design_speed",
                        "设计航速",
                        ParamType.FLOAT,
                        default=22.0,
                        unit="kn",
                        min_val=10,
                        max_val=30,
                        step=0.5,
                    ),
                    ParameterDef(
                        "economic_speed",
                        "经济航速",
                        ParamType.FLOAT,
                        default=18.0,
                        unit="kn",
                        min_val=8,
                        max_val=28,
                        step=0.5,
                    ),
                    ParameterDef(
                        "capacity_teu",
                        "载箱量",
                        ParamType.INT,
                        default=20000,
                        unit="TEU",
                        min_val=4000,
                        max_val=24000,
                        step=100,
                    ),
                    ParameterDef(
                        "load_factor",
                        "负载率",
                        ParamType.FLOAT,
                        default=0.8,
                        min_val=0.3,
                        max_val=1.0,
                        step=0.05,
                    ),
                ],
            ),
            param_group(
                "ship_consumption",
                "能耗参数",
                [
                    ParameterDef(
                        "base_daily_consumption",
                        "日基础油耗",
                        ParamType.FLOAT,
                        default=200.0,
                        unit="t/day",
                        min_val=50,
                        max_val=500,
                        step=10,
                    ),
                    ParameterDef(
                        "cii_reference",
                        "CII 参考值",
                        ParamType.FLOAT,
                        default=0.115,
                        description="IMO CII 基准线",
                        min_val=0.01,
                        max_val=0.5,
                        step=0.001,
                    ),
                ],
            ),
            param_group(
                "ship_behavior",
                "行为参数",
                [
                    ParameterDef(
                        "_delay_threshold_hours",
                        "延误触发阈值",
                        ParamType.FLOAT,
                        default=24.0,
                        unit="h",
                        min_val=0,
                        max_val=168,
                        step=1,
                    ),
                    ParameterDef(
                        "_speed_cap_delta",
                        "最大加速增量",
                        ParamType.FLOAT,
                        default=1.0,
                        unit="kn",
                        min_val=0,
                        max_val=10,
                        step=0.5,
                    ),
                    ParameterDef(
                        "_cii_danger_threshold",
                        "CII 危险阈值",
                        ParamType.FLOAT,
                        default=1.35,
                        min_val=1.0,
                        max_val=2.0,
                        step=0.01,
                    ),
                    ParameterDef(
                        "_cumulative_delay_cap",
                        "累计延误上限",
                        ParamType.FLOAT,
                        default=72.0,
                        unit="h",
                        min_val=0,
                        max_val=336,
                        step=6,
                    ),
                    ParameterDef(
                        "_loading_time_hours",
                        "标准装卸时间",
                        ParamType.FLOAT,
                        default=24.0,
                        unit="h",
                        min_val=1,
                        max_val=120,
                        step=1,
                    ),
                    ParameterDef(
                        "_cii_rating_thresholds",
                        "CII 评级阈值",
                        ParamType.STRING,
                        default={"A": 0.85, "B": 1.00, "C": 1.15, "D": 1.35},
                        description="JSON 对象格式",
                    ),
                    ParameterDef(
                        "_low_speed_threshold",
                        "低航速阈值",
                        ParamType.FLOAT,
                        default=0.5,
                        min_val=0.1,
                        max_val=1.0,
                        step=0.05,
                        description="低于此比例的设计航速视为低航速",
                    ),
                    ParameterDef(
                        "_low_speed_penalty",
                        "低航速油耗惩罚",
                        ParamType.FLOAT,
                        default=1.3,
                        min_val=1.0,
                        max_val=3.0,
                        step=0.05,
                        description="低航速时的燃油消耗倍增系数",
                    ),
                ],
            ),
        ]

    def _estimate_annual_cii(self) -> float:
        if self.model.current_time < 24:
            return self.cii_reference

        recent_emissions = (
            self._emission_history[-self._cii_window_days :]
            if self._emission_history
            else []
        )
        if not recent_emissions:
            return self.cii_reference

        days_in_window = len(recent_emissions)
        daily_avg_co2 = sum(recent_emissions) / days_in_window
        annual_co2 = daily_avg_co2 * 365

        estimated_cii = annual_co2 / (
            self.capacity_teu * self._annual_distance_estimate
        )
        return estimated_cii

    def _get_cii_ratio(self) -> float:
        estimated_cii = self._estimate_annual_cii()
        return estimated_cii / self.cii_reference if self.cii_reference > 0 else 1.0

    def _get_cii_rating(self, cii_value: float) -> str:
        thresholds = {
            k: self.cii_reference * v for k, v in self._cii_rating_thresholds.items()
        }
        for rating in ["A", "B", "C", "D"]:
            if cii_value <= thresholds[rating]:
                return rating
        return "E"

    def update_cii_tracking(self) -> None:
        if self.state == ShipState.SAILING and len(self._emission_history) > 0:
            latest_emission = (
                self._emission_history[-1] if self._emission_history else 0
            )
            estimated_cii = self._estimate_annual_cii()
            self._cii_rating = self._get_cii_rating(estimated_cii)

    def _behind_schedule(self) -> float:
        """计算当前延误小时数"""
        if self.schedule_time <= 0:
            return 0.0
        delay = self.model.current_time - self.schedule_time
        return max(0.0, delay)

    def _navigate(self) -> None:
        """
        航速决策：综合考虑班期约束与CII排放预算。
        CII 评级阈值（参考IMO DCS 2023）：A≤0.85R, B≤1.00R, C≤1.15R, D≤1.35R, E>1.35R
        安全/危险分界线为 D 级阈值 1.35R。
        """
        estimated_cii = self._estimate_annual_cii()
        cii_ratio = (
            estimated_cii / self.cii_reference if self.cii_reference > 0 else 1.0
        )

        delay_hours = self._behind_schedule()
        target_speed = self.economic_speed

        cii_danger = cii_ratio >= self._cii_danger_threshold  # D 级及以上（含D级）
        if cii_danger:
            self._cii_rating = "D"

        if delay_hours > self._delay_threshold_hours:
            if cii_danger:
                # 已延误但CII已达D级：有限加速
                target_speed = min(
                    self.design_speed, self.economic_speed + self._speed_cap_delta
                )
                self.log_decision(
                    reason=f"延误{delay_hours:.0f}h，CII达D级({cii_ratio:.2f})，限速至{target_speed}节",
                    event="speed_decision",
                    decision=f"set_speed:{target_speed}",
                    context={
                        "speed": target_speed,
                        "cii_ratio": cii_ratio,
                        "delay_hours": delay_hours,
                    },
                )
            else:
                # 延误但CII安全（C级及以下）：全速赶班
                target_speed = self.design_speed
                self.log_decision(
                    reason=f"延误{delay_hours:.0f}h，CII安全C级({cii_ratio:.2f})，全速赶班至{target_speed}节",
                    event="speed_decision",
                    decision=f"set_speed:{target_speed}",
                    context={
                        "speed": target_speed,
                        "cii_ratio": cii_ratio,
                        "delay_hours": delay_hours,
                    },
                )
        else:
            if cii_danger:
                # 无延误但CII已达D级：预防性降速
                target_speed = self.economic_speed
                self.log_decision(
                    reason=f"CII达D级({cii_ratio:.2f})，主动降至经济航速{target_speed}节控制排放",
                    event="speed_decision",
                    decision=f"set_speed:{target_speed}",
                    context={"speed": target_speed, "cii_ratio": cii_ratio},
                )
            else:
                # 正常巡航
                target_speed = self.economic_speed
                self.log_decision(
                    reason=f"CII安全({cii_ratio:.2f})，经济航速{target_speed}节航行",
                    event="speed_decision",
                    decision=f"set_speed:{target_speed}",
                    context={"speed": target_speed, "cii_ratio": cii_ratio},
                )

        self.current_speed = target_speed
        self.estimated_annual_cii = estimated_cii

    def handle_event(self, event: Event) -> None:
        if event.event_type == EventType.ARRIVE_PORT:
            self._handle_arrive_port(event)
        elif event.event_type == EventType.BERTH_ALLOCATED:
            self._handle_berth_allocated(event)
        elif event.event_type == EventType.LOADING_COMPLETE:
            self._handle_loading_complete(event)

    def _handle_arrive_port(self, event: Event) -> None:
        self.state = ShipState.ARRIVING
        port_id = event.payload.get("port_id")
        prev_port = event.payload.get("prev_port")

        uncertainty = get_uncertainty_engine()
        weather_delay = 0.0
        if prev_port and self.lat and self.lon:
            prev_port_agent = self.model.get_port(prev_port)
            if prev_port_agent:
                weather_delay = uncertainty.get_weather_delay(
                    prev_port_agent.lat, prev_port_agent.lon, self.lat, self.lon
                )

        port_agent = self.model.get_port(port_id)
        if port_agent:
            port_delay = uncertainty.get_port_delay(port_id, port_agent.queue_length)
        else:
            port_delay = uncertainty.get_port_delay(port_id, 0)

        total_delay = self.cumulative_delay + weather_delay + port_delay

        if port_agent:
            port_agent.record_arrival(
                self.unique_id, self.schedule_time, self.model.current_time
            )

        kpi_calc = get_kpi_calculator()
        kpi_calc.record_arrival(
            self.unique_id, self.schedule_time, self.model.current_time
        )

        self.delay_history.append(
            {
                "port": port_id,
                "sim_time": self.model.current_time,
                "weather_delay": weather_delay,
                "port_delay": port_delay,
                "cumulative_delay": total_delay,
            }
        )

        self.cumulative_delay = min(total_delay, self._cumulative_delay_cap)

        self.log_decision(
            reason=f"到达港口 {port_id}，累计延误 {self.cumulative_delay:.1f} 小时（天气延误 {weather_delay:.1f}h + 港口延误 {port_delay:.1f}h）",
            event=event.event_type,
            decision="request_berth",
            context={
                "port_id": port_id,
                "state": self.state,
                "cumulative_delay": self.cumulative_delay,
                "weather_delay": weather_delay,
                "port_delay": port_delay,
            },
        )

        self.model.scheduler.schedule_event_at(
            self.model.current_time,
            EventType.BERTH_REQUEST,
            port_id,
            {"ship_id": self.unique_id},
        )

    def _handle_berth_allocated(self, event: Event) -> None:
        self.state = ShipState.BERTHING
        port_id = event.payload.get("port_id")

        self.log_decision(
            reason=f"获得泊位 {port_id}",
            event=event.event_type,
            decision="berthed",
            context={"port_id": port_id, "state": self.state},
        )

        self.model.scheduler.schedule_event_at(
            self.model.current_time + self._loading_time_hours,
            EventType.LOADING_COMPLETE,
            self.unique_id,
            {"port_id": port_id},
        )

    def _handle_loading_complete(self, event: Event) -> None:
        self.state = ShipState.DEPARTING
        port_id = event.payload.get("port_id")

        self.log_decision(
            reason=f"装卸完成，准备离港 {port_id}",
            event=event.event_type,
            decision="depart",
            context={"port_id": port_id, "state": self.state},
        )

        self._schedule_departure(port_id)

    def _schedule_departure(self, port_id: str) -> None:
        route = self.model.get_route_for_ship(self.unique_id)
        if not route:
            return

        current_idx = self._route_index
        next_idx = (current_idx + 1) % len(route)
        next_port_id = route[next_idx]

        next_port = self.model.get_port(next_port_id)
        if not next_port:
            return

        # 释放泊位：装卸完成后立即释放，确保港口泊位可被后续船舶使用
        self.model.scheduler.schedule_event_at(
            self.model.current_time,
            EventType.BERTH_RELEASE,
            port_id,
            {"ship_id": self.unique_id},
        )

        distance = haversine(self.lat, self.lon, next_port.lat, next_port.lon)

        self.request_ai_speed_decision()

        # CII 自调节：基于碳排放趋势和延误状态调整航速
        # 注意：AI 启用时 _navigate() 会覆盖 AI 决策结果，故跳过
        if not get_ai_integration().ai_enabled:
            self._navigate()

        sailing_time = distance / self.current_speed

        # 更新预计到达时间（用于延误计算）
        self.schedule_time = self.model.current_time + sailing_time

        self._sailing_segment_start_time = self.model.current_time
        self._sailing_segment_distance = distance

        self._update_fuel_type()

        self.log_decision(
            reason=f"航向 {next_port_id}，距离 {distance:.0f} NM，预计航行 {sailing_time:.1f} 小时（航速 {self.current_speed} 节，{self._current_fuel_type}）",
            event=EventType.DEPART_PORT,
            decision="start_sailing",
            context={
                "from": port_id,
                "to": next_port_id,
                "distance": distance,
                "sailing_time": sailing_time,
                "speed": self.current_speed,
                "fuel_type": self._current_fuel_type,
                "eta": self.schedule_time,
            },
        )

        self.current_port = port_id
        self.next_port = next_port_id
        self.state = ShipState.SAILING
        self._route_index = next_idx

        viz_sync = get_visualization_sync()
        viz_sync.register_sailing(
            ship_id=self.unique_id,
            start_lat=self.lat,
            start_lon=self.lon,
            end_lat=next_port.lat,
            end_lon=next_port.lon,
            start_time=self.model.current_time,
            end_time=self.model.current_time + sailing_time,
            waypoints=get_waypoints(port_id, next_port_id),
        )

        self.model.scheduler.schedule_event_at(
            self.model.current_time + sailing_time,
            EventType.ARRIVE_PORT,
            self.unique_id,
            {"port_id": next_port_id, "prev_port": port_id},
        )

    def log_decision(
        self, reason: str, event: str = "", decision: str = "", context: dict = None
    ) -> None:
        self.decision_log.append(
            {
                "sim_time": self.model.current_time,
                "state": self.state,
                "event": event,
                "decision": decision,
                "reason": reason,
                "context": context or {},
            }
        )
        if len(self.decision_log) > self._decision_log_max:
            self.decision_log.pop(0)

    def update_params(self, params: dict) -> None:
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self) -> dict:
        return {
            "unique_id": self.unique_id,
            "name": self.display_name,
            "state": self.state,
            "current_speed": self.current_speed,
            "design_speed": self.design_speed,
            "economic_speed": self.economic_speed,
            "capacity_teu": self.capacity_teu,
            "load_factor": self.load_factor,
            "current_port": self.current_port,
            "next_port": self.next_port,
            "lat": self.lat,
            "lon": self.lon,
            "co2_emissions": self.co2_emissions,
            "cii_ratio": self._get_cii_ratio(),
            "cii_rating": self._cii_rating,
            "carbon_stats": self.get_carbon_stats(),
            "_route_index": self._route_index,
        }

    def update_sailing_position(self) -> None:
        if self.state != ShipState.SAILING:
            return

        viz_sync = get_visualization_sync()
        lat, lon, status = viz_sync.get_interpolated_position(
            self.unique_id, self.model.current_time
        )

        if status == "START":
            return

        if lat is not None and lon is not None:
            prev_lat, prev_lon = self.lat, self.lon
            self.lat, self.lon = lat, lon

            self._update_fuel_type()

            if prev_lat is not None and prev_lon is not None:
                segment_distance = haversine(prev_lat, prev_lon, self.lat, self.lon)
                self._total_distance_nm += segment_distance

            time_delta = 1.0
            self.update_carbon_emissions(time_delta)

            current_day = int(self.model.current_time // 24)
            if len(self._emission_history) < current_day + 1:
                self._emission_history.append(0.0)

            if len(self._emission_history) > 0:
                self._emission_history[-1] += (
                    self._calculate_emission_rate() * time_delta
                )

            self.update_cii_tracking()

    def _calculate_cii_ratio(self) -> float:
        if self._total_distance_nm > 0:
            cii_value = self._total_co2_tons / (
                self.capacity_teu * self._total_distance_nm
            )
        else:
            cii_value = self._total_co2_tons / (self.capacity_teu * 1.0)
        return cii_value / self.cii_reference if self.cii_reference > 0 else 0.5

    def is_in_eca_zone(self) -> bool:
        """使用 eca.py 模块的统一 ECA 区域检测。"""
        if self.lat is None or self.lon is None:
            return False
        return eca_is_in_eca(self.lat, self.lon) is not None

    def _update_fuel_type(self) -> str:
        was_in_eca = self._current_fuel_type == "MGO"
        is_in_eca = self.is_in_eca_zone()

        if is_in_eca and not was_in_eca:
            self._current_fuel_type = "MGO"
            self.log_decision(
                reason=f"[ECA] 进入ECA区域，燃油切换为MGO（CO2因子: {FUEL_PROPERTIES[FuelType.MGO]['co2_factor']}）",
                event="fuel_switch",
                decision="switch_to_mgo",
                context={"fuel_type": "MGO", "lat": self.lat, "lon": self.lon},
            )
        elif not is_in_eca and was_in_eca:
            self._current_fuel_type = "VLSFO"
            self.log_decision(
                reason=f"[ECA] 离开ECA区域，燃油切换为VLSFO（CO2因子: {FUEL_PROPERTIES[FuelType.VLSFO]['co2_factor']}）",
                event="fuel_switch",
                decision="switch_to_vlsfo",
                context={"fuel_type": "VLSFO", "lat": self.lat, "lon": self.lon},
            )

        return self._current_fuel_type

    def _calculate_emission_rate(self) -> float:

        hourly_fuel = calculate_hourly_fuel_consumption(
            self.current_speed,
            self.base_daily_consumption,
            design_speed=self.design_speed,
            low_speed_threshold=self._low_speed_threshold,
            low_speed_penalty=self._low_speed_penalty,
        )

        co2_factor = (
            FUEL_PROPERTIES[FuelType.MGO]["co2_factor"]
            if self._current_fuel_type == "MGO"
            else FUEL_PROPERTIES[FuelType.VLSFO]["co2_factor"]
        )

        return hourly_fuel * co2_factor

    def update_carbon_emissions(self, time_delta_hours: float) -> None:
        if self.state != ShipState.SAILING or time_delta_hours <= 0:
            return

        emission_rate = self._calculate_emission_rate()
        emission = emission_rate * time_delta_hours

        self._total_co2_tons += emission
        self.co2_emissions += emission

    def get_carbon_stats(self) -> dict:
        return {
            "total_co2_tons": self._total_co2_tons,
            "total_distance_nm": self._total_distance_nm,
            "cii_ratio": self._calculate_cii_ratio(),
            "current_fuel_type": self._current_fuel_type,
            "emission_rate_per_hour": self._calculate_emission_rate(),
        }

    def request_ai_speed_decision(self, target_arrival_time: float = None) -> None:
        ai = get_ai_integration()
        if not ai.ai_enabled:
            return

        context = DecisionContext(
            ship_id=self.unique_id,
            ship_name=self.name,
            current_speed=self.current_speed,
            economic_speed=self.economic_speed,
            design_speed=self.design_speed,
            current_state=self.state,
            current_port=self.current_port,
            next_port=self.next_port,
            lat=self.lat,
            lon=self.lon,
            cumulative_delay=self.cumulative_delay,
            cii_ratio=self._get_cii_ratio(),
            co2_emissions=self.co2_emissions,
            capacity_teu=self.capacity_teu,
            sim_time=self.model.current_time,
            route=self.model.get_route_for_ship(self.unique_id),
        )

        decision = ai.request_speed_decision(context, target_arrival_time)
        if decision:
            self.apply_ai_decision(decision)

    def apply_ai_decision(self, decision) -> None:
        if decision.decision_type.value == "speed_adjustment":
            old_speed = self.current_speed
            self.current_speed = decision.suggested_value

            self.log_decision(
                reason=f"[AI] {decision.reason}",
                event="ai_speed_decision",
                decision="ai_adjust_speed",
                context={
                    "old_speed": old_speed,
                    "new_speed": self.current_speed,
                    "ai_confidence": decision.confidence,
                    "suggested_value": decision.suggested_value,
                },
            )


class CraneAgent(BaseAgent):
    """岸桥 Agent —— 深层嵌套示范：Port → Cranes → CraneAgent"""

    def __init__(self, unique_id: str = None, owner: ActiveObject = None, **kwargs):
        super().__init__(unique_id=unique_id, owner=owner)
        self._display_name = kwargs.get("name", unique_id or "crane")
        self.handling_rate = kwargs.get("handling_rate", 30)
        self.status = kwargs.get("status", "idle")  # idle | working | maintenance
        self.assigned_ship = kwargs.get("assigned_ship", None)
        self.total_moves = kwargs.get("total_moves", 0)

    @classmethod
    def get_parameter_defs(cls) -> list[ParameterDef]:
        return [
            ParameterDef(
                "handling_rate",
                "作业效率",
                ParamType.INT,
                default=30,
                unit="TEU/h",
                min_val=10,
                max_val=60,
                step=5,
            ),
            ParameterDef(
                "status",
                "状态",
                ParamType.ENUM,
                default="idle",
                options=[
                    {"label": "空闲", "value": "idle"},
                    {"label": "作业中", "value": "working"},
                    {"label": "维护", "value": "maintenance"},
                ],
            ),
            ParameterDef(
                "total_moves",
                "累计箱量",
                ParamType.INT,
                default=0,
                description="累计装卸箱量",
            ),
        ]

    def to_dict(self) -> dict:
        return {
            "unique_id": self.unique_id,
            "name": self.display_name,
            "handling_rate": self.handling_rate,
            "status": self.status,
            "assigned_ship": self.assigned_ship,
            "total_moves": self.total_moves,
        }


class PortAgent(BaseAgent):
    def __init__(
        self,
        unique_id: str = None,
        owner: ActiveObject = None,
        model: "SimulationModel" = None,
        **kwargs,
    ):
        super().__init__(unique_id=unique_id, owner=owner)
        self._display_name = kwargs.get("name", unique_id or "port")
        self.lat = kwargs.get("lat", 0.0)
        self.lon = kwargs.get("lon", 0.0)
        self.berth_count = kwargs.get("berth_count", 4)
        self.crane_count = kwargs.get("crane_count", 8)
        self.handling_rate = kwargs.get("handling_rate", 120)
        self.available_berths = self.berth_count
        self.waiting_queue = []
        self.occupied_berths = {}
        self.arrival_history = []
        self.scheduled_times = {}
        self.actual_times = {}

        # 兼容旧接口：模型直接嵌入
        if model is not None:
            model.embed(self)

        # 岸桥子 Agent 树（深层嵌套示范）
        self.cranes = AgentPopulation(CraneAgent, owner=self, name="cranes")
        crane_count = kwargs.get("crane_count", 8)
        for i in range(crane_count):
            self.cranes.add(
                name=f"crane_{i + 1}", handling_rate=self.handling_rate // 2
            )

    @classmethod
    def get_parameter_defs(cls) -> list[ParameterDef]:
        """返回港口 Agent 的所有可配置参数定义。"""
        return [
            ParameterDef(
                "berth_count",
                "泊位数",
                ParamType.INT,
                default=4,
                min_val=1,
                max_val=20,
                step=1,
            ),
            ParameterDef(
                "crane_count",
                "岸桥数",
                ParamType.INT,
                default=8,
                min_val=1,
                max_val=30,
                step=1,
            ),
            ParameterDef(
                "handling_rate",
                "装卸效率",
                ParamType.INT,
                default=120,
                unit="TEU/h",
                min_val=30,
                max_val=300,
                step=10,
            ),
        ]

    def record_arrival(
        self, ship_id: str, scheduled_time: float, actual_time: float
    ) -> None:
        self.scheduled_times[ship_id] = scheduled_time
        self.actual_times[ship_id] = actual_time
        self.arrival_history.append(
            {
                "ship_id": ship_id,
                "scheduled": scheduled_time,
                "actual": actual_time,
                "delay": max(0.0, actual_time - scheduled_time),
            }
        )

    @property
    def queue_length(self) -> int:
        return len(self.waiting_queue)

    def handle_event(self, event: Event) -> None:
        if event.event_type == EventType.BERTH_REQUEST:
            self._handle_berth_request(event)
        elif event.event_type == EventType.BERTH_RELEASE:
            self._handle_berth_release(event)

    def _handle_berth_request(self, event: Event) -> None:
        ship_id = event.payload.get("ship_id")
        if self.available_berths > 0:
            self.available_berths -= 1
            self.occupied_berths[ship_id] = "OCCUPIED"
            self.model.scheduler.schedule_event_at(
                self.model.current_time,
                EventType.BERTH_ALLOCATED,
                ship_id,
                {"port_id": self.unique_id},
            )
        else:
            self.waiting_queue.append(ship_id)

    def _handle_berth_release(self, event: Event) -> None:
        ship_id = event.payload.get("ship_id")
        if ship_id in self.occupied_berths:
            del self.occupied_berths[ship_id]
            self.available_berths += 1

            if self.waiting_queue:
                next_ship = self.waiting_queue.pop(0)
                self.occupied_berths[next_ship] = "OCCUPIED"
                self.available_berths -= 1
                self.model.scheduler.schedule_event_at(
                    self.model.current_time,
                    EventType.BERTH_ALLOCATED,
                    next_ship,
                    {"port_id": self.unique_id},
                )

    def to_dict(self) -> dict:
        return {
            "unique_id": self.unique_id,
            "name": self.display_name,
            "lat": self.lat,
            "lon": self.lon,
            "berth_count": self.berth_count,
            "available_berths": self.available_berths,
            "waiting_queue": self.waiting_queue,
            "queue_length": len(self.waiting_queue),
            "cranes": {
                name: crane.to_dict() for name, crane in self.cranes.get_all().items()
            },
        }


class SimulationModel(ActiveObject):
    def __init__(self, engine: Engine = None):
        # 如果没有传入 engine，自动创建一个
        if engine is None:
            engine = Engine()
        self._name = "model"
        super().__init__(owner=engine)
        self._engine = engine  # 直接持有引用
        self.is_running: bool = False
        self.speed: float = 1.0
        self.simulation_mode = SimulationMode.ACADEMIC
        self.ais_source_mode = "mock"
        self.scheduler = EventDrivenScheduler(engine)
        self._agents = {}
        self._ship_routes = {}
        self._ports = {}
        self._ais_adapter = None

        get_ai_integration().set_model(self)

    @property
    def current_time(self) -> float:
        """当前仿真时间（委托给 Engine）。"""
        return self._engine.current_time

    @current_time.setter
    def current_time(self, val: float) -> None:
        self._engine.current_time = val

    def update_all_ships(self) -> None:
        for agent in self._agents.values():
            if isinstance(agent, ShipAgent):
                agent.update_sailing_position()

    def add_agent(self, agent: BaseAgent) -> None:
        self._agents[agent.unique_id] = agent
        # 使用 unique_id 作为树节点名称（而非中文名）
        self.embed(agent, name=agent.unique_id)
        if isinstance(agent, PortAgent):
            self._ports[agent.unique_id] = agent

    def remove_agent(self, agent_id: str):
        """
        按 unique_id 删除 agent，清理所有内部注册表。
        供 DELETE /api/sim/tree/agent 使用。
        """
        agent = self._agents.pop(agent_id, None)
        if agent is None:
            return None

        self._ports.pop(agent_id, None)
        self._ship_routes.pop(agent_id, None)
        self._embedded.pop(agent_id, None)
        agent._owner = None

        if hasattr(agent, "on_destroy"):
            try:
                agent.on_destroy()
            except Exception:
                pass

        return agent

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        return self._agents.get(agent_id)

    def get_port(self, port_id: str) -> Optional[PortAgent]:
        return self._ports.get(port_id)

    def get_all_ships(self) -> dict[str, dict]:
        return {
            aid: agent.to_dict()
            for aid, agent in self._agents.items()
            if isinstance(agent, ShipAgent)
        }

    def get_all_ports(self) -> dict[str, dict]:
        return {
            aid: agent.to_dict()
            for aid, agent in self._agents.items()
            if isinstance(agent, PortAgent)
        }

    def get_state(self) -> dict:
        return {
            "current_time": self.current_time,
            "is_running": self.is_running,
            "speed": self.speed,
            "simulation_mode": self.simulation_mode.value,
            "ais_source_mode": getattr(self, "ais_source_mode", "mock"),
            "ships": self.get_all_ships(),
            "ports": self.get_all_ports(),
        }

    def run_until(self, end_time: float) -> int:
        return self.scheduler.run_until(end_time)

    def reset(self) -> None:
        self._engine.current_time = 0.0
        self.is_running = False
        self.speed = 1.0
        self._agents = {}
        self._ship_routes = {}
        self._ports = {}
        self._embedded = {}  # 清空树
        self.scheduler = EventDrivenScheduler(self._engine)
        self.simulation_mode = SimulationMode.ACADEMIC
        self._ais_adapter = None
        get_visualization_sync().clear()
        get_kpi_calculator().reset()
        _reset_uncertainty()
        _init_demo_scenario(self)

    def set_route_for_ship(self, ship_id: str, route: list[str]) -> None:
        self._ship_routes[ship_id] = route

    def get_route_for_ship(self, ship_id: str) -> list[str]:
        return self._ship_routes.get(ship_id, [])

    def _get_ships_ais_data(self) -> list[dict]:
        """为 AIS Mock 模式提供船舶位置数据。"""
        ships_data = []
        for agent in self._agents.values():
            if isinstance(agent, ShipAgent):
                ships_data.append(
                    {
                        "ship_id": agent.unique_id,
                        "lat": agent.lat or 0.0,
                        "lon": agent.lon or 0.0,
                        "current_speed": agent.current_speed,
                        "speed": agent.current_speed,
                    }
                )
        return ships_data


_model_lock: threading.Lock = threading.Lock()
_global_model: Optional[SimulationModel] = None
_global_engine: Optional[Engine] = None


def get_model() -> SimulationModel:
    global _global_model, _global_engine
    if _global_model is None:
        with _model_lock:
            if _global_model is None:
                _global_engine = Engine()
                _global_model = SimulationModel(engine=_global_engine)
                _init_demo_scenario(_global_model)
    return _global_model


def get_engine() -> Engine:
    get_model()  # 确保已初始化
    return _global_engine


def _reset_uncertainty() -> None:
    """使用不确定性引擎模块的公共 API 进行重置。"""
    reset_uncertainty_engine()


def _init_demo_scenario(model: SimulationModel) -> None:
    """初始化 AEU 真实航线场景。"""
    from ..data.aeu_data import (
        AEU_VESSELS,
        AEU_PORT_ROTATIONS,
        AEU_SERVICES,
        AEU_PORT_COORDS,
        PORT_CODES_TO_NAMES,
        ALL_PORTS,
        get_port_infra,
        get_service_ships,
    )

    # ── 1. 创建港口 ──
    for port_code in ALL_PORTS:
        lat, lon = AEU_PORT_COORDS.get(port_code, (0.0, 0.0))
        berth_cnt, crane_cnt, handling_rate = get_port_infra(port_code)
        name = PORT_CODES_TO_NAMES.get(port_code, port_code)
        port = PortAgent(
            unique_id=port_code,
            model=model,
            name=name,
            lat=lat,
            lon=lon,
            berth_count=berth_cnt,
            crane_count=crane_cnt,
            handling_rate=handling_rate,
        )
        model.add_agent(port)

    # ── 2. 创建船舶（每周发一艘，错峰起航） ──
    service_ship_idx: dict[str, int] = {}
    for v in AEU_VESSELS:
        service = v["service"]
        week_idx = service_ship_idx.get(service, 0)
        service_ship_idx[service] = week_idx + 1
        start_delay_hours = week_idx * 168

        route = AEU_PORT_ROTATIONS.get(service, [])
        home_port_code = route[0] if route else "CNTAO"
        home_port = model.get_port(home_port_code)
        if not home_port:
            continue

        eco_speed = round(v["design_speed"] * 0.82, 1)
        load_factor = 0.75 if v["capacity"] > 20000 else 0.8

        ship = ShipAgent(
            unique_id=v["id"],
            model=model,
            name=v["name"],
            state=ShipState.SAILING,
            current_speed=eco_speed,
            design_speed=v["design_speed"],
            economic_speed=eco_speed,
            capacity_teu=v["capacity"],
            load_factor=load_factor,
            base_daily_consumption=v["fuel_consumption"],
            current_port=home_port_code,
            next_port=None,
            lat=home_port.lat,
            lon=home_port.lon,
            _route_index=0,
        )
        model.add_agent(ship)
        model.set_route_for_ship(v["id"], route)

        if len(route) > 1:
            next_port_id = route[1]
            next_port = model.get_port(next_port_id)
            if next_port:
                distance = haversine(
                    home_port.lat, home_port.lon, next_port.lat, next_port.lon
                )
                sailing_time = distance / eco_speed

                ship._route_index = 1
                ship._sailing_segment_start_time = start_delay_hours
                ship.schedule_time = start_delay_hours + sailing_time
                ship.next_port = next_port_id

                viz_sync = get_visualization_sync()
                viz_sync.register_sailing(
                    ship_id=v["id"],
                    start_lat=home_port.lat,
                    start_lon=home_port.lon,
                    end_lat=next_port.lat,
                    end_lon=next_port.lon,
                    start_time=start_delay_hours,
                    end_time=start_delay_hours + sailing_time,
                    waypoints=get_waypoints(home_port_code, next_port_id),
                )

                model.scheduler.schedule_event_at(
                    start_delay_hours + sailing_time,
                    EventType.ARRIVE_PORT,
                    v["id"],
                    {"port_id": next_port_id, "prev_port": home_port_code},
                )
