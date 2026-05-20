from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class DecisionType(Enum):
    SPEED_ADJUSTMENT = "speed_adjustment"
    PORT_SELECTION = "port_selection"
    BERTH_TIMING = "berth_timing"
    ROUTE_ADJUSTMENT = "route_adjustment"


@dataclass
class DecisionContext:
    ship_id: str
    ship_name: str
    current_speed: float
    economic_speed: float
    design_speed: float
    current_state: str
    current_port: Optional[str]
    next_port: Optional[str]
    lat: Optional[float] = None
    lon: Optional[float] = None
    cumulative_delay: float = 0.0
    cii_ratio: float = 0.0
    co2_emissions: float = 0.0
    capacity_teu: int = 0
    sim_time: float = 0.0
    route: Optional[list] = None


@dataclass
class AIDecision:
    decision_type: DecisionType
    ship_id: str
    suggested_action: str
    suggested_value: Any
    reason: str
    confidence: float
    context: Dict[str, Any]


class BaseAIAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.decision_history: list[AIDecision] = []

    @abstractmethod
    def evaluate_speed(
        self,
        context: DecisionContext,
        target_arrival_time: Optional[float] = None
    ) -> Optional[AIDecision]:
        pass

    @abstractmethod
    def evaluate_port_timing(
        self,
        context: DecisionContext,
        available_ports: list[str]
    ) -> Optional[AIDecision]:
        pass

    def record_decision(self, decision: AIDecision) -> None:
        self.decision_history.append(decision)
        if len(self.decision_history) > 500:
            self.decision_history.pop(0)

    def get_recent_decisions(self, ship_id: str = None, limit: int = 10) -> list[AIDecision]:
        if ship_id is None:
            return self.decision_history[-limit:]
        return [d for d in self.decision_history if d.ship_id == ship_id][-limit:]
