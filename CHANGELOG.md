# Changelog

## V0.0.10 - 2026-03-20

- Estandarización del versionado visible en formato `Vx.y.z` con una única fuente de verdad en `app_version.py`.
- Automatización ampliada para subir `patch`, `minor` o `major` y reservar la entrada correspondiente en `CHANGELOG.md`.
- Release de GitHub alineada con la versión de la app, publicando tags `Vx.y.z` y assets versionados.
- Compilación local reforzada para generar `clawbotGUI.exe` en la raíz del proyecto usando el `.ico` local y metadatos de versión de Windows.
- Documentación de README, contribución, seguridad y dependencias actualizada para distribución bajo Apache License 2.0.

## V0.0.9 - 2026-03-20

- Corrección de detección de runtime para reconocer tanto `openclaw.mjs gateway run` como el formato legado `dist/index.js gateway`.
- Prevención de dobles arranques cuando OpenClaw ya está vivo en otro puerto, evitando el error `gateway already running`.
- La GUI vuelve a reflejar correctamente `Activo`, puerto real y PID efectivo aunque `config.json` tenga un puerto antiguo.
- `Dashboard` y `Browser UI` ahora pueden resolver el puerto real del runtime cuando hay desfase entre configuración y ejecución.

## V0.0.8 - 2026-03-19

- Corrección del arranque de OpenClaw en Windows para que la GUI use `~/.openclaw/gateway.cmd` en modo oculto y no dispare la tarea programada interactiva.
- Eliminación práctica de la ventana de consola externa al iniciar desde la aplicación, manteniendo la salida solo en la pestaña `Consola OpenClaw`.
- Validación del flujo completo `start/stop/status` con la tarea programada permaneciendo en estado `Listo` mientras la app gestiona el proceso.

## V0.0.7 - 2026-03-19

- Corrección de la detección de estado para que la GUI identifique el gateway real aunque OpenClaw esté escuchando en un puerto distinto al configurado manualmente.
- La tarjeta de estado ahora muestra puerto y PID efectivos del proceso detectado.
- La barra de estado informa cuando el gateway está activo en un puerto diferente al definido en `config.json`.

## V0.0.6 - 2026-03-19

- Reorganización de la pestaña `Comandos` para que no se corte visualmente, usando una distribución más compacta y scroll seguro.
- Nueva pestaña `Consola OpenClaw` con salida embebida del proceso en modo silent, evitando depender de una ventana CMD externa.
- Protección contra clics repetidos en acciones largas para que no se lancen varias tareas `start/stop/restart` en paralelo.
- Mejora del botón `Detener` en Windows con parada rápida de la tarea programada y cierre directo del proceso del gateway.
- Blindaje de callbacks en segundo plano para evitar errores al cerrar la GUI mientras aún hay refrescos activos.

## V0.0.5 - 2026-03-19

- Corrección del arranque de OpenClaw en Windows para ejecutar shims `.cmd` y `.bat` mediante `cmd.exe` oculto.
- Refuerzo de `CREATE_NO_WINDOW` y `STARTUPINFO` para evitar cualquier ventana CLI visible al iniciar, detener o reiniciar OpenClaw.
- Validación funcional contra el binario real de OpenClaw, manteniendo la salida embebida en la bitácora de la GUI.

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
