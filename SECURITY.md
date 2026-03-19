# Security

## Supported Versions

La versión activa soportada actualmente es `V0.0.5`.

## Runtime Security Notes

- La aplicación evita `shell=True` en las llamadas a procesos.
- Los wrappers `.cmd` y `.bat` de Windows se ejecutan en modo oculto para no exponer consolas adicionales al usuario.
- La configuración se valida y sanea antes de usarse.
- `config.json` y `log.txt` se generan localmente y no se publican en git.
- La compilación del ejecutable se realiza en modo `--windowed` para evitar consola visible.

## Reporting

Si detectas una vulnerabilidad, no abras un issue público con detalles sensibles. Comparte el hallazgo por un canal privado con pasos de reproducción, impacto y posible mitigación.
