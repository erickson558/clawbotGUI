from pathlib import Path
import sys


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = get_app_dir()
CONFIG_PATH = APP_DIR / "config.json"
LOG_PATH = APP_DIR / "log.txt"

_icon_candidates = sorted(APP_DIR.glob("*.ico"))
ICON_PATH = _icon_candidates[0] if _icon_candidates else APP_DIR / "clawbotGUI.ico"
