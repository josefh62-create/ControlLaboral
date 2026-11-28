# E0 — Esqueleto de la aplicación ControlLaboral V2

## Objetivo
Una aplicación vacía que arranca con `PyPortable314`, con la estructura aprobada en `Documentacion/03_ARQUITECTURA_TECNICA.md` §4.1, la base SQLite creada por migraciones idempotentes, el tema claro/oscuro y una ventana principal con sidebar. Es la base sobre la que se construyen E1–E4 (doc 03 §13).

## Problema y por qué
Hoy el repositorio solo tiene documentación. Antes de programar el motor (E1) y los catálogos (E2) hace falta el esqueleto común: rutas relativas al runtime, compilación de `.ui`, conexión y migraciones, `ModeloBase`/`ControladorBase` y la regla de pureza del `Dominio/`. La línea de corte del 01/01/2027 (decisión 7) exige que este esqueleto quede listo pronto.

## Alcance autorizado
- Crear en `D:\Proyectos\ControlLaboral` el árbol del doc 03 §4.1 (solo las piezas de E0), los scripts y la configuración.
- Referencia de patrón (solo lectura): `D:\Proyectos\ControlDeAlmacen` (ya en PyPortable314) y `D:\Proyectos\Mi_Tiendita`. Se copian y adaptan, sin modificarlos.
- V1 (`D:\Proyectos\app_revisar_checadas`) estrictamente de solo lectura; E0 no reutiliza código de V1.
- Fuera de alcance: lógica del motor (E1), catálogos (E2), instalador (E6), Supabase.

## Restricciones
- SSD: MVC estricto, nomenclatura `frm_/vista_/modelo_/controlador_`, UI solo en `.ui`, `uic.exe`/`rcc.exe` reales con `-g python`, rutas relativas a `..\PyPortable314`, sin venv, claro/oscuro, `QFrame`/`QGroupBox`.
- Decisiones aprobadas del doc 03 §14: `Dominio/` puro (1), BD en `%LOCALAPPDATA%\MisApps\ControlLaboral\data\` en producción y `data/` en desarrollo (4), prefijos de widgets del doc. maestro §5.2 (`qled`, 9).
- `Dominio/` no importa PySide6, sqlite3 ni la fecha del sistema (prueba de arquitectura).
- No subir a Git BD, `data/`, `logs/`, `backups/` ni archivos generados que el proyecto excluya.

## TDD y pruebas
- Modo TDD: **desactivado** (fuente: no hay configuración de TDD en el proyecto ni elección del usuario; tener pytest no lo activa). Se corren pruebas funcionales ordinarias.
- Runner: `..\PyPortable314\python.exe -m pytest` desde la raíz del repo.
- Se revisará el modo TDD antes de E1 (motor), donde sí aporta.

## Tareas
- [x] T1 — Andamiaje: árbol de carpetas de E0, `.gitignore`, `run.bat`, `compilar_ui.bat`, `.vscode/settings.json`, `requirements.txt`, `pytest.ini`, `Config/config.py` (rutas dev/prod, versión de esquema), `README.md`.
- [x] T2 — Base de datos: `Database/conexion_sqlite.py` (PRAGMAs: `foreign_keys=ON`, WAL, `synchronous=FULL`, `busy_timeout`), `Database/unidad_trabajo.py`, `Database/crear_bd.py` con `_aplicar_migraciones` y `Database/migraciones/0001_esquema_base.sql` (tabla de versión de esquema). Pruebas: migración repetible e idempotente, PRAGMAs activos, rollback de la unidad de trabajo.
- [x] T3 — Bases MVC: `Modelos/modelo_base.py` (`ModeloBase`) y `Controladores/controlador_base.py` (`ControladorBase`) adaptados del patrón de ControlDeAlmacen/Mi_Tiendita. Pruebas mínimas de `ModeloBase` con BD temporal.
- [ ] T4 — Ventana principal y tema: `Recursos/Estilos/` (base/light/dark), `ClasesComunes/temas.py`, `Vistas/frm_principal.ui` con sidebar (contenedores `QFrame`), `vista_principal.py`, `controlador_principal.py` con `modulos_disponibles` vacío, `Recursos/Imagenes/controllaboral.qrc`, `main.py`. `.ui` compilado con `compilar_ui.bat`; la app arranca en claro y oscuro.
- [x] T5 — Arquitectura: paquete `Dominio/` (con `__init__.py`), `tests/arquitectura/test_pureza_dominio.py` (AST: `Dominio/` sin PySide6/sqlite3/`datetime.now`) y prueba de dirección de dependencias entre capas.

## Criterios de aceptación (doc 03 §13, E0)
- `run.bat` arranca la ventana principal con `PyPortable314`; cambia entre tema claro y oscuro.
- `compilar_ui.bat` compila `.ui` y `.qrc` con los binarios reales.
- Ejecutar dos veces la creación de BD deja el mismo esquema y la misma versión (idempotente).
- `pytest` pasa: migraciones, unidad de trabajo, `ModeloBase`, pureza del dominio.
- `git status` de V1, ControlDeAlmacen y Mi_Tiendita sin cambios nuevos.

## Verificación (comandos)
- `..\PyPortable314\python.exe -m pytest -q`
- `compilar_ui.bat` (sin errores) y arranque manual con `run.bat` (lo prueba el usuario en la app real).
- `git -C D:\Proyectos\app_revisar_checadas status --short` igual a la base (` M config.json`, `?? APP_REVISAR_CHECADAS_TE_AEI_260720.xlsx`).

## Entrega
- Rama `feat/e0-esqueleto`, apilada sobre `docs/t4-arquitectura` (PR #3) → PR #2.
- Pronóstico: ~900 líneas de autoría (sin contar `frm_*.py` y `*_rc.py` generados) → supera el presupuesto de ~400 por PR. Estrategia de entrega `ask-on-risk`; cadena elegida por el usuario (26/11/2026): **PR apilados hacia `main`** (`stacked-to-main`).
- Cortes: **E0-1** `feat/e0-esqueleto` = T1 + T2 · **E0-2** `feat/e0-bases-mvc` = T3 + T5 · **E0-3** `feat/e0-ventana` = T4. Cadena: #2 → #3 → E0-1 → E0-2 → E0-3.
- Un commit por tarea (Conventional Commits).

## Progreso
- 2026-11-26: documento creado; referencia elegida: ControlDeAlmacen (PyPortable314). Rutas por tarea: T1–T5 delegadas (disparador: 2+ archivos no triviales y lectura de preparación de las referencias).

- 2026-11-26: T1 `eb746d1` y T2 `3fed2fb` (delegados). `pytest -W error`: 11 passed (repetido por el orquestador). `compilar_ui.bat` sin .ui/.qrc: OK. V1 y ControlDeAlmacen sin cambios. 481 líneas de autoría (sobre el ~400 orientativo; mayormente pruebas). Riesgo evaluado: alto (evaluación con 0 líneas → se trata como alto); RDD desactivado → verificador independiente. Pendiente para E4/E6: respaldo automático antes de migrar (doc 03 §11).

- 2026-11-26: verificador independiente: PASS sin bloqueos; 4 correcciones aplicadas en `4f70428` (carrera entre procesos, checksum verificado, rollback sin enmascarar errores, ruta de datos absoluta) + pruebas reforzadas. `pytest -W error`: 15 passed (repetido por el orquestador). PR E0-1 abierto.

- 2026-11-26: T3 `3d22898` y T5 `2fb0db3` (delegados) + corrección del orquestador `1011272` (Dominio podía no importarse a sí mismo). `pytest -W error`: 42 passed, 2 skipped (Servicios/Repositorios aún no existen). ControlDeAlmacen y Mi_Tiendita sin cambios. Riesgo: medio (468 líneas) → autoverificación + comprobación del orquestador, sin verificador aparte. PR E0-2 abierto.

## Siguiente paso
E0-3 (T4: ventana principal, sidebar y tema) en `feat/e0-ventana`, apilada sobre E0-2.
