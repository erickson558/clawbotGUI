from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import re
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = REPO_ROOT / "app_version.py"
CHANGELOG_FILE = REPO_ROOT / "CHANGELOG.md"
VERSION_PATTERN = re.compile(r'APP_VERSION = "(\d+)\.(\d+)\.(\d+)"')


def parse_version(version: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("La versión debe tener formato x.y.z")
    return tuple(int(item) for item in version.split("."))


def format_version(parts: tuple[int, int, int]) -> str:
    return ".".join(str(item) for item in parts)


def bump_version(version: str, level: str) -> str:
    major, minor, patch = parse_version(version)
    if level == "major":
        return format_version((major + 1, 0, 0))
    if level == "minor":
        return format_version((major, minor + 1, 0))
    if level == "patch":
        return format_version((major, minor, patch + 1))
    raise ValueError(f"Nivel de versión no soportado: {level}")


def add_changelog_entry(version: str) -> None:
    content = CHANGELOG_FILE.read_text(encoding="utf-8")
    header = f"## V{version} - {date.today().isoformat()}"
    if header in content:
        return

    prefix = "# Changelog\n\n"
    if not content.startswith(prefix):
        raise RuntimeError("CHANGELOG.md no tiene el encabezado esperado")

    insertion = f"{header}\n\n- Pendiente de documentar cambios.\n\n"
    CHANGELOG_FILE.write_text(content.replace(prefix, prefix + insertion, 1), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Incrementa la versión SemVer y reserva una nueva entrada en CHANGELOG.md."
    )
    parser.add_argument(
        "version",
        nargs="?",
        help="Versión explícita en formato x.y.z. Si no se indica, sube patch por defecto.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--patch", action="store_true", help="Incrementa la versión patch.")
    group.add_argument("--minor", action="store_true", help="Incrementa la versión minor.")
    group.add_argument("--major", action="store_true", help="Incrementa la versión major.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    content = VERSION_FILE.read_text(encoding="utf-8")
    match = VERSION_PATTERN.search(content)
    if not match:
        raise RuntimeError("No se pudo leer APP_VERSION en app_version.py")

    current_version = ".".join(match.groups())
    target_version = current_version

    if args.version:
        target_version = format_version(parse_version(args.version.strip()))
    elif args.major:
        target_version = bump_version(current_version, "major")
    elif args.minor:
        target_version = bump_version(current_version, "minor")
    else:
        target_version = bump_version(current_version, "patch")

    updated = VERSION_PATTERN.sub(f'APP_VERSION = "{target_version}"', content, count=1)
    VERSION_FILE.write_text(updated, encoding="utf-8")
    add_changelog_entry(target_version)
    print(target_version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
