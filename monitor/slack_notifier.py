from datetime import datetime, timezone

import requests


def send_slack_alert(
    webhook_url: str,
    severity: str,
    error_type: str,
    occurrences: int,
    window_minutes: int,
    analysis: str,
) -> None:
    severity_upper = severity.upper()
    if severity_upper == "CRITICAL":
        color = "#d40e0d"
        sev_icon = "🔴"
    elif severity_upper == "HIGH":
        color = "#ff8c00"
        sev_icon = "🟠"
    else:
        color = "#2f81f7"
        sev_icon = "🔵"

    analysis_lines = [line.strip() for line in analysis.splitlines() if line.strip()]
    if not analysis_lines:
        analysis_lines = [analysis.strip()]
    formatted_analysis = "\n".join(f"• {line}" for line in analysis_lines if line)

    payload = {
        "text": f"Withdrawal Error Detected | {severity_upper} | {error_type}",
        "attachments": [
            {
                "color": color,
                "blocks": [
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
                            {"type": "mrkdwn", "text": f"*Error Type*\n`{error_type}`"},
                            {"type": "mrkdwn", "text": f"*Occurrences*\n`{occurrences}`"},
                            {"type": "mrkdwn", "text": f"*Window*\n`last {window_minutes} minutes`"},
                            {
                                "type": "mrkdwn",
                                "text": f"*Detected At (UTC)*\n`{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}`",
                            },
                        ],
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*Analysis*\n{formatted_analysis}"},
                    },
                ],
            }
        ],
    }
    response = requests.post(webhook_url, json=payload, timeout=12)
    if response.status_code >= 300:
        raise RuntimeError(
            f"Slack webhook error ({response.status_code}): {response.text[:300]}"
        )
