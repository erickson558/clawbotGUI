from __future__ import annotations

import logging
import os
from pathlib import Path
import re
import shlex
import shutil
import socket
import subprocess
import time
from urllib.parse import urlparse
import webbrowser


CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
PORT_PATTERN = re.compile(r":(\d+)$")
WINDOWS_EXECUTABLE_SUFFIXES = (".cmd", ".bat", ".exe", ".com")


class OpenClawService:
    def __init__(self, logger: logging.Logger, settings: dict[str, object]) -> None:
        self.logger = logger
        self.reload_settings(settings)

    def reload_settings(self, settings: dict[str, object]) -> None:
        self.command = str(settings.get("command", "openclaw")).strip()
        self.gateway_port = int(settings.get("gateway_port", 18789))
        self.dashboard_url = str(settings.get("dashboard_url", "http://127.0.0.1:18789")).strip()
        self.browser_url = str(settings.get("browser_url", "http://127.0.0.1:18791")).strip()

    def get_status(self) -> dict[str, object]:
        running = self.is_port_open("127.0.0.1", self.gateway_port)
        return {
            "running": running,
            "port": self.gateway_port,
            "pid": self.get_pid_by_port(self.gateway_port) if running else None,
        }

    def is_port_open(self, host: str, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.35)
            return sock.connect_ex((host, int(port))) == 0

    def get_pid_by_port(self, port: int) -> str | None:
        try:
            output = subprocess.check_output(
                ["netstat", "-ano", "-p", "tcp"],
                text=True,
                stderr=subprocess.STDOUT,
                timeout=10,
                **self._base_process_kwargs(),
            )
        except (OSError, subprocess.SubprocessError):
            return None

        for line in output.splitlines():
            parts = line.split()
            if len(parts) < 5:
                continue
            if self._extract_port(parts[1]) != port:
                continue
            return parts[-1]
        return None

    def start_gateway(self) -> None:
        if self.is_port_open("127.0.0.1", self.gateway_port):
            self.logger.info("OpenClaw ya parece estar activo.")
            return
        self._stream_command(self._command_with_args("gateway", "start"), "Iniciar OpenClaw")

    def stop_gateway(self) -> None:
        self._stream_command(self._command_with_args("gateway", "stop"), "Detener OpenClaw")

    def restart_gateway(self) -> None:
        self.logger.info(">>> Reinicio rápido de OpenClaw")
        try:
            stop_command = self._prepare_command(self._command_with_args("gateway", "stop"))
            subprocess.run(
                stop_command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=20,
                check=False,
                **self._base_process_kwargs(),
            )
            time.sleep(2)
            pid = self.get_pid_by_port(self.gateway_port)
            if pid:
                self.logger.info(
                    ">>> Puerto %s ocupado por PID %s. Finalizando proceso...",
                    self.gateway_port,
                    pid,
                )
                self._run_taskkill(pid)
                time.sleep(1)
            self._stream_command(self._command_with_args("gateway", "start"), "Reiniciar OpenClaw")
        except Exception as exc:
            self.logger.exception(">>> ERROR al reiniciar: %s", exc)

    def kill_gateway_process(self) -> None:
        pid = self.get_pid_by_port(self.gateway_port)
        if not pid:
            self.logger.info("No hay proceso ocupando el puerto %s.", self.gateway_port)
            return
        self._run_taskkill(pid)
        self.logger.info("Proceso PID %s finalizado.", pid)

    def open_dashboard(self) -> None:
        if not self._is_safe_http_url(self.dashboard_url):
            self.logger.error("La URL configurada no es válida: %s", self.dashboard_url)
            return
        webbrowser.open(self.dashboard_url, new=0, autoraise=True)
        self.logger.info("Abriendo Dashboard: %s", self.dashboard_url)

    def open_browser_ui(self) -> None:
        if not self._is_safe_http_url(self.browser_url):
            self.logger.error("La URL configurada no es válida: %s", self.browser_url)
            return
        webbrowser.open(self.browser_url, new=0, autoraise=True)
        self.logger.info("Abriendo Browser UI: %s", self.browser_url)

    def _command_with_args(self, *extra_args: str) -> list[str]:
        base = shlex.split(self.command, posix=os.name != "nt")
        if not base:
            raise ValueError("El comando OpenClaw no es válido.")
        base[0] = self._resolve_executable(base[0])
        return base + list(extra_args)

    def _resolve_executable(self, executable: str) -> str:
        candidate = executable.strip().strip('"')
        if not candidate:
            raise ValueError("El ejecutable configurado está vacío.")

        expanded = Path(os.path.expandvars(os.path.expanduser(candidate)))

        direct_match = self._find_local_executable(expanded)
        if direct_match is not None:
            return str(direct_match)

        path_match = shutil.which(candidate)
        if path_match:
            return path_match

        if os.name == "nt" and expanded.suffix == "":
            for suffix in WINDOWS_EXECUTABLE_SUFFIXES:
                path_match = shutil.which(candidate + suffix)
                if path_match:
                    return path_match

        raise FileNotFoundError(
            "No se encontró el ejecutable configurado. "
            f"Valor actual: '{self.command}'. "
            "En Windows, si OpenClaw fue instalado con npm, la app intentará resolver "
            "automáticamente 'openclaw.cmd'. Si sigue fallando, configura la ruta completa "
            "del ejecutable en el campo 'Comando OpenClaw'."
        )

    @staticmethod
    def _find_local_executable(candidate: Path) -> Path | None:
        if candidate.is_file():
            return candidate.resolve()

        if os.name != "nt" or candidate.suffix:
            return None

        for suffix in WINDOWS_EXECUTABLE_SUFFIXES:
            suffixed = candidate.with_suffix(suffix)
            if suffixed.is_file():
                return suffixed.resolve()
        return None

    def _stream_command(self, command: list[str], label: str) -> None:
        self.logger.info(">>> %s: %s", label, " ".join(command))
        prepared_command = self._prepare_command(command)
        try:
            proc = subprocess.Popen(
                prepared_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                **self._base_process_kwargs(),
            )
        except FileNotFoundError as exc:
            self.logger.error(">>> ERROR en %s: %s", label, exc)
            return
        except Exception as exc:
            self.logger.exception(">>> ERROR en %s: %s", label, exc)
            return

        try:
            if proc.stdout is not None:
                for line in iter(proc.stdout.readline, ""):
                    if line:
                        self.logger.info(line.rstrip())
                proc.stdout.close()
            return_code = proc.wait()
            self.logger.info(">>> %s finalizado con código %s", label, return_code)
        except Exception as exc:
            self.logger.exception(">>> ERROR en %s: %s", label, exc)

    def _run_taskkill(self, pid: str) -> None:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
            **self._base_process_kwargs(),
        )

    def _prepare_command(self, command: list[str]) -> list[str]:
        if os.name != "nt":
            return command

        suffix = Path(command[0]).suffix.lower()
        if suffix not in {".cmd", ".bat"}:
            return command

        return ["cmd.exe", "/d", "/s", "/c", subprocess.list2cmdline(command)]

    @staticmethod
    def _base_process_kwargs() -> dict[str, object]:
        kwargs: dict[str, object] = {
            "stdin": subprocess.DEVNULL,
            "shell": False,
        }
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            kwargs["startupinfo"] = startupinfo
            kwargs["creationflags"] = CREATE_NO_WINDOW
        return kwargs

    @staticmethod
    def _extract_port(address: str) -> int | None:
        cleaned = address.strip()
        if cleaned.startswith("[") and "]:" in cleaned:
            cleaned = cleaned.rsplit("]:", 1)[-1]
            try:
                return int(cleaned)
            except ValueError:
                return None

        match = PORT_PATTERN.search(cleaned)
        if not match:
            return None
        try:
            return int(match.group(1))
        except ValueError:
            return None

    @staticmethod
    def _is_safe_http_url(value: str) -> bool:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
