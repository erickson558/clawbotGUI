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
from app_icons import ButtonIconFactory
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


class ScrollableFrame(tk.Frame):
    def __init__(self, parent: tk.Widget, *, background: str) -> None:
        super().__init__(parent, bg=background)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            self,
            bg=background,
            highlightthickness=0,
            borderwidth=0,
            yscrollincrement=20,
        )
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.body = tk.Frame(self.canvas, bg=background)
        self.window_id = self.canvas.create_window((0, 0), window=self.body, anchor="nw")

        self.body.bind("<Configure>", self._sync_scroll_region)
        self.canvas.bind("<Configure>", self._sync_body_width)
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

    def _sync_scroll_region(self, _event: tk.Event[tk.Misc]) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _sync_body_width(self, event: tk.Event[tk.Misc]) -> None:
        self.canvas.itemconfigure(self.window_id, width=event.width)

    def _bind_mousewheel(self, _event: tk.Event[tk.Misc]) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, _event: tk.Event[tk.Misc]) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event: tk.Event[tk.Misc]) -> None:
        delta = int(-(event.delta / 120)) if getattr(event, "delta", 0) else 0
        if delta:
            self.canvas.yview_scroll(delta, "units")


class OpenClawManagerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.configure(bg="#08131D")
        self.root.minsize(1080, 680)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.console_queue: queue.Queue[str] = queue.Queue()
        self.config_manager = ConfigManager(CONFIG_PATH)
        self.config = self.config_manager.export()
        self.translator = Translator(self.config["language"])
        self.logger = configure_logging(LOG_PATH, self.log_queue)
        self.service = OpenClawService(
            self.logger,
            self.config["openclaw"],
            console_callback=self._enqueue_console_output,
        )
        self.icon_factory = ButtonIconFactory()
        self.button_icons: dict[str, object | None] = {}

        self._loading_ui = True
        self._closing = False
        self._save_after_id: str | None = None
        self._geometry_after_id: str | None = None
        self._countdown_after_id: str | None = None
        self._status_poll_after_id: str | None = None
        self._status_refresh_in_progress = False
        self._countdown_remaining: int | None = None
        self._active_actions: set[str] = set()
        self._action_buttons: dict[str, tk.Button] = {}

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

        self.action_palettes = {
            "start": {"base": "#0E8F63", "hover": "#15B97F", "active": "#0B754F", "border": "#7BF0C6"},
            "stop": {"base": "#C73E2B", "hover": "#E65944", "active": "#A53021", "border": "#FFB0A6"},
            "restart": {"base": "#D96D1F", "hover": "#F08A33", "active": "#B75A16", "border": "#FFD08C"},
            "refresh": {"base": "#175676", "hover": "#21779E", "active": "#11445B", "border": "#8AE5FF"},
            "dashboard": {"base": "#0F766E", "hover": "#139489", "active": "#0A5C56", "border": "#7BF3E7"},
            "browser": {"base": "#275D8C", "hover": "#347ABD", "active": "#1F4C72", "border": "#9BD1FF"},
            "kill": {"base": "#8F1233", "hover": "#B21942", "active": "#6D0E27", "border": "#FF9AB2"},
            "clear": {"base": "#50555C", "hover": "#6B717A", "active": "#3E4248", "border": "#C9D0D9"},
            "exit": {"base": "#111827", "hover": "#223146", "active": "#0B1220", "border": "#A7B7C8"},
        }

        style.configure("Accent.TButton", font=("Segoe UI Semibold", 10), padding=(14, 10))
        style.configure("Modern.TCheckbutton", background="#F7FBFF", font=("Segoe UI", 10))
        style.configure("Modern.TNotebook", background="#08131D", borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure(
            "Modern.TNotebook.Tab",
            background="#0F1E2C",
            foreground="#D4E7FF",
            padding=(18, 10),
            borderwidth=0,
            font=("Segoe UI Semibold", 10),
        )
        style.map(
            "Modern.TNotebook.Tab",
            background=[("selected", "#16A0B8"), ("active", "#13314A")],
            foreground=[("selected", "#FFFFFF"), ("active", "#FFFFFF")],
        )
        style.configure(
            "Modern.TEntry",
            padding=6,
            fieldbackground="#FFFFFF",
            foreground="#10273D",
            bordercolor="#C4D6E8",
            lightcolor="#C4D6E8",
            darkcolor="#C4D6E8",
        )
        style.configure(
            "Modern.TSpinbox",
            padding=6,
            arrowsize=14,
            fieldbackground="#FFFFFF",
            foreground="#10273D",
            bordercolor="#C4D6E8",
            lightcolor="#C4D6E8",
            darkcolor="#C4D6E8",
        )
        style.configure(
            "Modern.TCombobox",
            padding=6,
            arrowsize=16,
            fieldbackground="#FFFFFF",
            foreground="#10273D",
            bordercolor="#C4D6E8",
            lightcolor="#C4D6E8",
            darkcolor="#C4D6E8",
        )
        style.map(
            "Modern.TCombobox",
            fieldbackground=[("readonly", "#FFFFFF")],
            selectbackground=[("readonly", "#FFFFFF")],
            selectforeground=[("readonly", "#10273D")],
        )

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
            height=96,
            bg="#08131D",
            highlightthickness=0,
            bd=0,
        )
        self.banner_canvas.grid(row=0, column=0, sticky="ew")
        self.banner_canvas.create_oval(-50, -42, 220, 160, fill="#103B5F", outline="")
        self.banner_canvas.create_oval(860, -60, 1210, 150, fill="#17A2B8", outline="")
        self.banner_title_item = self.banner_canvas.create_text(
            34,
            18,
            anchor="nw",
            fill="#F7FBFF",
            font=("Segoe UI Semibold", 25),
            text="",
        )
        self.banner_subtitle_item = self.banner_canvas.create_text(
            36,
            55,
            anchor="nw",
            fill="#C8E3FF",
            font=("Segoe UI", 11),
            text="",
        )
        self.banner_version_item = self.banner_canvas.create_text(
            1010,
            32,
            anchor="ne",
            fill="#F7FBFF",
            font=("Consolas", 11, "bold"),
            text=APP_VERSION_TAG,
        )

        content = tk.Frame(self.root, bg="#08131D", padx=16, pady=14)
        content.grid(row=1, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)

        self.stats_card = self._make_card(content, padding=(16, 14))
        self.stats_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        for column_index in range(4):
            self.stats_card.grid_columnconfigure(column_index, weight=1, uniform="stat")

        self.runtime_title = self._card_title(self.stats_card)
        self.runtime_title.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 12))

        self.status_tile, self.app_status_label, self.app_status_value = self._make_stat_tile(
            self.stats_card,
            label_var=self.runtime_status_var,
            background="#0E2438",
            accent="#2FE4A7",
        )
        self.port_tile, self.port_runtime_label, self.port_runtime_value = self._make_stat_tile(
            self.stats_card,
            label_var=self.runtime_port_var,
            background="#11304A",
            accent="#6BD4FF",
        )
        self.pid_tile, self.pid_label, self.pid_value = self._make_stat_tile(
            self.stats_card,
            label_var=self.runtime_pid_var,
            background="#1C2D43",
            accent="#FF9E57",
        )
        self.version_tile, self.version_label, self.version_value = self._make_stat_tile(
            self.stats_card,
            label_var=self.version_var,
            background="#173B59",
            accent="#CFFB64",
        )

        for index, tile in enumerate((self.status_tile, self.port_tile, self.pid_tile, self.version_tile)):
            tile.grid(row=1, column=index, sticky="ew", padx=(0 if index == 0 else 6, 0))

        self.workspace = tk.Frame(content, bg="#08131D")
        self.workspace.grid(row=1, column=0, sticky="nsew")
        self.workspace.grid_rowconfigure(0, weight=1)
        self.workspace.grid_columnconfigure(0, weight=1)

        self.notebook = ttk.Notebook(self.workspace, style="Modern.TNotebook")
        self.notebook.grid(row=0, column=0, sticky="nsew")

        self.control_tab = tk.Frame(self.notebook, bg="#08131D", padx=2, pady=2)
        self.settings_tab = tk.Frame(self.notebook, bg="#08131D", padx=2, pady=2)
        self.console_tab = tk.Frame(self.notebook, bg="#08131D", padx=2, pady=2)
        self.logs_tab = tk.Frame(self.notebook, bg="#08131D", padx=2, pady=2)

        self.notebook.add(self.control_tab, text="")
        self.notebook.add(self.settings_tab, text="")
        self.notebook.add(self.console_tab, text="")
        self.notebook.add(self.logs_tab, text="")

        self.control_scroll = ScrollableFrame(self.control_tab, background="#08131D")
        self.control_scroll.pack(fill="both", expand=True)
        self.control_scroll.body.grid_columnconfigure(0, weight=1)

        self.controls_card = self._make_card(self.control_scroll.body, padding=(14, 14))
        self.controls_card.grid(row=0, column=0, sticky="ew")
        self.controls_card.grid_columnconfigure(0, weight=1)

        self.controls_title = self._card_title(self.controls_card)
        self.controls_title.grid(row=0, column=0, sticky="w")

        self.controls_summary = tk.Label(
            self.controls_card,
            bg="#F7FBFF",
            fg="#35506A",
            font=("Segoe UI", 10),
            justify="left",
            anchor="w",
            wraplength=980,
        )
        self.controls_summary.grid(row=1, column=0, sticky="ew", pady=(6, 12))

        self.primary_actions_title = self._card_subtitle(self.controls_card)
        self.primary_actions_title.grid(row=2, column=0, sticky="w", pady=(0, 6))

        self.primary_button_row = tk.Frame(self.controls_card, bg="#F7FBFF")
        self.primary_button_row.grid(row=3, column=0, sticky="ew")
        for column_index in range(3):
            self.primary_button_row.grid_columnconfigure(column_index, weight=1, uniform="primary-actions")

        self.start_button = self._make_action_button(self.primary_button_row, "start", self.start_openclaw)
        self.stop_button = self._make_action_button(self.primary_button_row, "stop", self.stop_openclaw)
        self.restart_button = self._make_action_button(self.primary_button_row, "restart", self.restart_openclaw)
        for column_index, button in enumerate((self.start_button, self.stop_button, self.restart_button)):
            button.grid(row=0, column=column_index, sticky="ew", padx=6, pady=6)

        self.quick_actions_title = self._card_subtitle(self.controls_card)
        self.quick_actions_title.grid(row=4, column=0, sticky="w", pady=(12, 6))

        self.tool_button_row = tk.Frame(self.controls_card, bg="#F7FBFF")
        self.tool_button_row.grid(row=5, column=0, sticky="ew")
        for column_index in range(6):
            self.tool_button_row.grid_columnconfigure(column_index, weight=1, uniform="quick-actions")

        self.refresh_button = self._make_action_button(
            self.tool_button_row,
            "refresh",
            lambda: self.refresh_status_async(True),
            compact=True,
        )
        self.dashboard_button = self._make_action_button(self.tool_button_row, "dashboard", self.open_dashboard, compact=True)
        self.browser_button = self._make_action_button(self.tool_button_row, "browser", self.open_browser_ui, compact=True)
        self.kill_button = self._make_action_button(self.tool_button_row, "kill", self.kill_port_process, compact=True)
        self.clear_log_button = self._make_action_button(self.tool_button_row, "clear", self.clear_log, compact=True)
        self.exit_button = self._make_action_button(self.tool_button_row, "exit", self.on_exit, compact=True)
        self._action_buttons = {
            "start": self.start_button,
            "stop": self.stop_button,
            "restart": self.restart_button,
            "refresh": self.refresh_button,
            "dashboard": self.dashboard_button,
            "browser": self.browser_button,
            "kill": self.kill_button,
            "clear": self.clear_log_button,
            "exit": self.exit_button,
        }

        quick_buttons = [
            self.refresh_button,
            self.dashboard_button,
            self.browser_button,
            self.kill_button,
            self.clear_log_button,
            self.exit_button,
        ]
        for column_index, button in enumerate(quick_buttons):
            button.grid(row=0, column=column_index, sticky="ew", padx=6, pady=6)

        self.shortcuts_title = self._card_subtitle(self.controls_card)
        self.shortcuts_title.grid(row=6, column=0, sticky="w", pady=(12, 4))
        self.shortcuts_label = tk.Label(
            self.controls_card,
            bg="#0E1D2C",
            fg="#D8E8FF",
            font=("Segoe UI", 9),
            justify="left",
            anchor="w",
            wraplength=980,
            padx=12,
            pady=8,
        )
        self.shortcuts_label.grid(row=7, column=0, sticky="ew")

        self.settings_scroll = ScrollableFrame(self.settings_tab, background="#08131D")
        self.settings_scroll.pack(fill="both", expand=True)
        self.settings_scroll.body.grid_columnconfigure(0, weight=1)

        self.settings_card = self._make_card(self.settings_scroll.body)
        self.settings_card.grid(row=0, column=0, sticky="ew")
        self.settings_card.grid_columnconfigure(0, weight=1)
        self.settings_title = self._card_title(self.settings_card)
        self.settings_title.grid(row=0, column=0, sticky="w")

        self.settings_fields = tk.Frame(self.settings_card, bg="#F7FBFF")
        self.settings_fields.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self.settings_fields.grid_columnconfigure(1, weight=1)

        self.command_label = self._field_label(self.settings_fields)
        self.command_entry = ttk.Entry(self.settings_fields, textvariable=self.command_var, style="Modern.TEntry")
        self.port_label = self._field_label(self.settings_fields)
        self.port_spinbox = ttk.Spinbox(
            self.settings_fields,
            from_=1,
            to=65535,
            textvariable=self.port_var,
            style="Modern.TSpinbox",
            validate="key",
            validatecommand=(self.root.register(self._validate_numeric), "%P"),
        )
        self.dashboard_label = self._field_label(self.settings_fields)
        self.dashboard_entry = ttk.Entry(self.settings_fields, textvariable=self.dashboard_var, style="Modern.TEntry")
        self.browser_label = self._field_label(self.settings_fields)
        self.browser_entry = ttk.Entry(self.settings_fields, textvariable=self.browser_var, style="Modern.TEntry")
        self.language_label = self._field_label(self.settings_fields)
        self.language_combo = ttk.Combobox(
            self.settings_fields,
            textvariable=self.language_var,
            values=list(LANGUAGE_LABELS.values()),
            state="readonly",
            style="Modern.TCombobox",
        )

        base_rows = [
            (self.command_label, self.command_entry),
            (self.port_label, self.port_spinbox),
            (self.dashboard_label, self.dashboard_entry),
            (self.browser_label, self.browser_entry),
            (self.language_label, self.language_combo),
        ]
        for row_index, (label, widget) in enumerate(base_rows):
            label.grid(row=row_index, column=0, sticky="w", padx=(0, 12), pady=7)
            widget.grid(row=row_index, column=1, sticky="ew", pady=7)

        self.automation_panel = tk.Frame(
            self.settings_card,
            bg="#0E1D2C",
            highlightbackground="#1A334A",
            highlightthickness=1,
            padx=16,
            pady=16,
        )
        self.automation_panel.grid(row=2, column=0, sticky="ew", pady=(18, 0))
        self.automation_panel.grid_columnconfigure(1, weight=1)
        self.automation_panel.grid_columnconfigure(2, weight=1)

        self.automation_title = tk.Label(
            self.automation_panel,
            bg="#0E1D2C",
            fg="#EAF4FF",
            font=("Segoe UI Semibold", 11),
        )
        self.automation_title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        self.auto_start_check = self._make_toggle(self.automation_panel, self.auto_start_var)
        self.auto_close_check = self._make_toggle(self.automation_panel, self.auto_close_var)
        self.remember_position_check = self._make_toggle(self.automation_panel, self.remember_position_var)
        self.auto_close_seconds_label = tk.Label(
            self.automation_panel,
            bg="#0E1D2C",
            fg="#AFC6E0",
            font=("Segoe UI", 10),
        )
        self.auto_close_spinbox = ttk.Spinbox(
            self.automation_panel,
            from_=5,
            to=86400,
            textvariable=self.auto_close_seconds_var,
            style="Modern.TSpinbox",
            validate="key",
            validatecommand=(self.root.register(self._validate_numeric), "%P"),
        )
        self.refresh_interval_label = tk.Label(
            self.automation_panel,
            bg="#0E1D2C",
            fg="#AFC6E0",
            font=("Segoe UI", 10),
        )
        self.refresh_interval_spinbox = ttk.Spinbox(
            self.automation_panel,
            from_=500,
            to=60000,
            increment=100,
            textvariable=self.refresh_interval_var,
            style="Modern.TSpinbox",
            validate="key",
            validatecommand=(self.root.register(self._validate_numeric), "%P"),
        )

        self.auto_start_check.grid(row=1, column=0, sticky="w", pady=6)
        self.auto_close_check.grid(row=2, column=0, sticky="w", pady=6)
        self.auto_close_seconds_label.grid(row=2, column=1, sticky="w", padx=(14, 8), pady=6)
        self.auto_close_spinbox.grid(row=2, column=2, sticky="ew", pady=6)
        self.remember_position_check.grid(row=3, column=0, sticky="w", pady=6)
        self.refresh_interval_label.grid(row=3, column=1, sticky="w", padx=(14, 8), pady=6)
        self.refresh_interval_spinbox.grid(row=3, column=2, sticky="ew", pady=6)

        self.console_tab.grid_columnconfigure(0, weight=1)
        self.console_tab.grid_rowconfigure(0, weight=1)

        self.console_card = self._make_card(self.console_tab, padding=(16, 16))
        self.console_card.grid(row=0, column=0, sticky="nsew")
        self.console_card.grid_rowconfigure(2, weight=1)
        self.console_card.grid_columnconfigure(0, weight=1)

        self.console_header = tk.Frame(self.console_card, bg="#F7FBFF")
        self.console_header.grid(row=0, column=0, sticky="ew")
        self.console_header.grid_columnconfigure(0, weight=1)

        self.console_title = self._card_title(self.console_header)
        self.console_title.grid(row=0, column=0, sticky="w")

        self.clear_console_button = ttk.Button(
            self.console_header,
            command=self.clear_console,
            style="Accent.TButton",
        )
        self.clear_console_button.grid(row=0, column=1, sticky="e")

        self.console_hint = tk.Label(
            self.console_card,
            bg="#F7FBFF",
            fg="#35506A",
            font=("Segoe UI", 10),
            justify="left",
            anchor="w",
            wraplength=980,
        )
        self.console_hint.grid(row=1, column=0, sticky="ew", pady=(8, 10))

        self.console_text = scrolledtext.ScrolledText(
            self.console_card,
            wrap="word",
            font=("Consolas", 10),
            background="#061018",
            foreground="#E6F2FF",
            insertbackground="#F7FBFF",
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=12,
        )
        self.console_text.grid(row=2, column=0, sticky="nsew")
        self.console_text.configure(state="disabled")

        self.logs_tab.grid_columnconfigure(0, weight=1)
        self.logs_tab.grid_rowconfigure(0, weight=1)

        self.log_card = self._make_card(self.logs_tab, padding=(16, 16))
        self.log_card.grid(row=0, column=0, sticky="nsew")
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

    def _make_card(self, parent: tk.Widget, *, padding: tuple[int, int] = (18, 18)) -> tk.Frame:
        return tk.Frame(
            parent,
            bg="#F7FBFF",
            highlightbackground="#D3E3F5",
            highlightthickness=1,
            bd=0,
            padx=padding[0],
            pady=padding[1],
        )

    def _card_title(self, parent: tk.Widget) -> tk.Label:
        return tk.Label(parent, bg="#F7FBFF", fg="#0E2B47", font=("Segoe UI Semibold", 14))

    def _card_subtitle(self, parent: tk.Widget) -> tk.Label:
        return tk.Label(parent, bg="#F7FBFF", fg="#1F4E79", font=("Segoe UI Semibold", 10))

    def _field_label(self, parent: tk.Widget) -> tk.Label:
        return tk.Label(parent, bg="#F7FBFF", fg="#35506A", font=("Segoe UI", 10))

    def _value_label(self, parent: tk.Widget, variable: tk.StringVar) -> tk.Label:
        return tk.Label(parent, textvariable=variable, bg="#F7FBFF", fg="#10273D", font=("Consolas", 11, "bold"))

    def _make_stat_tile(
        self,
        parent: tk.Widget,
        *,
        label_var: tk.StringVar,
        background: str,
        accent: str,
    ) -> tuple[tk.Frame, tk.Label, tk.Label]:
        tile = tk.Frame(
            parent,
            bg=background,
            highlightbackground=accent,
            highlightthickness=2,
            bd=0,
            padx=14,
            pady=12,
        )
        title_label = tk.Label(tile, bg=background, fg="#A8C4E0", font=("Segoe UI", 10))
        value_label = tk.Label(
            tile,
            textvariable=label_var,
            bg=background,
            fg=accent,
            font=("Consolas", 13, "bold"),
            anchor="w",
        )
        title_label.pack(anchor="w")
        value_label.pack(anchor="w", pady=(8, 0))
        return tile, title_label, value_label

    def _make_toggle(self, parent: tk.Widget, variable: tk.BooleanVar) -> tk.Checkbutton:
        return tk.Checkbutton(
            parent,
            variable=variable,
            bg="#0E1D2C",
            fg="#EAF4FF",
            activebackground="#0E1D2C",
            activeforeground="#FFFFFF",
            selectcolor="#F7FBFF",
            highlightthickness=0,
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI Semibold", 10),
        )

    def _make_action_button(
        self,
        parent: tk.Widget,
        variant: str,
        command: Callable[[], None],
        *,
        compact: bool = False,
    ) -> tk.Button:
        palette = self.action_palettes[variant]
        icon = self.button_icons.get(variant)
        if icon is None:
            icon = self.icon_factory.build(variant)
            self.button_icons[variant] = icon
        font = ("Segoe UI Semibold", 10 if compact else 11)
        padx = 10 if compact else 12
        pady = 10 if compact else 12
        wraplength = 100 if compact else 140
        compound = "left" if compact else "top"
        button = tk.Button(
            parent,
            command=command,
            bg=palette["base"],
            fg="#F7FBFF",
            activebackground=palette["active"],
            activeforeground="#FFFFFF",
            highlightbackground=palette["border"],
            highlightcolor=palette["border"],
            highlightthickness=2,
            bd=0,
            relief="flat",
            cursor="hand2",
            font=font,
            disabledforeground="#D0D9E3",
            padx=padx,
            pady=pady,
            wraplength=wraplength,
            image=icon,
            compound=compound,
        )
        self._bind_button_hover(button, palette["base"], palette["hover"])
        return button

    def _bind_button_hover(self, button: tk.Button, base_color: str, hover_color: str) -> None:
        button.bind("<Enter>", lambda _event: button.configure(bg=hover_color))
        button.bind("<Leave>", lambda _event: button.configure(bg=base_color))

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
        self.notebook.tab(self.control_tab, text=self.tr("section_controls"))
        self.notebook.tab(self.settings_tab, text=self.tr("section_settings"))
        self.notebook.tab(self.console_tab, text=self.tr("section_console"))
        self.notebook.tab(self.logs_tab, text=self.tr("section_logs"))

        self.controls_title.configure(text=self.tr("section_controls"))
        self.controls_summary.configure(text=self.tr("label_controls_summary"))
        self.primary_actions_title.configure(text=self.tr("label_primary_actions"))
        self.quick_actions_title.configure(text=self.tr("label_quick_actions"))
        self.start_button.configure(text=self.tr("button_start").upper())
        self.stop_button.configure(text=self.tr("button_stop").upper())
        self.restart_button.configure(text=self.tr("button_restart").upper())
        self.refresh_button.configure(text=self.tr("button_refresh").upper())
        self.dashboard_button.configure(text=self.tr("button_dashboard").upper())
        self.browser_button.configure(text=self.tr("button_browser").upper())
        self.kill_button.configure(text=self.tr("button_kill").upper())
        self.clear_log_button.configure(text=self.tr("button_clear_log").upper())
        self.exit_button.configure(text=self.tr("button_exit").upper())
        self.shortcuts_title.configure(text=self.tr("label_shortcuts"))
        self.shortcuts_label.configure(text=self.tr("shortcuts_hint"))

        self.settings_title.configure(text=self.tr("section_settings"))
        self.command_label.configure(text=self.tr("label_command"))
        self.port_label.configure(text=self.tr("label_port"))
        self.dashboard_label.configure(text=self.tr("label_dashboard"))
        self.browser_label.configure(text=self.tr("label_browser"))
        self.language_label.configure(text=self.tr("label_language"))
        self.automation_title.configure(text=self.tr("section_automation"))
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
        self.console_title.configure(text=self.tr("section_console"))
        self.console_hint.configure(text=self.tr("label_console_hint"))
        self.clear_console_button.configure(text=self.tr("button_clear_console"))
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
        self._show_console_tab()
        self._run_background_action("start", self.tr("button_start"), self.service.start_gateway)

    def stop_openclaw(self) -> None:
        self._show_console_tab()
        self._run_background_action("stop", self.tr("button_stop"), self.service.stop_gateway)

    def restart_openclaw(self) -> None:
        self._show_console_tab()
        self._run_background_action("restart", self.tr("button_restart"), self.service.restart_gateway)

    def kill_port_process(self) -> None:
        self._show_console_tab()
        self._run_background_action("kill", self.tr("button_kill"), self.service.kill_gateway_process)

    def open_dashboard(self) -> None:
        self._run_background_action("dashboard", self.tr("button_dashboard"), self.service.open_dashboard)

    def open_browser_ui(self) -> None:
        self._run_background_action("browser", self.tr("button_browser"), self.service.open_browser_ui)

    def _run_background_action(self, action_key: str, action_label: str, action: Callable[[], None]) -> None:
        if self._closing:
            return
        if action_key in self._active_actions:
            self.set_status_message(self.tr("status_action_running", action=action_label))
            return

        self._active_actions.add(action_key)
        self._set_action_button_state(action_key, enabled=False)
        self.set_status_message(self.tr("status_busy", action=action_label))

        def worker() -> None:
            try:
                action()
            except Exception as exc:
                logging.getLogger("clawbot").exception("Error inesperado: %s", exc)
            finally:
                self._safe_after(0, lambda: self._finish_background_action(action_key))

        threading.Thread(target=worker, daemon=True, name=f"task-{action_label}").start()

    def _finish_background_action(self, action_key: str) -> None:
        self._active_actions.discard(action_key)
        self._set_action_button_state(action_key, enabled=True)
        self.refresh_status_async(True)

    def _set_action_button_state(self, action_key: str, *, enabled: bool) -> None:
        button = self._action_buttons.get(action_key)
        if button is None:
            return
        button.configure(
            state="normal" if enabled else "disabled",
            cursor="hand2" if enabled else "arrow",
        )

    def _safe_after(self, delay_ms: int, callback: Callable[[], None]) -> str | None:
        if self._closing:
            return None
        try:
            return self.root.after(delay_ms, callback)
        except (RuntimeError, tk.TclError):
            return None

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
                self._safe_after(0, self._reset_status_refresh_flag)
                return
            self._safe_after(0, lambda: self._apply_runtime_status(status, show_feedback))

        threading.Thread(target=worker, daemon=True, name="status-refresh").start()

    def _apply_runtime_status(self, status: dict[str, object], show_feedback: bool) -> None:
        is_running = bool(status["running"])
        self.runtime_status_var.set(self.tr("status_active") if is_running else self.tr("status_stopped"))
        self.runtime_port_var.set(str(status["port"]))
        self.runtime_pid_var.set(str(status["pid"] or "-"))
        self.app_status_value.configure(fg="#2FE4A7" if is_running else "#FF6B6B")
        if show_feedback:
            self.set_status_message(self.tr("status_active") if is_running else self.tr("status_stopped"))
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

        try:
            while True:
                line = self.console_queue.get_nowait()
                self._append_console(line)
        except queue.Empty:
            pass

        if not self._closing:
            self.root.after(250, self._process_log_queue)

    def _enqueue_console_output(self, text: str) -> None:
        self.console_queue.put(text)

    def _append_log(self, text: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _append_console(self, text: str) -> None:
        self.console_text.configure(state="normal")
        self.console_text.insert("end", text + "\n")
        self.console_text.see("end")
        self.console_text.configure(state="disabled")

    def clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self.set_status_message(self.tr("button_clear_log"))

    def clear_console(self) -> None:
        self.console_text.configure(state="normal")
        self.console_text.delete("1.0", "end")
        self.console_text.configure(state="disabled")
        self.set_status_message(self.tr("button_clear_console"))

    def _show_console_tab(self) -> None:
        self.notebook.select(self.console_tab)

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
