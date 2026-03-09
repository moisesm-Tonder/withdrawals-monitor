import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
from anthropic import Anthropic
from botocore.exceptions import BotoCoreError, ClientError

from monitor.analysis import generate_analysis_with_claude, generate_fallback_analysis
from monitor.cache import cleanup_cache, load_cache, save_cache
from monitor.classification import classify_error
from monitor.cloudwatch_client import fetch_candidate_events
from monitor.config import load_config, load_dotenv_file
from monitor.logging_setup import configure_runtime
from monitor.parsing import (
    extract_error_message,
    extract_timestamp,
    is_fail_event,
    parse_cloudwatch_message,
)
from monitor.slack_notifier import send_slack_alert
from monitor.types import ErrorRule
from monitor.utils import build_incident_hash, floor_window_start


def run_monitor() -> None:
    load_dotenv_file()
    configure_runtime()
    config = load_config()

    now_utc = datetime.now(timezone.utc)
    window_start = now_utc - timedelta(minutes=config.window_minutes)
    window_bucket_start = floor_window_start(now_utc, window_minutes=config.window_minutes)

    logging.info("Inicio de ejecucion del monitor")
    start_epoch_ms = int(window_start.timestamp() * 1000)
    end_epoch_ms = int(now_utc.timestamp() * 1000)

    logs_client = boto3.client("logs", region_name=config.aws_region)
    try:
        raw_events = fetch_candidate_events(
            logs_client=logs_client,
            log_group_name=config.log_group_name,
            start_epoch_ms=start_epoch_ms,
            end_epoch_ms=end_epoch_ms,
            filter_pattern=config.filter_pattern,
        )
    except (BotoCoreError, ClientError) as exc:
        raise SystemExit(f"Error leyendo CloudWatch Logs: {exc}") from exc

    logging.info("Eventos candidatos leidos: %d", len(raw_events))

    buckets: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"rule": None, "count": 0, "sample_message": ""}
    )
    processed = 0

    for event in raw_events:
        raw_message = str(event.get("message", ""))
        doc = parse_cloudwatch_message(raw_message)
        if not is_fail_event(doc, raw_message):
            continue

        event_ts = extract_timestamp(doc, event.get("timestamp"))
        if not event_ts or event_ts < window_start:
            continue

        message = extract_error_message(doc, raw_message)
        rule = classify_error(message)
        if rule is None:
            continue

        processed += 1
        bucket = buckets[rule.error_type]
        bucket["rule"] = rule
        bucket["count"] += 1
        if not bucket["sample_message"]:
            bucket["sample_message"] = message

    logging.info("Eventos analizados en ventana: %d", processed)

    cache = load_cache(config.cache_file)
    cleanup_cache(cache, now_utc)
    anthropic_client = Anthropic(api_key=config.anthropic_api_key) if config.anthropic_api_key else None
    alerts_sent = 0

    for error_type, payload in buckets.items():
        rule: ErrorRule = payload["rule"]
        count: int = payload["count"]
        if count < rule.min_count:
            continue

        item_hash = build_incident_hash(error_type, window_bucket_start)
        if item_hash in cache:
            logging.info("Alerta duplicada omitida para %s", error_type)
            continue

        sample_message: str = payload["sample_message"]
        if anthropic_client:
            try:
                analysis = generate_analysis_with_claude(
                    anthropic_client,
                    error_type=error_type,
                    severity=rule.severity,
                    occurrences=count,
                    sample_message=sample_message,
                )
            except Exception as exc:
                logging.warning("Fallo analisis con Claude, usando fallback: %s", exc)
                analysis = generate_fallback_analysis(error_type, count)
        else:
            analysis = generate_fallback_analysis(error_type, count)

        send_slack_alert(
            webhook_url=config.slack_webhook_url,
            severity=rule.severity,
            error_type=error_type,
            occurrences=count,
            window_minutes=config.window_minutes,
            analysis=analysis,
        )
        cache[item_hash] = {
            "error_type": error_type,
            "window_start": window_bucket_start.isoformat(),
            "sent_at": now_utc.isoformat(),
        }
        alerts_sent += 1
        logging.info("Alerta enviada: %s (count=%d, severity=%s)", error_type, count, rule.severity)

    save_cache(config.cache_file, cache)
    logging.info("Tipos de error detectados: %s", ", ".join(sorted(buckets.keys())) or "ninguno")
    logging.info("Alertas enviadas: %d", alerts_sent)
