import json
import re
from datetime import datetime, timezone
from typing import Any

from monitor.types import IncidentContext
from monitor.utils import nested_get, parse_dt

REQUEST_ID_PATTERNS = (
    re.compile(r"START RequestId:\s*(?P<value>[0-9a-f-]{36})", re.IGNORECASE),
    re.compile(r"\[[A-Z]+\]\t[^\t]+\t(?P<value>[0-9a-f-]{36})\t"),
)
WITHDRAWAL_ID_PATTERN = re.compile(
    r"Error processing withdrawal (?P<value>[0-9a-f-]{36})",
    re.IGNORECASE,
)
CLAVE_RASTREO_PATTERN = re.compile(
    r"['\"]claveRastreo['\"]\s*:\s*['\"](?P<value>[^'\"]+)['\"]"
)
DESCRIPCION_ERROR_PATTERN = re.compile(
    r"['\"]descripcionError['\"]\s*:\s*['\"](?P<value>[^'\"]+)['\"]"
)
STP_RESULT_ID_PATTERN = re.compile(r"['\"]id['\"]\s*:\s*(?P<value>-?\d+)")


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


def extract_incident_context(doc: dict[str, Any], raw_message: str) -> IncidentContext:
    return IncidentContext(
        withdrawal_id=_extract_withdrawal_id(doc, raw_message),
        lambda_request_id=_extract_lambda_request_id(doc, raw_message),
        clave_rastreo=_extract_clave_rastreo(doc, raw_message),
        descripcion_error=_extract_descripcion_error(doc, raw_message),
        stp_result_id=_extract_stp_result_id(doc, raw_message),
    )


def merge_incident_context(
    primary: IncidentContext, secondary: IncidentContext
) -> IncidentContext:
    return IncidentContext(
        withdrawal_id=primary.withdrawal_id or secondary.withdrawal_id,
        lambda_request_id=primary.lambda_request_id or secondary.lambda_request_id,
        clave_rastreo=primary.clave_rastreo or secondary.clave_rastreo,
        descripcion_error=primary.descripcion_error or secondary.descripcion_error,
        stp_result_id=primary.stp_result_id or secondary.stp_result_id,
    )


def _extract_string_value(doc: dict[str, Any], candidate_paths: list[list[str]]) -> str:
    for path in candidate_paths:
        value = nested_get(doc, path)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _extract_match(patterns: tuple[re.Pattern[str], ...], raw_message: str) -> str:
    for pattern in patterns:
        match = pattern.search(raw_message)
        if match:
            return match.group("value").strip()
    return ""


def _extract_single_match(pattern: re.Pattern[str], raw_message: str) -> str:
    match = pattern.search(raw_message)
    if not match:
        return ""
    return match.group("value").strip()


def _extract_lambda_request_id(doc: dict[str, Any], raw_message: str) -> str:
    candidate_paths = [
        ["requestId"],
        ["request_id"],
        ["aws_request_id"],
        ["lambda_request_id"],
        ["context", "aws_request_id"],
    ]
    return _extract_string_value(doc, candidate_paths) or _extract_match(
        REQUEST_ID_PATTERNS, raw_message
    )


def _extract_withdrawal_id(doc: dict[str, Any], raw_message: str) -> str:
    candidate_paths = [
        ["withdrawal_id"],
        ["withdrawalId"],
        ["action", "withdrawal_id"],
        ["action", "withdrawalId"],
    ]
    return _extract_string_value(doc, candidate_paths) or _extract_single_match(
        WITHDRAWAL_ID_PATTERN, raw_message
    )


def _extract_clave_rastreo(doc: dict[str, Any], raw_message: str) -> str:
    candidate_paths = [
        ["claveRastreo"],
        ["data", "claveRastreo"],
        ["request", "data", "claveRastreo"],
        ["action", "request", "data", "claveRastreo"],
    ]
    return _extract_string_value(doc, candidate_paths) or _extract_single_match(
        CLAVE_RASTREO_PATTERN, raw_message
    )


def _extract_descripcion_error(doc: dict[str, Any], raw_message: str) -> str:
    candidate_paths = [
        ["resultado", "descripcionError"],
        ["error", "descripcionError"],
        ["action", "error", "descripcionError"],
    ]
    return _extract_string_value(doc, candidate_paths) or _extract_single_match(
        DESCRIPCION_ERROR_PATTERN, raw_message
    )


def _extract_stp_result_id(doc: dict[str, Any], raw_message: str) -> str:
    candidate_paths = [
        ["resultado", "id"],
        ["error", "id"],
        ["action", "error", "id"],
    ]
    return _extract_string_value(doc, candidate_paths) or _extract_single_match(
        STP_RESULT_ID_PATTERN, raw_message
    )
