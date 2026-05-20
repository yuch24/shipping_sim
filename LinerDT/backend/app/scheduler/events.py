from enum import Enum


class EventType(str, Enum):
    """类型安全的事件类型枚举。"""
    ARRIVE_PORT = "arrive_port"
    DEPART_PORT = "depart_port"
    BERTH_REQUEST = "berth_request"
    BERTH_ALLOCATED = "berth_allocated"
    BERTH_RELEASE = "berth_release"
    LOADING_COMPLETE = "loading_complete"
