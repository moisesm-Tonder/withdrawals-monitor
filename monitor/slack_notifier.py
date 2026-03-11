import re
import unicodedata
from datetime import datetime, timezone

import requests

from monitor.types import IncidentContext

ANALYSIS_LABELS = {
    "causa probable": "Causa probable",
    "impacto potencial": "Impacto potencial",
    "accion sugerida": "Accion sugerida",
}


def send_slack_alert(
    webhook_url: str,
    severity: str,
    error_type: str,
    occurrences: int,
    window_minutes: int,
    analysis: str,
    incident_context: IncidentContext | None = None,
) -> None:
    severity_upper = severity.upper()
    if severity_upper == "CRITICAL":
        color = "#d40e0d"
        sev_icon = ":red_circle:"
    elif severity_upper == "HIGH":
        color = "#ff8c00"
        sev_icon = ":large_orange_circle:"
    else:
        color = "#2f81f7"
        sev_icon = ":large_blue_circle:"

    blocks: list[dict[str, object]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Withdrawal Incident Alert"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{sev_icon} *Severity:* `{severity_upper}`",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Error Type*\n`{_format_inline(error_type)}`",
                },
                {"type": "mrkdwn", "text": f"*Occurrences*\n`{occurrences}`"},
                {
                    "type": "mrkdwn",
                    "text": f"*Window*\n`last {window_minutes} minutes`",
                },
                {
                    "type": "mrkdwn",
                    "text": (
                        "*Detected At (UTC)*\n"
                        f"`{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}`"
                    ),
                },
            ],
        },
    ]

    related_blocks = _build_related_blocks(incident_context)
    if related_blocks:
        blocks.extend([{"type": "divider"}, *related_blocks])

    analysis_blocks = _build_analysis_blocks(analysis)
    if analysis_blocks:
        blocks.extend([{"type": "divider"}, *analysis_blocks])

    payload = {
        "text": f"Withdrawal Error Detected | {severity_upper} | {error_type}",
        "attachments": [{"color": color, "blocks": blocks}],
    }
    response = requests.post(webhook_url, json=payload, timeout=12)
    if response.status_code >= 300:
        raise RuntimeError(
            f"Slack webhook error ({response.status_code}): {response.text[:300]}"
        )


def _build_related_blocks(
    incident_context: IncidentContext | None,
) -> list[dict[str, object]]:
    if not incident_context or incident_context.score() == 0:
        return []

    blocks: list[dict[str, object]] = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Related Execution*"},
        }
    ]

    context_fields = _build_context_fields(incident_context)
    if context_fields:
        blocks.append({"type": "section", "fields": context_fields})

    if incident_context.descripcion_error:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*descripcionError*\n"
                        f"`{_format_inline(incident_context.descripcion_error, limit=200)}`"
                    ),
                },
            }
        )

    return blocks


def _build_analysis_blocks(analysis: str) -> list[dict[str, object]]:
    items = _normalize_analysis_items(analysis)
    if not items:
        return []

    blocks: list[dict[str, object]] = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Analysis*"},
        }
    ]
    for title, body in items:
        text = _format_text(body, limit=500)
        if not text:
            continue
        if title:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*{title}*\n{text}"},
                }
            )
        else:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": text},
                }
            )
    return blocks


def _normalize_analysis_items(analysis: str) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for raw_line in analysis.splitlines():
        cleaned = _clean_analysis_line(raw_line)
        if not cleaned:
            continue
        label, body = _split_analysis_label(cleaned)
        items.append((label, body))
    return items


def _clean_analysis_line(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return ""
    cleaned = cleaned.replace("**", "")
    cleaned = re.sub(r"^[-*\u2022\s]+", "", cleaned)
    cleaned = re.sub(r"^\d+[\)\.\-:]\s*", "", cleaned)
    return cleaned.strip()


def _split_analysis_label(value: str) -> tuple[str, str]:
    if ":" not in value:
        return "", value
    raw_label, raw_body = value.split(":", 1)
    normalized_label = _normalize_label(raw_label)
    body = raw_body.strip()
    if normalized_label in ANALYSIS_LABELS and body:
        return ANALYSIS_LABELS[normalized_label], body
    return "", value


def _normalize_label(value: str) -> str:
    normalized = "".join(
        char
        for char in unicodedata.normalize("NFKD", value.strip().lower())
        if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", normalized)


def _build_context_fields(
    incident_context: IncidentContext,
) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    if incident_context.withdrawal_id:
        fields.append(
            {
                "type": "mrkdwn",
                "text": (
                    "*Withdrawal ID*\n"
                    f"`{_format_inline(incident_context.withdrawal_id)}`"
                ),
            }
        )
    if incident_context.lambda_request_id:
        fields.append(
            {
                "type": "mrkdwn",
                "text": (
                    "*Lambda Request ID*\n"
                    f"`{_format_inline(incident_context.lambda_request_id)}`"
                ),
            }
        )
    if incident_context.clave_rastreo:
        fields.append(
            {
                "type": "mrkdwn",
                "text": (
                    "*Clave Rastreo*\n"
                    f"`{_format_inline(incident_context.clave_rastreo)}`"
                ),
            }
        )
    if incident_context.stp_result_id:
        fields.append(
            {
                "type": "mrkdwn",
                "text": (
                    "*STP Result ID*\n"
                    f"`{_format_inline(incident_context.stp_result_id)}`"
                ),
            }
        )
    return fields


def _format_inline(value: str, limit: int = 120) -> str:
    return value.replace("`", "'")[:limit]


def _format_text(value: str, limit: int = 500) -> str:
    return value.replace("`", "'").strip()[:limit]
