# ControlLaboral V2

Control de jornada y tiempo extra (PySide6, SQLite, MVC). Corre con el Python
portatil comun del SSD: `..\PyPortable314`.

- `run.bat`: arranca la aplicacion.
- `compilar_ui.bat`: compila `.qrc` y `.ui` con los binarios reales de PySide6.
- `..\PyPortable314\python.exe -m pytest -q`: corre las pruebas.

La base de datos esta en `data/` (desarrollo) o en
`%LOCALAPPDATA%\MisApps\ControlLaboral\data\` (instalada); se puede forzar con la
variable `CONTROLLABORAL_DATA`. Nunca se versiona.

Arquitectura y decisiones: `Documentacion/03_ARQUITECTURA_TECNICA.md`.
