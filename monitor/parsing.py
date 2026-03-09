import json
from datetime import datetime, timezone
from typing import Any

from monitor.utils import nested_get, parse_dt


def parse_cloudwatch_message(raw_message: str) -> dict[str, Any]:
    raw_message = raw_message.strip()
    if not raw_message:
        return {}
    try:
        first = json.loads(raw_message)
    except json.JSONDecodeError:
        return {"message": raw_message}
    if isinstance(first, dict):
        inner_message = first.get("message")
        if isinstance(inner_message, str) and inner_message.startswith("{"):
            try:
                second = json.loads(inner_message)
                if isinstance(second, dict):
                    return second
            except json.JSONDecodeError:
                pass
        return first
    return {"message": raw_message}


def is_fail_event(doc: dict[str, Any], raw_message: str) -> bool:
    action_value = nested_get(doc, ["action", "action"])
    if isinstance(action_value, str) and action_value.upper() == "FAIL":
        return True
    lowered = raw_message.lower()
    return (
        '"action":"FAIL"' in raw_message
        or '"action": "FAIL"' in raw_message
        or "failed to create disbursement" in lowered
        or "error processing withdrawal" in lowered
    )


def extract_timestamp(doc: dict[str, Any], fallback_epoch_ms: int | None) -> datetime | None:
    candidate_paths = [
        ["createdAt"],
        ["created_at"],
        ["timestamp"],
        ["event_time"],
        ["ts"],
        ["action", "timestamp"],
    ]
    for path in candidate_paths:
        parsed = parse_dt(nested_get(doc, path))
        if parsed:
            return parsed.astimezone(timezone.utc)
    if fallback_epoch_ms is not None:
        return datetime.fromtimestamp(fallback_epoch_ms / 1000.0, tz=timezone.utc)
    return None


def extract_error_message(doc: dict[str, Any], raw_message: str) -> str:
    candidate_paths = [
        ["action", "errorMessage"],
        ["action", "error_message"],
        ["action", "message"],
        ["action", "error", "message"],
        ["error", "message"],
        ["message"],
    ]
    for path in candidate_paths:
        value = nested_get(doc, path)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return raw_message.strip()
