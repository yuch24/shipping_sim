import heapq
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Event:
    time: float
    event_type: str
    target_agent_id: str
    payload: dict = field(default_factory=dict)
    source: str = "system"

    def __lt__(self, other):
        return self.time < other.time


class EventQueue:
    def __init__(self):
        self._heap: list[Event] = []
        self._counter = 0

    def push(self, event: Event) -> None:
        heapq.heappush(self._heap, (event.time, self._counter, event))
        self._counter += 1

    def pop(self) -> Optional[Event]:
        if not self._heap:
            return None
        _, _, event = heapq.heappop(self._heap)
        return event

    def peek(self) -> Optional[Event]:
        if not self._heap:
            return None
        _, _, event = self._heap[0]
        return event

    def is_empty(self) -> bool:
        return len(self._heap) == 0

    def size(self) -> int:
        return len(self._heap)

    def to_list(self) -> list[dict]:
        return [
            {
                "time": e.time,
                "event_type": e.event_type,
                "target_agent_id": e.target_agent_id,
                "payload": e.payload,
                "source": e.source,
            }
            for _, _, e in sorted(self._heap)
        ]

    @classmethod
    def from_list(cls, data: list[dict]) -> "EventQueue":
        eq = cls()
        for item in data:
            event = Event(
                time=item["time"],
                event_type=item["event_type"],
                target_agent_id=item["target_agent_id"],
                payload=item.get("payload", {}),
                source=item.get("source", "system"),
            )
            eq.push(event)
        return eq
