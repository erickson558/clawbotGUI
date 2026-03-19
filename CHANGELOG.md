# Changelog

## V0.0.4 - 2026-03-19

- Corrección del arranque de OpenClaw en Windows resolviendo automáticamente ejecutables `.cmd`, `.bat` y rutas completas.
- Mensajes de error más claros cuando el comando configurado no existe.
- Documentación actualizada para el uso del campo `Comando OpenClaw`.

## V0.0.3 - 2026-03-19

- Reorganización completa del espacio central usando pestañas para comandos, configuración y bitácora.
- Incorporación de scroll en configuración para asegurar acceso a todos los controles.
- Iconos gráficos en los botones principales y mejora adicional del look agresivo.
- Compilación endurecida y consistente con la versión nueva en la app y el `.exe`.

## V0.0.2 - 2026-03-19

- Reorganización visual de la GUI para dar más espacio al panel de parámetros.
- Conversión del estado en tiempo real a tarjetas superiores compactas.
- Botones de acción con colores agresivos, hover y mayor jerarquía visual.
- Nuevo bloque visual para automatización y sesión, corrigiendo la visibilidad del checkbox de autocierre.
- Mejora del script de compilación para usar directorios temporales de PyInstaller y evitar bloqueos del folder `build`.

## V0.0.1 - 2026-03-19

- Refactorización completa separando frontend y backend.
- GUI rediseñada con versión visible, menú, atajos, estado persistente y barra de estado.
- Configuración externa en `config.json` con autoguardado.
- Logging a `log.txt` con timestamps.
- Inicio y operaciones de backend en hilos para evitar congelamiento.
- Soporte multilenguaje inicial: español e inglés.
- Build silencioso a `.exe` y workflow de release para GitHub.
