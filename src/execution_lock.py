import json
from datetime import datetime
from pathlib import Path


LOCK_PATH = Path("config/execution_lock.json")


DEFAULT_LOCK = {
    "cms_execution_enabled": False,
    "required_phrase": "ENABLE PAPER EXECUTION",
    "last_updated": None,
}


def ensure_lock_file() -> None:
    if not LOCK_PATH.exists():
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOCK_PATH.write_text(
            json.dumps(DEFAULT_LOCK, indent=2),
            encoding="utf-8",
        )


def load_execution_lock() -> dict:
    ensure_lock_file()

    data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    merged = DEFAULT_LOCK.copy()
    merged.update(data)

    return merged


def save_execution_lock(enabled: bool) -> dict:
    data = load_execution_lock()
    data["cms_execution_enabled"] = bool(enabled)
    data["last_updated"] = datetime.now().isoformat(timespec="seconds")

    LOCK_PATH.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )

    return data


def is_cms_execution_enabled() -> bool:
    data = load_execution_lock()
    return bool(data["cms_execution_enabled"])


def get_required_phrase() -> str:
    data = load_execution_lock()
    return str(data["required_phrase"])
