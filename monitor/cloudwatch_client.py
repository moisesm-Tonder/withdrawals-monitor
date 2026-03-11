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


def fetch_related_execution_events(
    logs_client: Any,
    log_group_name: str,
    log_stream_name: str,
    anchor_timestamp_ms: int | None,
    lambda_request_id: str,
) -> list[dict[str, Any]]:
    if not log_stream_name or anchor_timestamp_ms is None:
        return []

    response = logs_client.get_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        startTime=max(0, anchor_timestamp_ms - 5 * 60 * 1000),
        endTime=anchor_timestamp_ms + 60 * 1000,
        startFromHead=True,
    )
    events = response.get("events", [])
    if not lambda_request_id:
        return events
    return _slice_execution_events(events, lambda_request_id)


def _slice_execution_events(
    events: list[dict[str, Any]], lambda_request_id: str
) -> list[dict[str, Any]]:
    start_token = f"START RequestId: {lambda_request_id}"
    end_token = f"END RequestId: {lambda_request_id}"
    report_token = f"REPORT RequestId: {lambda_request_id}"

    start_index: int | None = None
    for index, event in enumerate(events):
        if start_token in str(event.get("message", "")):
            start_index = index
            break

    if start_index is None:
        return [
            event
            for event in events
            if lambda_request_id in str(event.get("message", ""))
        ]

    end_index: int | None = None
    saw_end = False
    for index in range(start_index, len(events)):
        message = str(events[index].get("message", ""))
        if report_token in message:
            end_index = index
            break
        if end_token in message:
            saw_end = True
            end_index = index
            continue
        if saw_end and message.startswith("REPORT RequestId:"):
            end_index = index
            break
        if index > start_index and message.startswith("START RequestId:"):
            end_index = index - 1
            break

    if end_index is None:
        end_index = min(len(events) - 1, start_index + 25)
    return events[start_index : end_index + 1]
