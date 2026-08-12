"""Configuração do command_vision e descoberta básica do ambiente de tela."""

from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path
from typing import Any

VISION_DIR = Path(__file__).resolve().parent
PROJECT_DIR = VISION_DIR.parent
CONFIG_FILE = VISION_DIR / "database_vision.json"
DB_DIR = VISION_DIR / "db"
SQLITE_FILE = DB_DIR / "db_system_vision.db"
CAPTURE_DIR = PROJECT_DIR / "captures"

DEFAULT_CONFIG: dict[str, Any] = {
    "system": {"name": "command_vision", "version": "0.2.0", "log_level": "INFO", "poll_interval_ms": 100, "default_profile_id": None},
    "display": {"monitor_index": 1, "all_screens": False, "width": None, "height": None, "left": 0, "top": 0, "pixel_format": "RGB"},
    "gpu": {"detected": False, "name": None, "vendor": None, "memory_mb": None, "driver": None, "resolution": None, "notes": ""},
    "vision": {"default_tolerance": 20, "minimum_matching_pixels": 1, "capture_format": "png", "capture_directory": "captures"},
    "input": {"keyboard_enabled": True, "joystick_enabled": False, "keyboard_backend": "pyautogui", "joystick_backend": "vgamepad"},
    "aim": {"show": True, "diameter": 120, "border_width": 3, "border_color": "#00ff00", "crosshair": True, "crosshair_width": 1, "crosshair_color": "#ffffff", "opacity": 0.35, "capture_button": "left", "hide_before_capture_ms": 150, "save_capture": True, "capture_name": "aim_capture"},
}


def _merge(base: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    result = {key: value.copy() if isinstance(value, dict) else value for key, value in base.items()}
    for section, section_values in values.items():
        if isinstance(section_values, dict) and isinstance(result.get(section), dict):
            result[section].update(section_values)
        else:
            result[section] = section_values
    return result


def load_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return _merge({}, DEFAULT_CONFIG)
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as file:
            return _merge(DEFAULT_CONFIG, json.load(file))
    except (OSError, json.JSONDecodeError):
        return _merge({}, DEFAULT_CONFIG)


def save_config(config: dict[str, Any]) -> None:
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_directories() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)


def resolve_capture_directory(config: dict[str, Any] | None = None) -> Path:
    current = config or load_config()
    configured = Path(current["vision"].get("capture_directory", "captures"))
    target = configured if configured.is_absolute() else PROJECT_DIR / configured
    target.mkdir(parents=True, exist_ok=True)
    return target


def detect_gpu_and_display() -> dict[str, Any]:
    """Coleta dados disponíveis no Windows sem tornar o sistema dependente deles."""
    config = load_config()
    gpu = config["gpu"]
    gpu["platform"] = platform.platform()
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        config["display"].update({"width": root.winfo_screenwidth(), "height": root.winfo_screenheight()})
        root.destroy()
    except Exception:
        pass
    if platform.system() == "Windows":
        try:
            output = subprocess.check_output(["wmic", "path", "win32_VideoController", "get", "Name,AdapterRAM,DriverVersion"], text=True, stderr=subprocess.DEVNULL)
            lines = [line.strip() for line in output.splitlines() if line.strip()]
            if len(lines) > 1:
                gpu["detected"] = True
                gpu["name"] = lines[1]
        except (OSError, subprocess.SubprocessError):
            pass
    config["gpu"] = gpu
    save_config(config)
    return config
