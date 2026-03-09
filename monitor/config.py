import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_WINDOW_MINUTES = 30
DEFAULT_LOG_GROUP_NAME = "usrv-withdrawals-withdrawals"
DEFAULT_FILTER_PATTERN = '"Failed to create disbursement"'
DEFAULT_CACHE_FILE = ".incident_cache.json"


@dataclass(frozen=True)
class AppConfig:
    slack_webhook_url: str
    aws_region: str
    log_group_name: str
    filter_pattern: str
    window_minutes: int
    anthropic_api_key: str
    cache_file: Path


def load_dotenv_file() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Falta variable de entorno requerida: {name}")
    return value


def load_config() -> AppConfig:
    window_minutes = int(os.getenv("WINDOW_MINUTES", str(DEFAULT_WINDOW_MINUTES)))
    if window_minutes <= 0:
        raise SystemExit("WINDOW_MINUTES debe ser mayor que 0.")

    return AppConfig(
        slack_webhook_url=require_env("SLACK_WEBHOOK_URL"),
        aws_region=require_env("AWS_REGION"),
        log_group_name=os.getenv("LOG_GROUP_NAME", DEFAULT_LOG_GROUP_NAME).strip()
        or DEFAULT_LOG_GROUP_NAME,
        filter_pattern=os.getenv("CLOUDWATCH_FILTER_PATTERN", DEFAULT_FILTER_PATTERN).strip(),
        window_minutes=window_minutes,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        cache_file=Path(os.getenv("INCIDENT_CACHE_FILE", DEFAULT_CACHE_FILE)),
    )
