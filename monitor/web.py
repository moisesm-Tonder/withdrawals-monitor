import logging
import os
import threading
import time
from datetime import datetime, timezone

from flask import Flask, jsonify, request

from monitor.logging_setup import configure_runtime
from monitor.runner import run_monitor

app = Flask(__name__)
_run_lock = threading.Lock()
_scheduler_started = False


def _run_once() -> str:
    if not _run_lock.acquire(blocking=False):
        return "already_running"
    try:
        run_monitor()
        return "ok"
    except SystemExit as exc:
        raise RuntimeError(str(exc)) from exc
    finally:
        _run_lock.release()


def _scheduler_loop(interval_seconds: int) -> None:
    while True:
        try:
            status = _run_once()
            logging.info("Scheduler run completed with status: %s", status)
        except Exception:
            logging.exception("Scheduler run failed")
        time.sleep(interval_seconds)


def _maybe_start_scheduler() -> None:
    global _scheduler_started
    if _scheduler_started:
        return

    enabled = os.getenv("ENABLE_SCHEDULER", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not enabled:
        logging.info("Scheduler is disabled by ENABLE_SCHEDULER")
        _scheduler_started = True
        return

    interval_minutes = int(os.getenv("SCHEDULE_EVERY_MINUTES", "5"))
    if interval_minutes <= 0:
        interval_minutes = 5

    thread = threading.Thread(
        target=_scheduler_loop,
        args=(interval_minutes * 60,),
        daemon=True,
        name="withdrawals-monitor-scheduler",
    )
    thread.start()
    _scheduler_started = True
    logging.info("Scheduler started (every %d minutes)", interval_minutes)


@app.get("/")
def root() -> tuple[dict[str, str], int]:
    return {"service": "withdrawals-monitor", "status": "running"}, 200


@app.get("/health")
def health() -> tuple[dict[str, str], int]:
    return {
        "status": "ok",
        "service": "withdrawals-monitor",
        "time_utc": datetime.now(timezone.utc).isoformat(),
    }, 200


@app.post("/run")
def run_now():
    expected_token = os.getenv("RUN_TRIGGER_TOKEN", "").strip()
    if expected_token:
        provided_token = request.headers.get("X-Run-Token", "").strip()
        if provided_token != expected_token:
            return jsonify({"status": "unauthorized"}), 401

    try:
        status = _run_once()
        status_code = 200 if status == "ok" else 202
        return jsonify({"status": status}), status_code
    except Exception as exc:
        logging.exception("Manual run failed")
        return jsonify({"status": "error", "message": str(exc)}), 500


configure_runtime()
_maybe_start_scheduler()
