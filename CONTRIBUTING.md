# Contributing

## Flujo recomendado

1. Instala dependencias con `python -m pip install -r requirements.txt`.
2. Ejecuta la app localmente con `python .\clawbotmanayer.py`.
3. Antes de preparar un commit para `main`, incrementa la versión con `python .\scripts\bump_version.py`.
4. Completa la nueva entrada reservada en `CHANGELOG.md`.
5. Recompila con `.\build.ps1` y valida que `clawbotGUI.exe` se genere en la raíz del proyecto.
6. Haz commit con un mensaje claro que incluya el impacto real del cambio.

## Política de versiones

- La fuente única de verdad es `app_version.py`.
- El formato visible es `Vx.y.z`.
- Cada commit destinado a `main` debe incrementar la versión.
- Usa SemVer: `major` para incompatibilidades, `minor` para funcionalidad nueva y `patch` para correcciones compatibles.

Comandos disponibles:

```powershell
python .\scripts\bump_version.py
python .\scripts\bump_version.py --minor
python .\scripts\bump_version.py --major
python .\scripts\bump_version.py 1.2.3
```

## Releases en GitHub

- El workflow `release` publica una release por cada push a `main`.
- El tag de la release debe coincidir con la versión de la app, por ejemplo `V0.0.10`.
- El asset de GitHub se publica como `clawbotGUI-Vx.y.z.exe`.
- El workflow `version-check` valida que la versión aumente antes de integrar cambios.

## Estándares del repositorio

- Documenta cambios funcionales en `CHANGELOG.md`.
- Mantén `README.md` actualizado cuando cambie comportamiento, build o distribución.
- No subas `config.json`, `log.txt` ni binarios temporales.
- Usa la licencia Apache 2.0 ya incluida en el repositorio.
