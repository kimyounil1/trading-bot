import json
from pathlib import Path


CONFIG_PATH = Path("config/notification_config.json")

DEFAULT_CONFIG = {
    "telegram_enabled": True,
    "notify_run_summary": True,
    "notify_orders": True,
    "notify_errors": True,
}


def ensure_notification_config() -> None:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(DEFAULT_CONFIG, indent=2),
            encoding="utf-8",
        )


def load_notification_config() -> dict:
    ensure_notification_config()

    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    merged = DEFAULT_CONFIG.copy()
    merged.update(raw)

    return merged


def save_notification_config(config: dict) -> None:
    merged = DEFAULT_CONFIG.copy()
    merged.update(config)

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def telegram_enabled() -> bool:
    return bool(load_notification_config()["telegram_enabled"])


def run_summary_enabled() -> bool:
    config = load_notification_config()
    return bool(config["telegram_enabled"] and config["notify_run_summary"])


def order_notifications_enabled() -> bool:
    config = load_notification_config()
    return bool(config["telegram_enabled"] and config["notify_orders"])


def error_notifications_enabled() -> bool:
    config = load_notification_config()
    return bool(config["telegram_enabled"] and config["notify_errors"])
