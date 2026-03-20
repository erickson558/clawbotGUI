# clawbotGUI

`clawbotGUI` es una interfaz de escritorio para administrar OpenClaw sin perder la funcionalidad actual del proyecto original. La aplicación ahora separa frontend y backend, guarda su configuración automáticamente y puede compilarse a un `.exe` silencioso para Windows.

## Qué hace

- Inicia, detiene y reinicia el gateway de OpenClaw.
- Consulta el estado del puerto configurado y muestra el PID activo.
- Abre Dashboard y Browser UI desde la interfaz.
- Libera el puerto configurado sin abrir ventanas de consola.
- Muestra actividad en una bitácora visual y la escribe en `log.txt`.
- Muestra la salida de OpenClaw en una consola embebida dentro de la propia GUI.
- Soporta español e inglés.
- Reorganiza la experiencia en pestañas para que toda la GUI siga siendo usable incluso con contenido adicional.
- Usa botones con iconografía integrada para reforzar las acciones principales.

## Mejoras implementadas

- Versionado centralizado en [`app_version.py`](app_version.py).
- Configuración externa en `config.json` junto al `.py` o `.exe`.
- Autoguardado de cambios de la GUI en cada ajuste.
- Persistencia de tamaño y posición de ventana.
- Autoinicio opcional del proceso.
- Autocierre configurable con countdown en la barra de estado.
- Menú superior con About y atajos de teclado.
- Navegación por pestañas para separar comandos, configuración y bitácora.
- Nueva pestaña `Consola OpenClaw` para ver la salida silenciosa del proceso sin depender de una ventana CMD.
- Panel de configuración con scroll para no perder controles por altura de ventana.
- Pestaña de comandos reorganizada en acciones principales y herramientas rápidas para evitar cortes visuales.
- Botones visuales con iconos generados en runtime.
- Logging con timestamp y escritura atómica de configuración.
- Llamadas a procesos en modo silencioso usando `CREATE_NO_WINDOW`.
- Resolución robusta del ejecutable de OpenClaw en Windows, incluyendo shims `.cmd` de npm.
- Ejecución oculta de wrappers `.cmd` y `.bat` de OpenClaw en Windows, manteniendo la salida integrada en la bitácora de la GUI.
- Inicio gestionado del gateway en Windows usando `~/.openclaw/gateway.cmd`, evitando que la GUI dispare la tarea programada interactiva que abría una consola externa.
- Detección del runtime real tanto para el formato antiguo `dist/index.js gateway` como para el formato actual `openclaw.mjs gateway run`.
- Protección contra clics repetidos en operaciones largas para evitar acciones paralelas duplicadas.
- Detección de estado alineada con el proceso real de OpenClaw, incluso si el puerto efectivo no coincide con el configurado en la GUI.
- Apertura de `Dashboard` y `Browser UI` usando el puerto real detectado cuando OpenClaw está corriendo fuera del puerto guardado en `config.json`.

## Estructura

- [`clawbotmanayer.py`](clawbotmanayer.py): punto de entrada.
- [`app_ui.py`](app_ui.py): GUI y eventos.
- [`app_backend.py`](app_backend.py): procesos, puertos y URLs.
- [`app_config.py`](app_config.py): lectura, validación y guardado de `config.json`.
- [`app_logging.py`](app_logging.py): `log.txt` y cola de mensajes para la GUI.
- [`app_i18n.py`](app_i18n.py): idiomas.
- [`app_icons.py`](app_icons.py): iconos de acciones generados en runtime.
- [`build.ps1`](build.ps1): compilación a `.exe`.

## Configuración

La aplicación usa `config.json` en la misma carpeta del `.py` o `.exe`. Si no existe, lo crea automáticamente con valores seguros por defecto. El archivo de referencia está en [`config.example.json`](config.example.json).

En Windows, el campo `Comando OpenClaw` acepta `openclaw`, `openclaw.cmd`, `npx openclaw` o una ruta completa al ejecutable. La aplicación intenta resolver automáticamente los shims `.cmd` típicos de npm y los ejecuta en modo oculto para que no aparezca ninguna consola separada.

Cuando detecta `~/.openclaw/gateway.cmd`, la GUI usa ese launcher foreground en modo oculto para iniciar el gateway sin pasar por `openclaw gateway start`. Eso evita que Windows abra una terminal externa desde la tarea programada. Si el puerto efectivo de OpenClaw no coincide con el configurado manualmente en la GUI, la tarjeta de estado mostrará el puerto real detectado, evitará arrancar una segunda instancia y abrirá `Dashboard`/`Browser UI` usando los puertos activos del runtime.

## Ejecución local

```powershell
python clawbotmanayer.py
```

## Compilación a EXE

```powershell
python -m pip install -r requirements.txt
.\build.ps1
```

El ejecutable se genera como `clawbotGUI.exe` en la raíz del proyecto, sin ventana de consola. Del mismo modo, los procesos de OpenClaw lanzados desde la app mantienen su salida dentro de la consola embebida y de la bitácora visual, sin depender de una ventana CMD externa.

## Versionado

La fuente única de verdad es [`app_version.py`](app_version.py). Para subir la versión patch en `0.0.1` usa:

```powershell
python .\scripts\bump_version.py
```

Para fijar una versión manual:

```powershell
python .\scripts\bump_version.py 0.0.2
```

## Publicación en GitHub

El workflow [`release.yml`](.github/workflows/release.yml) crea una release con cada push a `main`, usando la versión definida en `app_version.py`.

## Seguridad

- Sin `shell=True`.
- URLs validadas antes de abrirse.
- Configuración saneada y guardada de forma atómica.
- Archivos de runtime sensibles ignorados por git: `config.json` y `log.txt`.

## Licencia

Apache License 2.0. Ver [`LICENSE`](LICENSE).
