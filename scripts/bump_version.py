from __future__ import annotations

from pathlib import Path
import re
import sys


VERSION_FILE = Path(__file__).resolve().parents[1] / "app_version.py"
VERSION_PATTERN = re.compile(r'APP_VERSION = "(\d+)\.(\d+)\.(\d+)"')


def next_patch(version: str) -> str:
    major, minor, patch = [int(item) for item in version.split(".")]
    return f"{major}.{minor}.{patch + 1}"


def validate(version: str) -> str:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("La versión debe tener formato x.y.z")
    return version


def main() -> int:
    content = VERSION_FILE.read_text(encoding="utf-8")
    match = VERSION_PATTERN.search(content)
    if not match:
        raise RuntimeError("No se pudo leer APP_VERSION en app_version.py")

    current_version = ".".join(match.groups())
    target_version = next_patch(current_version)

    if len(sys.argv) > 1:
        argument = sys.argv[1].strip()
        if argument != "--patch":
            target_version = validate(argument)

    updated = VERSION_PATTERN.sub(f'APP_VERSION = "{target_version}"', content, count=1)
    VERSION_FILE.write_text(updated, encoding="utf-8")
    print(target_version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
