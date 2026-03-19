from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import re
import shutil
import threading
from typing import Any


DEFAULT_CONFIG = {
    "language": "es",
    "window": {
        "geometry": "1220x780+80+60",
        "remember_position": True,
    },
    "behavior": {
        "auto_start_enabled": False,
        "auto_close_enabled": False,
        "auto_close_seconds": 60,
        "refresh_interval_ms": 2000,
    },
    "openclaw": {
        "command": "openclaw",
        "gateway_port": 18789,
        "dashboard_url": "http://127.0.0.1:18789",
        "browser_url": "http://127.0.0.1:18791",
    },
}

GEOMETRY_PATTERN = re.compile(r"^\d+x\d+[+-]\d+[+-]\d+$")


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def clamp_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(number, maximum))


def coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def clean_text(value: Any, default: str, max_length: int) -> str:
    if not isinstance(value, str):
        return default
    cleaned = value.strip()
    if not cleaned:
        return default
    return cleaned[:max_length]


def clean_geometry(value: Any, default: str) -> str:
    if isinstance(value, str) and GEOMETRY_PATTERN.match(value.strip()):
        return value.strip()
    return default


def sanitize_config(data: dict[str, Any]) -> dict[str, Any]:
    sanitized = deep_merge(DEFAULT_CONFIG, data or {})

    sanitized["language"] = clean_text(sanitized.get("language"), DEFAULT_CONFIG["language"], 8)
    if sanitized["language"] not in {"es", "en"}:
        sanitized["language"] = DEFAULT_CONFIG["language"]

    window = sanitized.setdefault("window", {})
    window["geometry"] = clean_geometry(window.get("geometry"), DEFAULT_CONFIG["window"]["geometry"])
    window["remember_position"] = coerce_bool(
        window.get("remember_position"),
        DEFAULT_CONFIG["window"]["remember_position"],
    )

    behavior = sanitized.setdefault("behavior", {})
    behavior["auto_start_enabled"] = coerce_bool(
        behavior.get("auto_start_enabled"),
        DEFAULT_CONFIG["behavior"]["auto_start_enabled"],
    )
    behavior["auto_close_enabled"] = coerce_bool(
        behavior.get("auto_close_enabled"),
        DEFAULT_CONFIG["behavior"]["auto_close_enabled"],
    )
    behavior["auto_close_seconds"] = clamp_int(
        behavior.get("auto_close_seconds"),
        DEFAULT_CONFIG["behavior"]["auto_close_seconds"],
        5,
        86400,
    )
    behavior["refresh_interval_ms"] = clamp_int(
        behavior.get("refresh_interval_ms"),
        DEFAULT_CONFIG["behavior"]["refresh_interval_ms"],
        500,
        60000,
    )

    openclaw = sanitized.setdefault("openclaw", {})
    openclaw["command"] = clean_text(openclaw.get("command"), DEFAULT_CONFIG["openclaw"]["command"], 512)
    openclaw["gateway_port"] = clamp_int(
        openclaw.get("gateway_port"),
        DEFAULT_CONFIG["openclaw"]["gateway_port"],
        1,
        65535,
    )
    openclaw["dashboard_url"] = clean_text(
        openclaw.get("dashboard_url"),
        DEFAULT_CONFIG["openclaw"]["dashboard_url"],
        2048,
    )
    openclaw["browser_url"] = clean_text(
        openclaw.get("browser_url"),
        DEFAULT_CONFIG["openclaw"]["browser_url"],
        2048,
    )

    return sanitized


class ConfigManager:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.lock = threading.RLock()
        self.recovery_notes: list[str] = []
        self.data = self.load()

    def load(self) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            data = sanitize_config(deepcopy(DEFAULT_CONFIG))
            self._write(data)
            self.recovery_notes.append("Se creó config.json con valores predeterminados.")
            return data

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_path = self.path.with_suffix(f".invalid-{stamp}.json")
            try:
                shutil.move(str(self.path), str(backup_path))
            except OSError:
                backup_path = None
            data = sanitize_config(deepcopy(DEFAULT_CONFIG))
            self._write(data)
            if backup_path:
                self.recovery_notes.append(
                    f"Config inválida detectada. Respaldo creado en {backup_path.name}."
                )
            else:
                self.recovery_notes.append("Config inválida detectada. Se restauró la configuración segura.")
            return data

        data = sanitize_config(raw if isinstance(raw, dict) else {})
        self._write(data)
        return data

    def export(self) -> dict[str, Any]:
        with self.lock:
            return deepcopy(self.data)

    def update(self, patch: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.data = sanitize_config(deep_merge(self.data, patch))
            self._write(self.data)
            return deepcopy(self.data)

    def _write(self, payload: dict[str, Any]) -> None:
        temp_path = self.path.with_suffix(".json.tmp")
        serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        temp_path.write_text(serialized + "\n", encoding="utf-8")
        temp_path.replace(self.path)
