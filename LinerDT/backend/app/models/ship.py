from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel


class ShipState(str, Enum):
    IDLE = "IDLE"
    SAILING = "SAILING"
    ARRIVING = "ARRIVING"
    WAITING = "WAITING"
    BERTHING = "BERTHING"
    LOADING = "LOADING"
    UNLOADING = "UNLOADING"
    DEPARTING = "DEPARTING"


class Ship(BaseModel):
    unique_id: str
    name: str
    capacity_teu: int
    current_speed: float
    design_speed: float
    economic_speed: float
    state: ShipState = ShipState.IDLE
    current_port: Optional[str] = None
    next_port: Optional[str] = None
    load_factor: float = 0.8
    lat: Optional[float] = None
    lon: Optional[float] = None
    co2_emissions: float = 0.0

    class Config:
        use_enum_values = True


class Port(BaseModel):
    unique_id: str
    name: str
    country: str
    lat: float
    lon: float
    berth_count: int
    crane_count: int
    handling_rate: float
    queue_length: int = 0
    waiting_ships: list[str] = []

    class Config:
        use_enum_values = True


class Route(BaseModel):
    unique_id: str
    name: str
    ports: list[str]
    distance_matrix: dict[str, dict[str, float]]


class SimState(BaseModel):
    current_time: float
    is_running: bool
    speed: float
    ships: dict[str, Ship]
    ports: dict[str, Port]

    class Config:
        use_enum_values = True
