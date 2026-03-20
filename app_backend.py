from __future__ import annotations

from collections.abc import Callable
import logging
import os
from pathlib import Path
import re
import shlex
import shutil
import socket
import subprocess
import threading
import time
from urllib.parse import urlparse
import webbrowser


CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
PORT_PATTERN = re.compile(r":(\d+)$")
WINDOWS_EXECUTABLE_SUFFIXES = (".cmd", ".bat", ".exe", ".com")
WINDOWS_GATEWAY_TASK_NAME = "OpenClaw Gateway"


class OpenClawService:
    def __init__(
        self,
        logger: logging.Logger,
        settings: dict[str, object],
        console_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.logger = logger
        self.console_callback = console_callback
        self._managed_process_lock = threading.Lock()
        self._managed_gateway_process: subprocess.Popen[str] | None = None
        self.reload_settings(settings)

    def reload_settings(self, settings: dict[str, object]) -> None:
        self.command = str(settings.get("command", "openclaw")).strip()
        self.gateway_port = int(settings.get("gateway_port", 18789))
        self.dashboard_url = str(settings.get("dashboard_url", "http://127.0.0.1:18789")).strip()
        self.browser_url = str(settings.get("browser_url", "http://127.0.0.1:18791")).strip()

    def get_status(self) -> dict[str, object]:
        running = self.is_port_open("127.0.0.1", self.gateway_port)
        if running:
            return {
                "running": True,
                "port": self.gateway_port,
                "pid": self.get_pid_by_port(self.gateway_port),
                "configured_port": self.gateway_port,
                "port_mismatch": False,
            }

        detected_runtime = self._detect_gateway_runtime()
        if detected_runtime is not None:
            actual_port = int(detected_runtime["port"])
            return {
                "running": True,
                "port": actual_port,
                "pid": str(detected_runtime["pid"]),
                "configured_port": self.gateway_port,
                "port_mismatch": actual_port != self.gateway_port,
            }

        return {
            "running": False,
            "port": self.gateway_port,
            "pid": None,
            "configured_port": self.gateway_port,
            "port_mismatch": False,
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
        status = self.get_status()
        if bool(status["running"]):
            actual_port = status["port"]
            self.logger.info("OpenClaw ya parece estar activo en el puerto %s.", actual_port)
            self._emit_console_line(f"OpenClaw ya parece estar activo en el puerto {actual_port}.")
            return
        if os.name == "nt":
            self._start_gateway_windows_managed("Iniciar OpenClaw")
            return
        self._stream_command(self._command_with_args("gateway", "start"), "Iniciar OpenClaw")

    def stop_gateway(self) -> None:
        if os.name == "nt":
            self._stop_gateway_windows_fast()
            return
        self._stream_command(self._command_with_args("gateway", "stop"), "Detener OpenClaw")

    def restart_gateway(self) -> None:
        self.logger.info(">>> Reinicio rápido de OpenClaw")
        try:
            if os.name == "nt":
                self._stop_gateway_windows_fast()
                time.sleep(1)
                self._start_gateway_windows_managed("Reiniciar OpenClaw")
                return

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
        self._terminate_managed_gateway_process()
        if os.name == "nt":
            self._end_windows_task(WINDOWS_GATEWAY_TASK_NAME)
        pids = self._collect_gateway_process_ids()
        if not pids:
            self.logger.info("No hay proceso ocupando el puerto %s.", self.gateway_port)
            self._emit_console_line(f"No hay proceso ocupando el puerto {self.gateway_port}.")
            return
        for pid in sorted(pids):
            self._run_taskkill(pid)
        self.logger.info("Procesos finalizados: %s", ", ".join(sorted(pids)))
        self._emit_console_line(f"Procesos finalizados: {', '.join(sorted(pids))}")

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
        self._emit_console_line(f"$ {' '.join(command)}")
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
            self._emit_console_line(f"ERROR: {exc}")
            return
        except Exception as exc:
            self.logger.exception(">>> ERROR en %s: %s", label, exc)
            self._emit_console_line(f"ERROR: {exc}")
            return

        try:
            if proc.stdout is not None:
                for line in iter(proc.stdout.readline, ""):
                    if line:
                        cleaned = line.rstrip()
                        self.logger.info(cleaned)
                        self._emit_console_line(cleaned)
                proc.stdout.close()
            return_code = proc.wait()
            self.logger.info(">>> %s finalizado con código %s", label, return_code)
            self._emit_console_line(f"[{label}] código de salida: {return_code}")
        except Exception as exc:
            self.logger.exception(">>> ERROR en %s: %s", label, exc)
            self._emit_console_line(f"ERROR: {exc}")

    def _start_gateway_windows_managed(self, label: str) -> None:
        command, env_overrides = self._resolve_windows_gateway_command()
        self.logger.info(">>> %s: %s", label, " ".join(command))
        self._emit_console_line(f"$ {' '.join(command)}")
        self._terminate_managed_gateway_process()
        self._end_windows_task(WINDOWS_GATEWAY_TASK_NAME)

        proc = self._launch_streaming_process(command, label, env_overrides=env_overrides)
        if proc is None:
            return

        self._set_managed_gateway_process(proc)
        threading.Thread(
            target=self._stream_managed_gateway_output,
            args=(proc,),
            daemon=True,
            name="openclaw-managed-output",
        ).start()

        status = self._wait_for_gateway_startup(proc, timeout_seconds=35.0)
        if status is not None:
            self.logger.info(
                ">>> %s listo en puerto %s con PID %s",
                label,
                status["port"],
                status["pid"] or "-",
            )
            self._emit_console_line(
                f"[{label}] gateway activo en puerto {status['port']} (PID {status['pid'] or '-'})"
            )
            return

        exit_code = proc.poll()
        if exit_code is not None:
            self.logger.error(">>> %s terminó antes de quedar en línea con código %s", label, exit_code)
            self._emit_console_line(f"[{label}] terminó antes de quedar en línea: {exit_code}")
            return

        self.logger.warning(">>> %s sigue iniciando, pero aún no respondió en el puerto esperado.", label)
        self._emit_console_line(f"[{label}] sigue iniciando, pero aún no respondió en el puerto esperado.")

    def _resolve_windows_gateway_command(self) -> tuple[list[str], dict[str, str] | None]:
        gateway_script = Path.home() / ".openclaw" / "gateway.cmd"
        if gateway_script.is_file():
            return [str(gateway_script)], None
        return self._command_with_args("gateway", "run", "--force", "--port", str(self.gateway_port)), None

    def _launch_streaming_process(
        self,
        command: list[str],
        label: str,
        env_overrides: dict[str, str] | None = None,
    ) -> subprocess.Popen[str] | None:
        prepared_command = self._prepare_command(command)
        try:
            env = os.environ.copy()
            if env_overrides:
                env.update(env_overrides)
            return subprocess.Popen(
                prepared_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                **self._base_process_kwargs(),
            )
        except FileNotFoundError as exc:
            self.logger.error(">>> ERROR en %s: %s", label, exc)
            self._emit_console_line(f"ERROR: {exc}")
        except Exception as exc:
            self.logger.exception(">>> ERROR en %s: %s", label, exc)
            self._emit_console_line(f"ERROR: {exc}")
        return None

    def _stream_managed_gateway_output(self, proc: subprocess.Popen[str]) -> None:
        try:
            if proc.stdout is not None:
                for line in iter(proc.stdout.readline, ""):
                    if not line:
                        continue
                    cleaned = line.rstrip()
                    self.logger.info(cleaned)
                    self._emit_console_line(cleaned)
                proc.stdout.close()
            return_code = proc.wait()
            self.logger.info(">>> Gateway OpenClaw finalizado con código %s", return_code)
            self._emit_console_line(f"[Gateway OpenClaw] código de salida: {return_code}")
        except Exception as exc:
            self.logger.exception(">>> ERROR leyendo la salida del gateway: %s", exc)
            self._emit_console_line(f"ERROR: {exc}")
        finally:
            self._clear_managed_gateway_process(proc)

    def _wait_for_gateway_startup(
        self,
        proc: subprocess.Popen[str],
        timeout_seconds: float,
    ) -> dict[str, object] | None:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            status = self.get_status()
            if bool(status["running"]):
                return status
            if proc.poll() is not None:
                return None
            time.sleep(0.5)
        status = self.get_status()
        if bool(status["running"]):
            return status
        return None

    def _stop_gateway_windows_fast(self) -> None:
        command = self._command_with_args("gateway", "stop")
        self.logger.info(">>> Detener OpenClaw: %s", " ".join(command))
        self._emit_console_line(f"$ {' '.join(command)}")

        managed_wrapper_stopped = self._terminate_managed_gateway_process()
        if managed_wrapper_stopped:
            self.logger.info(">>> Wrapper oculto del gateway finalizado.")
            self._emit_console_line("Wrapper oculto del gateway finalizado.")

        task_ended = self._end_windows_task(WINDOWS_GATEWAY_TASK_NAME)
        if task_ended:
            self.logger.info(">>> Tarea programada '%s' finalizada.", WINDOWS_GATEWAY_TASK_NAME)
            self._emit_console_line(f"Tarea programada '{WINDOWS_GATEWAY_TASK_NAME}' finalizada.")

        pids = self._collect_gateway_process_ids()
        if pids:
            self.logger.info(">>> Finalizando procesos del gateway: %s", ", ".join(sorted(pids)))
            self._emit_console_line(f"Finalizando procesos del gateway: {', '.join(sorted(pids))}")
            for pid in sorted(pids):
                self._run_taskkill(pid)

        if self._wait_for_gateway_shutdown(timeout_seconds=3.0):
            self.logger.info(">>> Detener OpenClaw finalizado con código 0")
            self._emit_console_line("[Detener OpenClaw] código de salida: 0")
            return

        self.logger.warning(">>> La detención rápida no liberó el gateway. Ejecutando parada estándar...")
        self._emit_console_line("La detención rápida no liberó el gateway. Ejecutando parada estándar...")
        self._stream_command(command, "Detener OpenClaw (respaldo)")

        residual_pids = self._collect_gateway_process_ids()
        if residual_pids:
            self.logger.warning(">>> Persisten procesos del gateway: %s", ", ".join(sorted(residual_pids)))
            self._emit_console_line(f"Persisten procesos del gateway: {', '.join(sorted(residual_pids))}")
            for pid in sorted(residual_pids):
                self._run_taskkill(pid)

        finished = self._wait_for_gateway_shutdown(timeout_seconds=2.0)
        self.logger.info(">>> Detener OpenClaw finalizado con código %s", 0 if finished else 1)
        self._emit_console_line(f"[Detener OpenClaw] código de salida: {0 if finished else 1}")

    def _run_taskkill(self, pid: str) -> None:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
            **self._base_process_kwargs(),
        )

    def _end_windows_task(self, task_name: str) -> bool:
        if os.name != "nt":
            return False

        completed = subprocess.run(
            ["schtasks", "/End", "/TN", task_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
            **self._base_process_kwargs(),
        )
        return completed.returncode == 0

    def _collect_gateway_process_ids(self) -> set[str]:
        pids: set[str] = set()
        pid = self.get_pid_by_port(self.gateway_port)
        if pid:
            pids.add(pid)
        if os.name == "nt":
            pids.update({item["pid"] for item in self._find_gateway_processes()})
        return pids

    def _find_gateway_processes(self) -> list[dict[str, str | int | None]]:
        if os.name != "nt":
            return []

        script = rf"""
$pattern = 'node_modules\\openclaw\\dist\\index\.js gateway'
Get-CimInstance Win32_Process |
    Where-Object {{
        $_.Name -eq 'node.exe' -and
        $_.CommandLine -match $pattern
    }} |
    ForEach-Object {{
        $port = ''
        if ($_.CommandLine -match '--port\s+(\d+)') {{
            $port = $matches[1]
        }}
        '{{0}}|{{1}}' -f $_.ProcessId, $port
    }}
"""
        try:
            output = subprocess.check_output(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                text=True,
                stderr=subprocess.STDOUT,
                timeout=10,
                **self._base_process_kwargs(),
            )
        except (OSError, subprocess.SubprocessError):
            return []

        processes: list[dict[str, str | int | None]] = []
        for raw_line in output.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            pid_text, _, port_text = line.partition("|")
            if not pid_text.isdigit():
                continue
            processes.append(
                {
                    "pid": pid_text,
                    "port": int(port_text) if port_text.isdigit() else None,
                }
            )
        return processes

    def _detect_gateway_runtime(self) -> dict[str, str | int] | None:
        for process in self._find_gateway_processes():
            port = process.get("port")
            pid = process.get("pid")
            if port is None or pid is None:
                continue
            if self.is_port_open("127.0.0.1", int(port)):
                return {
                    "pid": str(pid),
                    "port": int(port),
                }
        return None

    def _wait_for_gateway_shutdown(self, timeout_seconds: float) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if not self._collect_gateway_process_ids() and not self.is_port_open("127.0.0.1", self.gateway_port):
                return True
            time.sleep(0.2)
        return not self._collect_gateway_process_ids() and not self.is_port_open("127.0.0.1", self.gateway_port)

    def _set_managed_gateway_process(self, proc: subprocess.Popen[str]) -> None:
        with self._managed_process_lock:
            self._managed_gateway_process = proc

    def _clear_managed_gateway_process(self, proc: subprocess.Popen[str] | None = None) -> None:
        with self._managed_process_lock:
            if proc is None or self._managed_gateway_process is proc:
                self._managed_gateway_process = None

    def _terminate_managed_gateway_process(self) -> bool:
        with self._managed_process_lock:
            proc = self._managed_gateway_process
            self._managed_gateway_process = None

        if proc is None or proc.poll() is not None:
            return False

        try:
            proc.terminate()
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        except OSError:
            return False
        return True

    def _emit_console_line(self, text: str) -> None:
        if not text or self.console_callback is None:
            return
        try:
            self.console_callback(text.rstrip())
        except Exception:
            self.logger.debug("No se pudo enviar salida a la consola embebida.", exc_info=True)

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
