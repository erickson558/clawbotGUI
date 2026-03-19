from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
import tkinter.scrolledtext as scrolledtext
from tkinter import ttk
from typing import Callable

from app_backend import OpenClawService
from app_config import ConfigManager
from app_i18n import LANGUAGE_LABELS, Translator
from app_paths import CONFIG_PATH, ICON_PATH, LOG_PATH
from app_logging import configure_logging
from app_version import APP_NAME, APP_VERSION_TAG, COPYRIGHT_YEAR


class AboutDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, title: str, message: str, close_text: str) -> None:
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.configure(bg="#0A1420")
        self.resizable(False, False)

        container = tk.Frame(self, bg="#F7FBFF", padx=22, pady=22)
        container.pack(fill="both", expand=True, padx=18, pady=18)

        tk.Label(
            container,
            text=title,
            bg="#F7FBFF",
            fg="#0E2B47",
            font=("Segoe UI Semibold", 14),
        ).pack(anchor="w")

        tk.Label(
            container,
            text=message,
            bg="#F7FBFF",
            fg="#26415C",
            font=("Segoe UI", 11),
            justify="left",
            wraplength=360,
            pady=12,
        ).pack(anchor="w")

        ttk.Button(container, text=close_text, command=self.destroy, style="Accent.TButton").pack(anchor="e", pady=(8, 0))

        self.bind("<Escape>", lambda _event: self.destroy())
        self.after(50, self._center_on_parent)

    def _center_on_parent(self) -> None:
        self.update_idletasks()
        parent = self.master
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{max(x, 20)}+{max(y, 20)}")


class OpenClawManagerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.configure(bg="#08131D")
        self.root.minsize(1120, 720)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.config_manager = ConfigManager(CONFIG_PATH)
        self.config = self.config_manager.export()
        self.translator = Translator(self.config["language"])
        self.logger = configure_logging(LOG_PATH, self.log_queue)
        self.service = OpenClawService(self.logger, self.config["openclaw"])

        self._loading_ui = True
        self._closing = False
        self._save_after_id: str | None = None
        self._geometry_after_id: str | None = None
        self._countdown_after_id: str | None = None
        self._status_poll_after_id: str | None = None
        self._status_refresh_in_progress = False
        self._countdown_remaining: int | None = None

        self._build_variables()
        self._configure_styles()
        self._apply_window_settings()
        self._build_ui()
        self._bind_shortcuts()
        self._load_values_into_ui()
        self._render_texts()

        self._loading_ui = False
        for note in self.config_manager.recovery_notes:
            self.logger.warning(note)

        self.logger.info("Aplicación iniciada en %s", LOG_PATH)
        self.set_status_message(self.tr("status_ready"))
        self._process_log_queue()
        self._start_status_poll_loop()
        self._restart_auto_close_timer()

        if self.auto_start_var.get():
            self.root.after(900, self.start_openclaw)

    def tr(self, key: str, **kwargs) -> str:
        return self.translator.tr(key, **kwargs)

    def _build_variables(self) -> None:
        self.command_var = tk.StringVar()
        self.port_var = tk.StringVar()
        self.dashboard_var = tk.StringVar()
        self.browser_var = tk.StringVar()
        self.language_var = tk.StringVar()
        self.auto_start_var = tk.BooleanVar()
        self.auto_close_var = tk.BooleanVar()
        self.auto_close_seconds_var = tk.StringVar()
        self.refresh_interval_var = tk.StringVar()
        self.remember_position_var = tk.BooleanVar()

        self.runtime_status_var = tk.StringVar(value=self.tr("status_checking"))
        self.runtime_pid_var = tk.StringVar(value="-")
        self.runtime_port_var = tk.StringVar(value="-")
        self.version_var = tk.StringVar(value=APP_VERSION_TAG)
        self.status_bar_var = tk.StringVar(value=self.tr("status_ready"))
        self.countdown_var = tk.StringVar(value=self.tr("countdown_disabled"))

    def _configure_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Accent.TButton", font=("Segoe UI Semibold", 10), padding=(14, 10))
        style.configure("Neutral.TButton", font=("Segoe UI Semibold", 10), padding=(14, 10))
        style.configure("Danger.TButton", font=("Segoe UI Semibold", 10), padding=(14, 10))
        style.configure("Modern.TCheckbutton", background="#F7FBFF", font=("Segoe UI", 10))

    def _apply_window_settings(self) -> None:
        self.root.title(f"{APP_NAME} {APP_VERSION_TAG}")
        self.root.geometry(self.config["window"]["geometry"])
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.root.bind("<Configure>", self._on_root_configure)
        if ICON_PATH.exists():
            try:
                self.root.iconbitmap(ICON_PATH)
            except tk.TclError:
                self.logger.debug("No se pudo aplicar el icono %s", ICON_PATH)

    def _build_ui(self) -> None:
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        self.banner_canvas = tk.Canvas(
            self.root,
            height=132,
            bg="#08131D",
            highlightthickness=0,
            bd=0,
        )
        self.banner_canvas.grid(row=0, column=0, sticky="ew")
        self.banner_canvas.create_oval(-60, -40, 240, 200, fill="#103B5F", outline="")
        self.banner_canvas.create_oval(800, -70, 1180, 180, fill="#17A2B8", outline="")
        self.banner_title_item = self.banner_canvas.create_text(
            34,
            34,
            anchor="nw",
            fill="#F7FBFF",
            font=("Segoe UI Semibold", 28),
            text="",
        )
        self.banner_subtitle_item = self.banner_canvas.create_text(
            36,
            78,
            anchor="nw",
            fill="#C8E3FF",
            font=("Segoe UI", 12),
            text="",
        )
        self.banner_version_item = self.banner_canvas.create_text(
            1010,
            40,
            anchor="ne",
            fill="#F7FBFF",
            font=("Consolas", 12, "bold"),
            text=APP_VERSION_TAG,
        )

        content = tk.Frame(self.root, bg="#08131D", padx=18, pady=18)
        content.grid(row=1, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=1, uniform="content")
        content.grid_columnconfigure(1, weight=1, uniform="content")
        content.grid_rowconfigure(0, weight=0)
        content.grid_rowconfigure(1, weight=1)

        self.controls_card = self._make_card(content)
        self.controls_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        for column_index in range(3):
            self.controls_card.grid_columnconfigure(column_index, weight=1)

        self.controls_title = self._card_title(self.controls_card)
        self.controls_title.grid(row=0, column=0, columnspan=3, sticky="w")

        self.start_button = ttk.Button(self.controls_card, command=self.start_openclaw, style="Accent.TButton")
        self.stop_button = ttk.Button(self.controls_card, command=self.stop_openclaw, style="Neutral.TButton")
        self.restart_button = ttk.Button(self.controls_card, command=self.restart_openclaw, style="Neutral.TButton")
        self.refresh_button = ttk.Button(self.controls_card, command=lambda: self.refresh_status_async(True), style="Neutral.TButton")
        self.dashboard_button = ttk.Button(self.controls_card, command=self.open_dashboard, style="Neutral.TButton")
        self.browser_button = ttk.Button(self.controls_card, command=self.open_browser_ui, style="Neutral.TButton")
        self.kill_button = ttk.Button(self.controls_card, command=self.kill_port_process, style="Danger.TButton")
        self.clear_log_button = ttk.Button(self.controls_card, command=self.clear_log, style="Neutral.TButton")
        self.exit_button = ttk.Button(self.controls_card, command=self.on_exit, style="Danger.TButton")

        buttons = [
            self.start_button,
            self.stop_button,
            self.restart_button,
            self.refresh_button,
            self.dashboard_button,
            self.browser_button,
            self.kill_button,
            self.clear_log_button,
            self.exit_button,
        ]
        for index, button in enumerate(buttons, start=1):
            row = ((index - 1) // 3) + 1
            column = (index - 1) % 3
            button.grid(row=row, column=column, sticky="ew", padx=5, pady=5)

        self.shortcuts_title = self._card_subtitle(self.controls_card)
        self.shortcuts_title.grid(row=4, column=0, sticky="w", pady=(12, 0))
        self.shortcuts_label = tk.Label(
            self.controls_card,
            bg="#F7FBFF",
            fg="#35506A",
            font=("Segoe UI", 9),
            justify="left",
            anchor="w",
            wraplength=520,
        )
        self.shortcuts_label.grid(row=5, column=0, columnspan=3, sticky="ew")

        self.settings_card = self._make_card(content)
        self.settings_card.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        self.settings_card.grid_columnconfigure(1, weight=1)
        self.settings_title = self._card_title(self.settings_card)
        self.settings_title.grid(row=0, column=0, columnspan=2, sticky="w")

        self.command_label = self._field_label(self.settings_card)
        self.command_entry = ttk.Entry(self.settings_card, textvariable=self.command_var)
        self.port_label = self._field_label(self.settings_card)
        self.port_spinbox = ttk.Spinbox(
            self.settings_card,
            from_=1,
            to=65535,
            textvariable=self.port_var,
            validate="key",
            validatecommand=(self.root.register(self._validate_numeric), "%P"),
        )
        self.dashboard_label = self._field_label(self.settings_card)
        self.dashboard_entry = ttk.Entry(self.settings_card, textvariable=self.dashboard_var)
        self.browser_label = self._field_label(self.settings_card)
        self.browser_entry = ttk.Entry(self.settings_card, textvariable=self.browser_var)
        self.language_label = self._field_label(self.settings_card)
        self.language_combo = ttk.Combobox(
            self.settings_card,
            textvariable=self.language_var,
            values=list(LANGUAGE_LABELS.values()),
            state="readonly",
        )
        self.auto_start_check = ttk.Checkbutton(self.settings_card, variable=self.auto_start_var, style="Modern.TCheckbutton")
        self.auto_close_check = ttk.Checkbutton(self.settings_card, variable=self.auto_close_var, style="Modern.TCheckbutton")
        self.auto_close_seconds_label = self._field_label(self.settings_card)
        self.auto_close_spinbox = ttk.Spinbox(
            self.settings_card,
            from_=5,
            to=86400,
            textvariable=self.auto_close_seconds_var,
            validate="key",
            validatecommand=(self.root.register(self._validate_numeric), "%P"),
        )
        self.refresh_interval_label = self._field_label(self.settings_card)
        self.refresh_interval_spinbox = ttk.Spinbox(
            self.settings_card,
            from_=500,
            to=60000,
            increment=100,
            textvariable=self.refresh_interval_var,
            validate="key",
            validatecommand=(self.root.register(self._validate_numeric), "%P"),
        )
        self.remember_position_check = ttk.Checkbutton(
            self.settings_card,
            variable=self.remember_position_var,
            style="Modern.TCheckbutton",
        )

        setting_rows = [
            (self.command_label, self.command_entry),
            (self.port_label, self.port_spinbox),
            (self.dashboard_label, self.dashboard_entry),
            (self.browser_label, self.browser_entry),
            (self.language_label, self.language_combo),
            (None, self.auto_start_check),
            (None, self.auto_close_check),
            (self.auto_close_seconds_label, self.auto_close_spinbox),
            (self.refresh_interval_label, self.refresh_interval_spinbox),
            (None, self.remember_position_check),
        ]
        for row_index, (label, widget) in enumerate(setting_rows, start=1):
            if label is not None:
                label.grid(row=row_index, column=0, sticky="w", padx=(0, 10), pady=6)
                widget.grid(row=row_index, column=1, sticky="ew", pady=6)
            else:
                widget.grid(row=row_index, column=0, columnspan=2, sticky="w", pady=6)

        right_panel = tk.Frame(content, bg="#08131D")
        right_panel.grid(row=0, column=1, rowspan=2, sticky="nsew")
        right_panel.grid_rowconfigure(1, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        self.runtime_card = self._make_card(right_panel)
        self.runtime_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.runtime_card.grid_columnconfigure(1, weight=1)
        self.runtime_title = self._card_title(self.runtime_card)
        self.runtime_title.grid(row=0, column=0, columnspan=2, sticky="w")

        self.app_status_label = self._field_label(self.runtime_card)
        self.app_status_value = self._value_label(self.runtime_card, self.runtime_status_var)
        self.port_runtime_label = self._field_label(self.runtime_card)
        self.port_runtime_value = self._value_label(self.runtime_card, self.runtime_port_var)
        self.pid_label = self._field_label(self.runtime_card)
        self.pid_value = self._value_label(self.runtime_card, self.runtime_pid_var)
        self.version_label = self._field_label(self.runtime_card)
        self.version_value = self._value_label(self.runtime_card, self.version_var)

        runtime_rows = [
            (self.app_status_label, self.app_status_value),
            (self.port_runtime_label, self.port_runtime_value),
            (self.pid_label, self.pid_value),
            (self.version_label, self.version_value),
        ]
        for row_index, (label, value) in enumerate(runtime_rows, start=1):
            label.grid(row=row_index, column=0, sticky="w", padx=(0, 12), pady=6)
            value.grid(row=row_index, column=1, sticky="w", pady=6)

        self.log_card = self._make_card(right_panel)
        self.log_card.grid(row=1, column=0, sticky="nsew")
        self.log_card.grid_rowconfigure(1, weight=1)
        self.log_card.grid_columnconfigure(0, weight=1)

        self.log_title = self._card_title(self.log_card)
        self.log_title.grid(row=0, column=0, sticky="w")
        self.log_text = scrolledtext.ScrolledText(
            self.log_card,
            wrap="word",
            font=("Consolas", 10),
            background="#07111A",
            foreground="#DDEBFF",
            insertbackground="#F7FBFF",
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=12,
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self.log_text.configure(state="disabled")

        self.status_bar = tk.Frame(self.root, bg="#061018", padx=12, pady=8)
        self.status_bar.grid(row=2, column=0, sticky="ew")
        self.status_bar.grid_columnconfigure(0, weight=1)

        tk.Label(
            self.status_bar,
            textvariable=self.status_bar_var,
            bg="#061018",
            fg="#E5F0FF",
            font=("Segoe UI", 10),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")

        tk.Label(
            self.status_bar,
            textvariable=self.countdown_var,
            bg="#061018",
            fg="#87C4FF",
            font=("Consolas", 10, "bold"),
            anchor="e",
        ).grid(row=0, column=1, sticky="e")

        self._build_menu()
        self._register_variable_handlers()

    def _make_card(self, parent: tk.Widget) -> tk.Frame:
        return tk.Frame(parent, bg="#F7FBFF", highlightbackground="#D3E3F5", highlightthickness=1, bd=0, padx=18, pady=18)

    def _card_title(self, parent: tk.Widget) -> tk.Label:
        return tk.Label(parent, bg="#F7FBFF", fg="#0E2B47", font=("Segoe UI Semibold", 14))

    def _card_subtitle(self, parent: tk.Widget) -> tk.Label:
        return tk.Label(parent, bg="#F7FBFF", fg="#1F4E79", font=("Segoe UI Semibold", 10))

    def _field_label(self, parent: tk.Widget) -> tk.Label:
        return tk.Label(parent, bg="#F7FBFF", fg="#35506A", font=("Segoe UI", 10))

    def _value_label(self, parent: tk.Widget, variable: tk.StringVar) -> tk.Label:
        return tk.Label(parent, textvariable=variable, bg="#F7FBFF", fg="#10273D", font=("Consolas", 11, "bold"))

    def _build_menu(self) -> None:
        self.menu_bar = tk.Menu(self.root)
        file_menu = tk.Menu(self.menu_bar, tearoff=False)
        help_menu = tk.Menu(self.menu_bar, tearoff=False)

        file_menu.add_command(label=self.tr("menu_start"), command=self.start_openclaw, accelerator="Alt+I")
        file_menu.add_command(label=self.tr("menu_stop"), command=self.stop_openclaw, accelerator="Alt+D")
        file_menu.add_command(label=self.tr("menu_restart"), command=self.restart_openclaw, accelerator="Alt+R")
        file_menu.add_separator()
        file_menu.add_command(label=self.tr("menu_refresh"), command=lambda: self.refresh_status_async(True), accelerator="F5")
        file_menu.add_command(label=self.tr("menu_dashboard"), command=self.open_dashboard)
        file_menu.add_command(label=self.tr("menu_browser"), command=self.open_browser_ui)
        file_menu.add_command(label=self.tr("menu_release_port"), command=self.kill_port_process)
        file_menu.add_command(label=self.tr("menu_clear_log"), command=self.clear_log, accelerator="Ctrl+L")
        file_menu.add_separator()
        file_menu.add_command(label=self.tr("menu_exit"), command=self.on_exit, accelerator="Alt+X")

        help_menu.add_command(label=self.tr("menu_about"), command=self.show_about_dialog, accelerator="F1")

        self.menu_bar.add_cascade(label=self.tr("menu_file"), menu=file_menu)
        self.menu_bar.add_cascade(label=self.tr("menu_help"), menu=help_menu)
        self.root.config(menu=self.menu_bar)

    def _register_variable_handlers(self) -> None:
        for variable in (
            self.command_var,
            self.port_var,
            self.dashboard_var,
            self.browser_var,
            self.language_var,
            self.auto_start_var,
            self.auto_close_var,
            self.auto_close_seconds_var,
            self.refresh_interval_var,
            self.remember_position_var,
        ):
            variable.trace_add("write", self._on_ui_value_changed)

    def _load_values_into_ui(self) -> None:
        self.command_var.set(self.config["openclaw"]["command"])
        self.port_var.set(str(self.config["openclaw"]["gateway_port"]))
        self.dashboard_var.set(self.config["openclaw"]["dashboard_url"])
        self.browser_var.set(self.config["openclaw"]["browser_url"])
        self.language_var.set(self.translator.code_to_label(self.config["language"]))
        self.auto_start_var.set(self.config["behavior"]["auto_start_enabled"])
        self.auto_close_var.set(self.config["behavior"]["auto_close_enabled"])
        self.auto_close_seconds_var.set(str(self.config["behavior"]["auto_close_seconds"]))
        self.refresh_interval_var.set(str(self.config["behavior"]["refresh_interval_ms"]))
        self.remember_position_var.set(self.config["window"]["remember_position"])

    def _render_texts(self) -> None:
        self.banner_canvas.itemconfigure(self.banner_title_item, text=self.tr("app_title"))
        self.banner_canvas.itemconfigure(self.banner_subtitle_item, text=self.tr("app_subtitle"))
        self.banner_canvas.itemconfigure(self.banner_version_item, text=self.tr("version_badge", version=APP_VERSION_TAG))

        self.controls_title.configure(text=self.tr("section_controls"))
        self.start_button.configure(text=self.tr("button_start"))
        self.stop_button.configure(text=self.tr("button_stop"))
        self.restart_button.configure(text=self.tr("button_restart"))
        self.refresh_button.configure(text=self.tr("button_refresh"))
        self.dashboard_button.configure(text=self.tr("button_dashboard"))
        self.browser_button.configure(text=self.tr("button_browser"))
        self.kill_button.configure(text=self.tr("button_kill"))
        self.clear_log_button.configure(text=self.tr("button_clear_log"))
        self.exit_button.configure(text=self.tr("button_exit"))
        self.shortcuts_title.configure(text=self.tr("label_shortcuts"))
        self.shortcuts_label.configure(text=self.tr("shortcuts_hint"))

        self.settings_title.configure(text=self.tr("section_settings"))
        self.command_label.configure(text=self.tr("label_command"))
        self.port_label.configure(text=self.tr("label_port"))
        self.dashboard_label.configure(text=self.tr("label_dashboard"))
        self.browser_label.configure(text=self.tr("label_browser"))
        self.language_label.configure(text=self.tr("label_language"))
        self.auto_start_check.configure(text=self.tr("label_auto_start"))
        self.auto_close_check.configure(text=self.tr("label_auto_close"))
        self.auto_close_seconds_label.configure(text=self.tr("label_auto_close_seconds"))
        self.refresh_interval_label.configure(text=self.tr("label_refresh_interval"))
        self.remember_position_check.configure(text=self.tr("label_window_position"))

        self.runtime_title.configure(text=self.tr("section_runtime"))
        self.app_status_label.configure(text=self.tr("label_app_status"))
        self.port_runtime_label.configure(text=self.tr("label_port_runtime"))
        self.pid_label.configure(text=self.tr("label_pid"))
        self.version_label.configure(text=self.tr("label_version"))
        self.log_title.configure(text=self.tr("section_logs"))
        self._build_menu()
        self._apply_runtime_status(self.service.get_status(), False)
        self._refresh_countdown_text()

    def _bind_shortcuts(self) -> None:
        bindings: list[tuple[str, Callable[[], None]]] = [
            ("<Alt-i>", self.start_openclaw),
            ("<Alt-I>", self.start_openclaw),
            ("<Alt-d>", self.stop_openclaw),
            ("<Alt-D>", self.stop_openclaw),
            ("<Alt-r>", self.restart_openclaw),
            ("<Alt-R>", self.restart_openclaw),
            ("<Alt-x>", self.on_exit),
            ("<Alt-X>", self.on_exit),
            ("<F1>", self.show_about_dialog),
            ("<F5>", lambda: self.refresh_status_async(True)),
            ("<Control-l>", self.clear_log),
            ("<Control-L>", self.clear_log),
        ]

        for event_name, callback in bindings:
            self.root.bind_all(event_name, lambda _event, fn=callback: fn())

    def _on_ui_value_changed(self, *_args: object) -> None:
        if self._loading_ui or self._closing:
            return
        if self._save_after_id is not None:
            self.root.after_cancel(self._save_after_id)
        self._save_after_id = self.root.after(300, self._commit_ui_state)

    def _commit_ui_state(self) -> None:
        self._save_after_id = None
        patch = self._build_config_patch()
        if patch is None:
            return

        previous_language = self.config["language"]
        self.config = self.config_manager.update(patch)
        self.service.reload_settings(self.config["openclaw"])

        current_language = self.config["language"]
        if current_language != previous_language:
            self.translator.set_language(current_language)
            self._render_texts()

        self._restart_auto_close_timer()
        self._restart_status_poll_loop()
        self.set_status_message(self.tr("status_saved"))

    def _build_config_patch(self) -> dict[str, object] | None:
        try:
            port = int(self.port_var.get())
            auto_close_seconds = int(self.auto_close_seconds_var.get())
            refresh_interval = int(self.refresh_interval_var.get())
        except ValueError:
            self.set_status_message(self.tr("status_invalid_number", field="valor"))
            return None

        return {
            "language": self.translator.label_to_code(self.language_var.get()),
            "window": {
                "remember_position": bool(self.remember_position_var.get()),
            },
            "behavior": {
                "auto_start_enabled": bool(self.auto_start_var.get()),
                "auto_close_enabled": bool(self.auto_close_var.get()),
                "auto_close_seconds": auto_close_seconds,
                "refresh_interval_ms": refresh_interval,
            },
            "openclaw": {
                "command": self.command_var.get(),
                "gateway_port": port,
                "dashboard_url": self.dashboard_var.get(),
                "browser_url": self.browser_var.get(),
            },
        }

    def _validate_numeric(self, new_value: str) -> bool:
        return new_value.isdigit() or new_value == ""

    def start_openclaw(self) -> None:
        self._run_background_action(self.tr("button_start"), self.service.start_gateway)

    def stop_openclaw(self) -> None:
        self._run_background_action(self.tr("button_stop"), self.service.stop_gateway)

    def restart_openclaw(self) -> None:
        self._run_background_action(self.tr("button_restart"), self.service.restart_gateway)

    def kill_port_process(self) -> None:
        self._run_background_action(self.tr("button_kill"), self.service.kill_gateway_process)

    def open_dashboard(self) -> None:
        self._run_background_action(self.tr("button_dashboard"), self.service.open_dashboard)

    def open_browser_ui(self) -> None:
        self._run_background_action(self.tr("button_browser"), self.service.open_browser_ui)

    def _run_background_action(self, action_label: str, action: Callable[[], None]) -> None:
        self.set_status_message(self.tr("status_busy", action=action_label))

        def worker() -> None:
            try:
                action()
            except Exception as exc:
                logging.getLogger("clawbot").exception("Error inesperado: %s", exc)
            finally:
                self.root.after(0, lambda: self.refresh_status_async(False))

        threading.Thread(target=worker, daemon=True, name=f"task-{action_label}").start()

    def refresh_status_async(self, show_feedback: bool = False) -> None:
        if self._closing or self._status_refresh_in_progress:
            return
        self._status_refresh_in_progress = True
        if show_feedback:
            self.set_status_message(self.tr("status_checking"))

        def worker() -> None:
            try:
                status = self.service.get_status()
            except Exception as exc:
                self.logger.exception("Error consultando el estado: %s", exc)
                self.root.after(0, self._reset_status_refresh_flag)
                return
            self.root.after(0, lambda: self._apply_runtime_status(status, show_feedback))

        threading.Thread(target=worker, daemon=True, name="status-refresh").start()

    def _apply_runtime_status(self, status: dict[str, object], show_feedback: bool) -> None:
        self.runtime_status_var.set(self.tr("status_active") if status["running"] else self.tr("status_stopped"))
        self.runtime_port_var.set(str(status["port"]))
        self.runtime_pid_var.set(str(status["pid"] or "-"))
        if show_feedback:
            self.set_status_message(self.tr("status_active") if status["running"] else self.tr("status_stopped"))
        self._status_refresh_in_progress = False

    def _reset_status_refresh_flag(self) -> None:
        self._status_refresh_in_progress = False

    def _start_status_poll_loop(self) -> None:
        self._restart_status_poll_loop()
        self.refresh_status_async(False)

    def _restart_status_poll_loop(self) -> None:
        if self._status_poll_after_id is not None:
            self.root.after_cancel(self._status_poll_after_id)
        interval = max(500, int(self.config["behavior"]["refresh_interval_ms"]))

        def loop() -> None:
            if self._closing:
                return
            self.refresh_status_async(False)
            self._status_poll_after_id = self.root.after(interval, loop)

        self._status_poll_after_id = self.root.after(interval, loop)

    def _process_log_queue(self) -> None:
        try:
            while True:
                line = self.log_queue.get_nowait()
                self._append_log(line)
        except queue.Empty:
            pass

        if not self._closing:
            self.root.after(250, self._process_log_queue)

    def _append_log(self, text: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self.set_status_message(self.tr("button_clear_log"))

    def set_status_message(self, message: str) -> None:
        self.status_bar_var.set(message)

    def _restart_auto_close_timer(self) -> None:
        if self._countdown_after_id is not None:
            self.root.after_cancel(self._countdown_after_id)
            self._countdown_after_id = None

        if not self.config["behavior"]["auto_close_enabled"]:
            self._countdown_remaining = None
            self._refresh_countdown_text()
            return

        self._countdown_remaining = int(self.config["behavior"]["auto_close_seconds"])
        self._refresh_countdown_text()
        self._schedule_countdown_tick()

    def _schedule_countdown_tick(self) -> None:
        self._countdown_after_id = self.root.after(1000, self._countdown_tick)

    def _countdown_tick(self) -> None:
        if self._closing or self._countdown_remaining is None:
            return
        self._countdown_remaining -= 1
        if self._countdown_remaining <= 0:
            self.countdown_var.set(self.tr("countdown_finished"))
            self.logger.info("Autocierre ejecutado por temporizador.")
            self.on_exit()
            return
        self._refresh_countdown_text()
        self._schedule_countdown_tick()

    def _refresh_countdown_text(self) -> None:
        if self._countdown_remaining is None:
            self.countdown_var.set(self.tr("countdown_disabled"))
        else:
            self.countdown_var.set(self.tr("countdown_active", seconds=self._countdown_remaining))

    def show_about_dialog(self) -> None:
        AboutDialog(
            self.root,
            self.tr("about_title"),
            self.tr("about_message", version=APP_VERSION_TAG, year=COPYRIGHT_YEAR),
            self.tr("dialog_close"),
        )

    def _on_root_configure(self, event: tk.Event[tk.Misc]) -> None:
        if self._loading_ui or self._closing:
            return
        if event.widget is not self.root:
            return
        if not self.remember_position_var.get():
            return
        if self.root.state() != "normal":
            return
        if self._geometry_after_id is not None:
            self.root.after_cancel(self._geometry_after_id)
        self._geometry_after_id = self.root.after(500, self._save_geometry)

    def _save_geometry(self) -> None:
        self._geometry_after_id = None
        self.config = self.config_manager.update({"window": {"geometry": self.root.geometry()}})

    def on_exit(self) -> None:
        if self._closing:
            return
        self._closing = True
        self.logger.info("Cerrando aplicación")

        if self.remember_position_var.get() and self.root.state() == "normal":
            self.config_manager.update({"window": {"geometry": self.root.geometry()}})

        for after_id in (
            self._save_after_id,
            self._geometry_after_id,
            self._countdown_after_id,
            self._status_poll_after_id,
        ):
            if after_id is not None:
                try:
                    self.root.after_cancel(after_id)
                except tk.TclError:
                    pass

        self.root.destroy()


def create_app(root: tk.Tk) -> OpenClawManagerApp:
    return OpenClawManagerApp(root)
