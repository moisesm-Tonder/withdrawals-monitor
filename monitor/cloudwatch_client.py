from typing import Any


def fetch_candidate_events(
    logs_client: Any,
    log_group_name: str,
    start_epoch_ms: int,
    end_epoch_ms: int,
    filter_pattern: str,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "logGroupName": log_group_name,
        "startTime": start_epoch_ms,
        "endTime": end_epoch_ms,
        "interleaved": True,
    }
    if filter_pattern:
        params["filterPattern"] = filter_pattern

    paginator = logs_client.get_paginator("filter_log_events")
    events: list[dict[str, Any]] = []
    for page in paginator.paginate(**params):
        events.extend(page.get("events", []))
    return events
