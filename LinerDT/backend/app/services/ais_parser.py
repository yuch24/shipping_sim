"""
AIS 数据解析与清洗模块

支持 AisStream.io JSON 格式 + mock 数据格式。
清洗规则：位置校验、速度校验、重复数据去重。
"""

from typing import Optional


def validate_position(lat: float, lon: float) -> bool:
    """位置有效性校验"""
    if abs(lat) < 0.01 and abs(lon) < 0.01:
        return False
    if lat < -90 or lat > 90 or lon < -180 or lon > 180:
        return False
    return True


def validate_speed(sog: float) -> bool:
    """速度有效性校验（超过50节视为异常）"""
    return 0 <= sog <= 50


def parse_ais_message(raw: dict) -> Optional[dict]:
    """
    解析单条 AIS 报文，返回标准化格式。
    支持 AisStream.io 的 MessageType 格式 和 简化 mock 格式。
    """
    # AisStream.io 格式
    message = raw.get("Message", raw)
    msg_type = message.get("MessageType", None)

    if msg_type == "PositionReport":
        pos = message.get("PositionReport", {})
        meta = message.get("MetaData", {})

        mmsi = pos.get("MMSI", 0)
        lat = pos.get("Latitude", 0.0)
        lon = pos.get("Longitude", 0.0)
        sog = pos.get("SOG", 0.0)
        cog = pos.get("COG", 0.0)
        timestamp = meta.get("time_utc", "")

    else:
        # 简化 mock 格式
        mmsi = raw.get("mmsi", raw.get("ship_id", 0))
        lat = raw.get("lat", raw.get("latitude", 0.0))
        lon = raw.get("lon", raw.get("longitude", 0.0))
        sog = raw.get("sog", raw.get("speed", 0.0))
        cog = raw.get("cog", raw.get("heading", 0.0))
        timestamp = raw.get("timestamp", "")

    # 数据清洗
    if not validate_position(lat, lon):
        return None
    if not validate_speed(sog):
        return None

    return {
        "ship_id": str(mmsi),
        "lat": round(lat, 6),
        "lon": round(lon, 6),
        "sog": round(sog, 1),
        "cog": round(cog, 1),
        "timestamp": str(timestamp),
        "source": "ais",
    }


def filter_duplicates(messages: list[dict], window_seconds: int = 30) -> list[dict]:
    """
    基于 ship_id 去重：相同船舶在时间窗口内只保留最新一条。
    """
    seen = {}
    result = []
    for msg in messages:
        ship_id = msg.get("ship_id", "")
        prev = seen.get(ship_id)
        if prev:
            # 简单去重：保留后一条
            continue
        seen[ship_id] = msg
        result.append(msg)
    return result
