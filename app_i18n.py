LANGUAGE_LABELS = {
    "es": "Español",
    "en": "English",
}


TEXTS = {
    "es": {
        "app_title": "OpenClaw Manager",
        "app_subtitle": "Centro de control visual para OpenClaw",
        "version_badge": "Versión {version}",
        "section_controls": "Comandos",
        "section_settings": "Parámetros",
        "section_runtime": "Estado en tiempo real",
        "section_logs": "Bitácora",
        "label_command": "Comando OpenClaw",
        "label_port": "Puerto gateway",
        "label_dashboard": "URL Dashboard",
        "label_browser": "URL Browser UI",
        "label_language": "Idioma",
        "label_auto_start": "Autoiniciar al abrir",
        "label_auto_close": "Autocerrar aplicación",
        "label_auto_close_seconds": "Segundos de autocierre",
        "label_refresh_interval": "Refresco de estado (ms)",
        "label_window_position": "Recordar posición",
        "label_app_status": "Estado",
        "label_pid": "PID",
        "label_port_runtime": "Puerto",
        "label_version": "Versión",
        "label_shortcuts": "Atajos",
        "button_start": "Iniciar",
        "button_stop": "Detener",
        "button_restart": "Reiniciar",
        "button_refresh": "Verificar",
        "button_dashboard": "Dashboard",
        "button_browser": "Browser UI",
        "button_kill": "Liberar puerto",
        "button_clear_log": "Limpiar log",
        "button_exit": "Salir",
        "status_ready": "Listo",
        "status_checking": "Verificando estado...",
        "status_active": "Activo",
        "status_stopped": "Detenido",
        "status_saved": "Configuración guardada automáticamente",
        "status_busy": "Procesando {action}...",
        "status_invalid_number": "El valor de {field} no es válido.",
        "countdown_active": "Autocierre en {seconds}s",
        "countdown_disabled": "Autocierre desactivado",
        "countdown_finished": "Tiempo agotado. Cerrando aplicación...",
        "about_title": "Acerca de",
        "about_message": "{version} creado por Synyster Rick, {year} Derechos Reservados",
        "menu_file": "Archivo",
        "menu_help": "Ayuda",
        "menu_about": "Acerca de",
        "menu_exit": "Salir",
        "menu_refresh": "Verificar estado",
        "menu_clear_log": "Limpiar log",
        "menu_start": "Iniciar",
        "menu_stop": "Detener",
        "menu_restart": "Reiniciar",
        "menu_dashboard": "Abrir Dashboard",
        "menu_browser": "Abrir Browser UI",
        "menu_release_port": "Liberar puerto",
        "shortcuts_hint": "Alt+I iniciar | Alt+D detener | Alt+R reiniciar | F5 verificar | Ctrl+L limpiar | Alt+X salir | F1 about",
        "dialog_close": "Cerrar",
    },
    "en": {
        "app_title": "OpenClaw Manager",
        "app_subtitle": "Visual control center for OpenClaw",
        "version_badge": "Version {version}",
        "section_controls": "Commands",
        "section_settings": "Settings",
        "section_runtime": "Live status",
        "section_logs": "Log stream",
        "label_command": "OpenClaw command",
        "label_port": "Gateway port",
        "label_dashboard": "Dashboard URL",
        "label_browser": "Browser UI URL",
        "label_language": "Language",
        "label_auto_start": "Auto-start on launch",
        "label_auto_close": "Auto-close application",
        "label_auto_close_seconds": "Auto-close seconds",
        "label_refresh_interval": "Status refresh (ms)",
        "label_window_position": "Remember position",
        "label_app_status": "Status",
        "label_pid": "PID",
        "label_port_runtime": "Port",
        "label_version": "Version",
        "label_shortcuts": "Shortcuts",
        "button_start": "Start",
        "button_stop": "Stop",
        "button_restart": "Restart",
        "button_refresh": "Refresh",
        "button_dashboard": "Dashboard",
        "button_browser": "Browser UI",
        "button_kill": "Free port",
        "button_clear_log": "Clear log",
        "button_exit": "Exit",
        "status_ready": "Ready",
        "status_checking": "Checking status...",
        "status_active": "Running",
        "status_stopped": "Stopped",
        "status_saved": "Configuration saved automatically",
        "status_busy": "Processing {action}...",
        "status_invalid_number": "{field} has an invalid value.",
        "countdown_active": "Auto-close in {seconds}s",
        "countdown_disabled": "Auto-close disabled",
        "countdown_finished": "Time reached. Closing application...",
        "about_title": "About",
        "about_message": "{version} created by Synyster Rick, {year} All Rights Reserved",
        "menu_file": "File",
        "menu_help": "Help",
        "menu_about": "About",
        "menu_exit": "Exit",
        "menu_refresh": "Refresh status",
        "menu_clear_log": "Clear log",
        "menu_start": "Start",
        "menu_stop": "Stop",
        "menu_restart": "Restart",
        "menu_dashboard": "Open Dashboard",
        "menu_browser": "Open Browser UI",
        "menu_release_port": "Free port",
        "shortcuts_hint": "Alt+I start | Alt+D stop | Alt+R restart | F5 refresh | Ctrl+L clear | Alt+X exit | F1 about",
        "dialog_close": "Close",
    },
}


class Translator:
    def __init__(self, language: str = "es") -> None:
        self.language = language if language in LANGUAGE_LABELS else "es"

    def set_language(self, language: str) -> None:
        self.language = language if language in LANGUAGE_LABELS else "es"

    def tr(self, key: str, **kwargs) -> str:
        bucket = TEXTS.get(self.language, TEXTS["es"])
        template = bucket.get(key, TEXTS["es"].get(key, key))
        return template.format(**kwargs)

    def code_to_label(self, code: str) -> str:
        return LANGUAGE_LABELS.get(code, LANGUAGE_LABELS["es"])

    def label_to_code(self, label: str) -> str:
        for code, text in LANGUAGE_LABELS.items():
            if text == label:
                return code
        return "es"
