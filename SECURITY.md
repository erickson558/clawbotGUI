# Security

## Supported Versions

La versión soportada es siempre la release estable más reciente publicada desde `main`. La versión visible para usuarios, el ejecutable y el tag de GitHub salen de la misma fuente de verdad: [`app_version.py`](app_version.py).

## Runtime Security Notes

- La aplicación evita `shell=True` en las llamadas a procesos.
- Los wrappers `.cmd` y `.bat` de Windows se ejecutan en modo oculto para no exponer consolas adicionales al usuario.
- El inicio del gateway en Windows usa el launcher local `~/.openclaw/gateway.cmd` en modo oculto, evitando depender de la tarea programada interactiva.
- La detección del runtime valida procesos y puertos reales de OpenClaw para no disparar una segunda instancia sobre un gateway ya vivo.
- La configuración se valida y sanea antes de usarse.
- `config.json` y `log.txt` se generan localmente y no se publican en git.
- La compilación del ejecutable se realiza en modo `--windowed` para evitar consola visible.
- El ejecutable de Windows se compila con metadatos de versión alineados con `APP_VERSION_TAG`.

## Reporting

Si detectas una vulnerabilidad, no abras un issue público con detalles sensibles. Comparte el hallazgo por un canal privado con pasos de reproducción, impacto y posible mitigación.
