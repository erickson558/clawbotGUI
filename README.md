# clawbotGUI

`clawbotGUI` es una interfaz de escritorio para administrar OpenClaw desde Windows sin depender de una terminal visible. La aplicación concentra operación, estado, configuración y salida del gateway en una sola GUI y puede distribuirse como `clawbotGUI.exe`.

## Qué hace el programa

- Inicia, detiene y reinicia el gateway de OpenClaw.
- Detecta el proceso activo, el puerto real y el PID en ejecución.
- Abre `Dashboard` y `Browser UI` desde la interfaz usando el puerto efectivo.
- Libera el puerto configurado sin abrir ventanas de consola.
- Guarda configuración local en `config.json` y bitácora en `log.txt`.
- Muestra la salida de OpenClaw dentro de una consola embebida en la GUI.
- Soporta español e inglés.
- Mantiene la operación en modo silencioso con `CREATE_NO_WINDOW` y wrappers ocultos para `.cmd` y `.bat`.

## Requisitos

- Windows 10 u 11.
- Python 3.12.
- OpenClaw instalado y accesible por comando o ruta.
- `tkinter`, que viene con la instalación estándar de Python en Windows.

## Dependencias del proyecto

Las dependencias de runtime y build están en [`requirements.txt`](requirements.txt):

- `pyinstaller>=6.19.0,<7` para compilar el ejecutable de Windows.
- `Pillow>=11.0.0,<12` para iconografía y recursos gráficos en runtime.

## Ejecución local

```powershell
python -m pip install -r requirements.txt
python .\clawbotmanayer.py
```

## Configuración

La aplicación usa `config.json` en la misma carpeta del `.py` o `.exe`. Si no existe, lo crea automáticamente con valores seguros por defecto. El archivo de referencia está en [`config.example.json`](config.example.json).

En Windows, el campo `Comando OpenClaw` acepta `openclaw`, `openclaw.cmd`, `npx openclaw` o una ruta completa al ejecutable. La app resuelve shims `.cmd` típicos de npm y los ejecuta en modo oculto para evitar una consola adicional.

Cuando detecta `~/.openclaw/gateway.cmd`, la GUI usa ese launcher foreground en modo oculto en lugar de `openclaw gateway start`. Con eso evita la consola externa disparada por la tarea programada de Windows y mantiene la salida dentro de la propia interfaz.

## Compilación a EXE

```powershell
python -m pip install -r requirements.txt
.\build.ps1
```

La compilación:

- genera `clawbotGUI.exe` en la misma carpeta raíz donde vive [`clawbotmanayer.py`](clawbotmanayer.py),
- toma automáticamente el archivo `.ico` presente en la raíz del proyecto,
- embebe metadatos de versión de Windows alineados con la versión mostrada por la app.

## Política de versionado

La fuente única de verdad es [`app_version.py`](app_version.py). La versión visible siempre usa formato `Vx.y.z`, siguiendo SemVer:

- `major`: cambios incompatibles.
- `minor`: funcionalidad nueva compatible hacia atrás.
- `patch`: correcciones y cambios internos compatibles.

Antes de cada commit destinado a `main`, incrementa la versión:

```powershell
python .\scripts\bump_version.py
```

También puedes subir `minor`, `major` o fijar una versión explícita:

```powershell
python .\scripts\bump_version.py --minor
python .\scripts\bump_version.py --major
python .\scripts\bump_version.py 1.2.3
```

El script actualiza la versión central y reserva una nueva entrada en [`CHANGELOG.md`](CHANGELOG.md).

## GitHub y releases

- [`release.yml`](.github/workflows/release.yml) crea o actualiza una release por cada push a `main`.
- El tag de GitHub usa exactamente el mismo formato que la app: `Vx.y.z`.
- El asset publicado se sube como `clawbotGUI-Vx.y.z.exe`.
- [`version-check.yml`](.github/workflows/version-check.yml) valida que la versión aumente respecto a la base del cambio.

Para el flujo de contribución y publicación, revisa [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Estructura

- [`clawbotmanayer.py`](clawbotmanayer.py): punto de entrada.
- [`app_ui.py`](app_ui.py): GUI y eventos.
- [`app_backend.py`](app_backend.py): procesos, puertos y URLs.
- [`app_config.py`](app_config.py): lectura, validación y guardado de `config.json`.
- [`app_logging.py`](app_logging.py): `log.txt` y cola de mensajes para la GUI.
- [`app_i18n.py`](app_i18n.py): idiomas.
- [`app_icons.py`](app_icons.py): iconos generados en runtime.
- [`build.ps1`](build.ps1): build local del `.exe`.
- [`scripts/bump_version.py`](scripts/bump_version.py): automatización de versionado.

## Seguridad

- Sin `shell=True`.
- URLs validadas antes de abrirse.
- Configuración saneada y guardada de forma atómica.
- Archivos locales sensibles ignorados por git: `config.json` y `log.txt`.
- Runtime y build documentados en [`SECURITY.md`](SECURITY.md).

## Licencia

Apache License 2.0. Ver [`LICENSE`](LICENSE) y [`NOTICE`](NOTICE).
