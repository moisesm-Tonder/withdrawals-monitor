import hashlib
from datetime import datetime, timezone
from typing import Any


def nested_get(doc: dict[str, Any], path: list[str]) -> Any:
    current: Any = doc
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 10_000_000_000:
            ts = ts / 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        text = text.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def floor_window_start(now_utc: datetime, window_minutes: int) -> datetime:
    minute_bucket = (now_utc.minute // window_minutes) * window_minutes
    return now_utc.replace(minute=minute_bucket, second=0, microsecond=0)


def build_incident_hash(error_type: str, window_start: datetime) -> str:
    raw = f"{error_type}|{window_start.isoformat()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
