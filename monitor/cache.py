import json
from datetime import datetime, timedelta
from pathlib import Path

from monitor.utils import parse_dt


def load_cache(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return {}


def save_cache(path: Path, cache: dict[str, dict[str, str]]) -> None:
    path.write_text(
        json.dumps(cache, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def cleanup_cache(cache: dict[str, dict[str, str]], now_utc: datetime) -> None:
    cutoff = now_utc - timedelta(hours=24)
    to_remove: list[str] = []
    for item_hash, meta in cache.items():
        sent_at = parse_dt(meta.get("sent_at"))
        if sent_at is None or sent_at < cutoff:
            to_remove.append(item_hash)
    for key in to_remove:
        cache.pop(key, None)
