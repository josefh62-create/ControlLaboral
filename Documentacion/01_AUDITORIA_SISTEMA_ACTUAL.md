# 01 — Auditoría del sistema actual (V1: `app_revisar_checadas`)

**Proyecto:** ControlLaboral V2.0 · **Documento:** 01_AUDITORIA_SISTEMA_ACTUAL · **Fecha de auditoría:** 24/11/2026
**Referencia de V1:** `D:\Proyectos\app_revisar_checadas`, rama principal, HEAD `bc7f5fd` (11/11/2026, «feat(empleados): require rest day on capture and import»), 51 commits, 128 archivos versionados.
**Plan aplicable:** `ControlLaboral_Plan_Maestro_v3.0.md`, caps. 0, 1, 2, 3, 4, 5, 13, 14, 16–19 y 22.
**Estado:** diagnóstico inicial, sin implementación. Esperar aprobación explícita antes de diseñar o codificar V2 (AGENTS.md).

## 0. Método, alcance y convenciones

- **Solo lectura.** Se usaron únicamente lectura de archivos, `grep` y comandos `git` de consulta sobre V1. No se ejecutó código ni pruebas de V1, no se abrieron sus `.db` ni sus `.xlsx`, y no se conectó ningún dispositivo.
- **Excluido:** `.claude/worktrees/` (copia duplicada), `.codegraph`, `.pytest_cache`, `__pycache__`.
- **Cobertura del código.** Leídos íntegros: `main.py`, `config.py`, `models.py`, `empresas.py`, `helpers.py`, `tiempo_extra/ClasesComunes/{calculo_te,dominio,fechas,reloj_generico,excel_sl}.py`, `tiempo_extra/Database/*`, `tiempo_extra/Modelos/*`, `tiempo_extra/Config/*`, `tiempo_extra/Vistas/vista_tiempo_extra.py` y los tramos relevantes de `forms/form_revisa_checadas.py` (≈1100 de 1390 líneas), `vista_empleados.py`, `exportar_reporte.py`, `form_editar_empresa.py` y `form_tiempo_extra_ventana.py`. **No** se auditó línea por línea: los `*_ui.py` y `*_rc.py` (código generado), los `.ui`, `style.qss`, la maquetación de `exportar_reporte.py` (solo se leyó `_construir`/`es_dia_laborable`) ni `docs/superpowers/*`.
- **Etiquetas de evidencia.** **Comprobado (ruta:línea)** = visto en el código; **Hipótesis** = inferencia no verificada ejecutando; **No localizado** = se buscó y no existe (se indica dónde).
- **Privacidad.** El documento cita rutas, símbolos y estructura de columnas; no contiene datos de empleados ni contenido de bases o Excel.
- **Rutas.** Relativas a `D:\Proyectos\app_revisar_checadas` salvo indicación.

## 1. Inventario

### 1.1 Estructura de carpetas (rama principal)

| Ruta | Contenido | Observación |
|---|---|---|
| `main.py` | Punto de entrada | Crea `QApplication`, estilo Fusion, carga `style.qss`, abre `FrmRevisarChecadas` (`main.py:61-73`) |
| raíz: `helpers.py`, `models.py`, `config.py`, `empresas.py`, `excel_helpers.py`, `fix_encoding.py` | Lógica de la app «Revisar Checadas» | `helpers.py` (1286 líneas) mezcla fechas, lectura/conversión de Excel, cálculo, catálogo y un `QMessageBox` (`helpers.py:1210`) |
| `forms/` | `form_revisa_checadas.py` (1390 líneas), `form_busca_empleado.py`, `form_admin_empresas.py`, `form_editar_empresa.py`, `form_tiempo_extra_ventana.py` y sus `*_ui.py` generados | Formularios con lógica de negocio incrustada |
| `ui/` | 5 `.ui` de la app principal | |
| `tiempo_extra/` | Submódulo «Reporte de Tiempo Extra»: `Vistas/`, `Modelos/`, `ClasesComunes/`, `Database/`, `Config/`, `Plantillas/`, `Recursos/`, `Empresas/<id>/` (BD por empresa), `te_rc.py` | Ya organizado casi como MVC; sin `Controladores/` |
| `datos/` | Contiene `catalogo_te.db` | **Hipótesis:** BD huérfana o legado; ningún `.py` la referencia (búsqueda de `catalogo_te` y `datos/` en `*.py`). No se abrió |
| `tests/` | 6 archivos de prueba | Ver 1.8 |
| `Recursos/` | Iconos y `RevisarChecadas.qrc` → `RevisarChecadas_rc.py` | |
| `docs/superpowers/` | 2 planes y 2 especificaciones (catálogo por empresa, carpeta de reportes) | No auditados en detalle |
| `odd/tasks/te-reglas-registrar.md` | Tarea ODD de V1: unificar reglas «Registrar_TiempoExtra» | Documenta la regla fuente del cálculo (ver A02) |
| Archivos sueltos | `build.ps1`, `compilar.ps1`, `RevisarChecadas.spec`, `instalador.json`, `run.bat`, `style.qss`, `AGENTS.md`, `CLAUDE.md`, `MODIFICACION DE LEJOJ CHECADOR PARA BATAB.docx` | El `.docx` es una nota de requerimientos de un usuario (ver 6.3) |
| `Empresas/` en la **raíz** | **No localizado.** Se buscó en la raíz de V1 (`ls`). El directorio multiempresa real es `tiempo_extra/Empresas/` | |
| Datos locales (no versionados) | `config.json` (modificado), `empresas.json`, `APP_REVISAR_CHECADAS_TE_AEI_260720.xlsx` (sin versionar; por su nombre, un export/archivo de trabajo) | Solo se verificó su existencia |

### 1.2 Punto de entrada y arranque

- **Comprobado:** `run.bat:9` ejecuta `"%~dp0..\PyPortable311\python.exe" main.py`; `main.py:61-73` instala `sys.excepthook`, crea la ventana principal y entra al loop de Qt. El módulo Tiempo Extra no tiene entrada propia: se abre desde el botón «Reporte de Tiempo Extra» (`forms/form_revisa_checadas.py:335-348`) y fija la BD de la empresa activa (`forms/form_tiempo_extra_ventana.py:23-35`).

### 1.3 Tecnologías y versiones

| Elemento | Valor | Evidencia |
|---|---|---|
| Lenguaje / runtime | Python 3.11.9 portátil `PyPortable311` (con PySide6 6.11.1) | `run.bat:9`; `.vscode/settings.json` (`python.defaultInterpreterPath`); `D:\Proyectos\PyPortable311\RUNTIME_VERSION.txt` = `3.11.9+PySide6-6.11.1` |
| Framework UI | PySide6, estilo Fusion + `style.qss` (un solo tema claro; no se localizó soporte de modo oscuro en `style.qss`) | `main.py:65-68` |
| Persistencia | SQLite vía `sqlite3` (solo submódulo `tiempo_extra`) + JSON (`config.json`, `empresas.json`) + Excel (openpyxl) | `tiempo_extra/Database/conexion_sqlite.py`; `config.py`; `empresas.py` |
| Excel | `openpyxl` | `excel_helpers.py:8`; `tiempo_extra/ClasesComunes/excel_sl.py` |
| PDF | `reportlab` | `forms/form_revisa_checadas.py:1049-1058`; `exportar_reporte.py:447` |
| Empaquetado | PyInstaller (`RevisarChecadas.spec`, `build.ps1`) y `instalador.json` (generador SSD) | `instalador.json`; `build.ps1:22-38` |

### 1.4 Dependencias

| Paquete | Restricción declarada | Evidencia |
|---|---|---|
| PySide6 | `>=6.5.0` (sin tope) | `requirements.txt:1` |
| openpyxl | `>=3.1.0` | `requirements.txt:2` |
| reportlab | `>=4.0.0` | `requirements.txt:3` |
| Pillow | `>=10.0.0` | `requirements.txt:4` |
| pyinstaller | `>=6.0.0` | `requirements.txt:5` |

Versiones realmente instaladas en el portátil: solo consta PySide6 6.11.1 (`RUNTIME_VERSION.txt`); las de openpyxl, reportlab y Pillow **No localizado** sin inspeccionar `PyPortable311\Lib\site-packages` (no se hizo; fuera del alcance de V1).

**Desviaciones respecto al estándar del SSD (Comprobado):**
- `.vscode/settings.json` apunta a los wrappers `Scripts\pyside6-uic.exe` / `pyside6-rcc.exe`, que `D:\Proyectos\CLAUDE.md` prohíbe (Windows App Control los bloquea). `.vscode/tasks.json` apunta a `designer.exe` con ruta **absoluta** `D:\Proyectos\...`.
- `build.ps1:8-12` depende de `.venv\Scripts\*` (prohibido en el SSD); `compilar.ps1:6-13` sí usa los binarios reales con fallback.
- No existe `compilar_ui.bat` (nombre estándar); no localizado en la raíz de V1.

### 1.5 Multiempresa

- **Comprobado:** `empresas.json` es la única fuente de verdad del catálogo de empresas y de la empresa activa (`empresas.py:19-60`; `tiempo_extra/Config/empresas.py:1-17`). Contiene 3 empresas. La BD SQLite es **una por empresa** en `tiempo_extra/Empresas/<id>/tiempo_extra.db` (`tiempo_extra/Config/empresas.py:59-72`; `Config.usar_empresa`, `tiempo_extra/Config/config.py:41-44`).
- El `location_id` de una empresa se deriva de su **posición** en la lista (`empresas.py:105-117`): reordenar o borrar empresas cambia el identificador. **Comprobado.**
- Cada empresa define su rango de fechas (`fecha_inicio`/`fecha_fin`), y el **día de inicio de semana** se infiere del `weekday()` de `fecha_inicio` (`empresas.py:120-131` y `tiempo_extra/Config/empresas.py:46-53`; default lunes). **Comprobado.**
- Eliminar una empresa solo borra su entrada JSON (`empresas.py:96-102`); su BD y sus checadas no se tocan. **Comprobado.**
- **No localizado:** separación de centro de trabajo/departamento más allá de un texto libre `departamento`/`categoria` por empleado.

### 1.6 `config.json` y `empresas.json` (solo claves)

| Archivo | Claves | Uso real |
|---|---|---|
| `config.json` | `horas_semanales_max` (mapa año→horas), `ruta_ultimo_archivo`, `actual`, `carpeta_exportacion`, `fecha_inicio`, `fecha_fin`, `fondo`, `rangos_semanales`, `tipo_semana_activo` | **Comprobado:** solo se leen `horas_semanales_max` (`config.py:59-76`) y `ruta_ultimo_archivo` (`form_revisa_checadas.py:392,402`). Las demás claves no se referencian en ningún `.py` consultado: **Hipótesis:** remanentes de versiones anteriores |
| `empresas.json` | `empresa_activa`, `empresas[]` con `id`, `nombre_largo`, `nombre_corto`, `nombre_catalogo`, `fecha_inicio`, `fecha_fin`, `reporto`, `autorizo`, `carpeta_reportes_te`, `logo_reporte_tam` (y `logo_reporte`) | `forms/form_editar_empresa.py:93-132` |

Observaciones **Comprobadas**: (1) `config.json` está **versionado en git** y V1 lo reescribe en cada selección de archivo (`config.py:38-53`), por eso aparece como modificado en `git status`; (2) la tabla legal de horas semanales vive en un JSON editable sin protección (ver A01/NL03).

### 1.7 Pruebas existentes (no ejecutadas)

Conteo estático: 34 funciones `test_*` en 6 archivos.

| Archivo | Cubre | Pruebas |
|---|---|---|
| `tests/test_horas_jornada.py` | `RutinasDeReloj.calcula_horas_jornada` (jornada entre semana, sábado 8 h, domingo/descanso todo extra, turno nocturno, fechas invertidas, sin jornada) y `parsea_hora_decimal`/`parsea_dia_descanso` | 13 |
| `tests/tiempo_extra/test_modelo_empleados.py` | `ModeloEmpleados.con_tiempo_extra` (activo/calcula_te) | 5 |
| `tests/tiempo_extra/test_empleados_descanso_obligatorio.py` | Importación Excel y formulario rechazan empleado sin día de descanso | 3 |
| `tests/tiempo_extra/test_modelo_registro_diario_alteraciones.py` | Bitácora `log_alteraciones_reloj` y `campos_alterados` | 8 |
| `tests/tiempo_extra/test_vista_empleados_logica.py` / `_widget.py` | Regla `activo`↔`calcula_te` | 5 |

**No cubierto (Comprobado por ausencia):** `calculo_te.arma_dia` y `neto_semana`; `carga_checadas_del_empleado` y la deduplicación de 30 min; los conversores de formato (`Fichaje`, `Timecard`); `reloj_generico.cargar`; `lista_semanas_laboradas`; `config.horas_max_para_anio`; exportación a Excel/PDF; cálculo semanal. Es decir, **la regla de compensación semanal de faltantes y la lectura de archivos no tienen pruebas**. Las pruebas existentes son de caracterización parcial y pueden reutilizarse como punto de partida (ver matriz 13).

### 1.8 Distribución

`instalador.json` declara v1.0.0, entry `main.pyc`, excluye `tests`, `docs`, `*.db` (`instalador.json:7-13`). **Comprobado.** `RevisarChecadas.spec:8` empaqueta solo `style.qss` como dato.

## 2. Arquitectura actual y cercanía al MVC del SSD

### 2.1 Capas y módulos

| Capa MVC del SSD | App principal («Revisar Checadas») | Submódulo `tiempo_extra/` |
|---|---|---|
| **Vista** | `forms/form_*.py` + `*_ui.py` (generados desde `ui/*.ui`) con la lógica de vista **y de negocio** dentro | `Vistas/frm_*.ui`, `ui_*.py`, `vista_empleados.py`, `vista_tiempo_extra.py` |
| **Modelo** | **No localizado.** Dataclasses en `models.py`; lógica de datos en `helpers.py` (lectura Excel) | `Modelos/modelo_base.py`, `modelo_empleados.py`, `modelo_registro_diario.py` (CRUD genérico sobre `OperacionesSqlite`) |
| **Controlador** | **No localizado** (`CLAUDE.md` de V1 lo admite como pendiente) | **No localizado**: las vistas llaman directo a los modelos |
| **Dominio / cálculo** | `RutinasDeReloj.calcula_horas_jornada` (`helpers.py:399`) delega en el módulo siguiente | `ClasesComunes/calculo_te.py` (funciones puras: `arma_dia`, `calcula_tiempo_extra`, `neto_semana`) |
| **Persistencia** | JSON + Excel | SQLite con `Database/conexion_sqlite.py` (conexión por operación, `with_connection`) y `crear_bd.py` (DDL idempotente + `_migrar`) |

### 2.2 Valoración

| Aspecto | Valoración | Evidencia |
|---|---|---|
| Separación MVC | **Parcial**: el submódulo tiene Modelos/Vistas con nomenclatura del SSD (`modelo_empleados.py`, `vista_empleados.py`, `frm_empleados.ui`); la app principal es monolítica | `CLAUDE.md` de V1 («falta migrarla a MVC completo»); `forms/form_revisa_checadas.py` (cálculo, E/S, exportación y PDF en un solo archivo) |
| Motor de cálculo desacoplado | **Parcial**: `calculo_te.py` es Python puro (sin Qt ni SQLite), pero (a) recibe horas decimales sueltas en vez de contexto explícito (norma, tolerancias), (b) está duplicado en la ruta de revisión vía `helpers.py:428`, (c) la lógica semanal vive en la vista (`vista_tiempo_extra.py:423-437`, `:526-637`) | `calculo_te.py:89-176` |
| UI en `.ui` (Designer) | **Cumple** en las pantallas inspeccionadas (5 `.ui` + 3 en `tiempo_extra/Vistas`); hay tablas pobladas por código (normal) y estilos/colores por código (`vista_tiempo_extra.py:46-55`, `helpers.py:1233-1243`) | `ui/`, `tiempo_extra/Vistas/*.ui` |
| Modo claro/oscuro | **No cumple** (un solo QSS claro; colores literales por código) | `style.qss`; `vista_tiempo_extra.py:46-55` |
| Nomenclatura de widgets | **Parcial**: la app principal usa `btn*/txt*/dgv*/cmb*` (p. ej. `btnCalcular`, `dgvChecadasReloj`); el submódulo usa `btn_guardar`, `txt_buscar`, `tabla` (snake_case sin prefijo del estándar) | `form_revisa_checadas.py:317-329`; `vista_tiempo_extra.py:113-121` |
| Layouts con `QFrame`/`QGroupBox` | No verificado (no se inspeccionaron los `.ui`). **Hipótesis:** parcial (se ve `gpbPanelPrincipal` en el form principal) | `form_revisa_checadas.py:499` |
| Runtime SSD y compiladores | **Parcial**: `run.bat` correcto; settings/tareas/`build.ps1` desviados (ver 1.4) | |
| Migraciones de esquema | **Cumple** el patrón idempotente (`_migrar`, `ALTER TABLE ... ADD COLUMN`), sin tabla de versiones de esquema | `crear_bd.py:100-118` |
| Concurrencia/durabilidad SQLite | Solo `foreign_keys=ON`; **No localizado** `journal_mode`, `synchronous`, `busy_timeout`, `integrity_check`, backup API | `conexion_sqlite.py:78`; `crear_bd.py:133` |

## 3. Hallazgos A01–A10 del plan (cap. 3)

Estados: cumple / parcial / no cumple / no aplica / pendiente. «Riesgo» en escala Alto/Medio/Bajo respecto de los requisitos de V2.

### A01 — Constantes laborales, multiplicaciones por días y textos fijos

**Inventario exhaustivo (Grep sobre `*.py` no generados de V1).** Se buscaron: 48, 46, 44, 42, 40, 480, 540, 2880, 0.33, 0.5, 18, 24, 30, 10, 60, 3600, 8, 9, 12, nombres de días, «sábado», «domingo» y `weekday()`. No se encontraron 480, 540, 2880, 9, 12 como constantes laborales (solo coincidencias de maquetación, p. ej. tamaños de fuente), ni multiplicaciones `×6`/`×5` días.

| # | Ruta:línea y símbolo | Valor | Propósito | Equivale en el plan | Comentario |
|---|---|---|---|---|---|
| K01 | `config.py:26-28` `DEFAULT_HORAS_MAX` | `{2026:48, 2027:46, 2028:44, 2029:42, 2030:40}` | Umbral semanal por año (reforma) | Cap. 2 (solo la columna «ordinaria semanal»); no tiene art. 66/68 | Tabla por **año calendario** con corte 1/ene, sin vigencia exacta del decreto (1/may/2026) ni versionado |
| K02 | `config.py:64` `horas_max_para_anio` | `48.0` | Valor por defecto si la tabla viene vacía | NL04 (debe bloquear, no asumir) | Asume 48 sin bloquear |
| K03 | `config.py:68-71` | clamp a extremos | Años <2026 → 48; >2030 → 40 | Cap. 2 («hasta nueva reforma») | Para 2026-ene–abr aplica 48 (correcto en ordinaria), pero el régimen anterior de extras no existe |
| K04 | `forms/form_revisa_checadas.py:954-956` `_recalcular_totales` | `max(0, total_trab − umbral)` | «Horas extras jornada oficial» semanal | Cap. 5.3 (solo ordinaria; no clasifica doble/triple) | **Informativo**: solo se muestra en `txtTotalHrsExtSem` (:957); no se exporta ni se usa para el cálculo de T.E. (confirmado por lectura del flujo) |
| K05 | `form_revisa_checadas.py:139-143` | texto «48 hrs hasta 2026; baja 2 hrs por año hasta 40 hrs en 2030» | Tooltip fijo | HO07 | Texto legal fijo (duplicado de K01) |
| K06 | `calculo_te.py:36` `HORAS_FINDE` | `8.0` | Jornada fija de sábado y domingo (no descanso) | HO01, cap. 4.2 (el sábado de 2027 son 6 h, etc.) | **Contradice** la reforma: la jornada ordinaria del sábado/domingo no es fija de 8 h; se usa para decidir qué es extra |
| K07 | `calculo_te.py:133-134`; `helpers.py:422` `es_finde = dow in (0, 6)` | Sáb/Dom = fin de semana | Selección del umbral de 8 h | HO05/HO01 (días no programados ≠ fin de semana) | Presupone semana L–V con sábado/domingo especiales |
| K08 | `calculo_te.py:111-112` `calcula_tiempo_extra` | `round(entrada + 0.33)`; `round(salida − 0.33)` | «Tolerancia» y redondeo a hora entera | Cap. 4.3 y RE07 | Ver A04: no es tolerancia 0–15, redondea a horas enteras |
| K09 | `helpers.py:412-413` `calcula_horas_jornada` | `+0.33` / `−0.33` | Solo valida orden entrada/salida; el cálculo real lo hace `calculo_te` | — | Constante duplicada (K08) |
| K10 | `helpers.py:425-426` | `jornada_ent, jornada_sal = 0.0, 8.0` | Jornada por defecto si el catálogo no la trae | **HO06: «no inventar 8 h por defecto»** | **No cumple** HO06 (documentado en `tests/test_horas_jornada.py:69-72`) |
| K11 | `helpers.py:520-526`; `reloj_generico.py:26,101` `_UMBRAL_DOBLE_PUNCH_HORAS` | `0.5` h (30 min) | Descarta checadas a ≤30 min de la anterior (mismo día) | Cap. 5.1.2 y cap. 14 (conservar checadas originales, incluso duplicadas) | Descarta evidencia en memoria; no se persiste cuáles |
| K12 | `form_revisa_checadas.py:711` | `> 18` horas | Aviso «Horas excesivas» | AL07 (12 h totales/día), AL05 | Umbral arbitrario distinto a 12 h; solo un `msgbox` |
| K13 | `helpers.py:76` | `/ 3600.0` | Conversión segundos→horas decimales (conserva segundos) | RE07 | Difiere de `fechas.py:34` que descarta segundos (ver 6.1) |
| K14 | `helpers.py:375` `parsea_hora_decimal` | `0 < v < 1` → `v·24` | Interpreta fracción de día de Excel | — | Ambigüedad: `0.5` se interpreta como 12:00, no como 0.5 h |
| K15 | `helpers.py:388-396`; `models.py:27`; `crear_bd.py:29` | `0..6` Domingo=0 | Convención C# `DayOfWeek` para descanso | HO05 | Un solo día de descanso por empleado (ver A03) |
| K16 | `helpers.py:168,171`; `fechas.py:97-121` `lista_semanas_laboradas` | `timedelta(days=7)`, `% 7`, `+6` | Genera semanas de 7 días con inicio configurable | RE01 | Correcto y reutilizable; semana = día de `fecha_inicio` de la empresa |
| K17 | `dominio.py:33-38`; `models.py:84-93` `NOMBRES_DIA_C_SHARP`, `NOMBRES_DIA_CORTO` | «Domingo … Sábado», «Dom … Sáb» | Textos de días | — | Nombres de días fijos y duplicados en 2 módulos (`models.py` y `dominio.py`) |
| K18 | `helpers.py:99-103` | mapa «ene…dic» → 1..12 | Parseo de textos de periodo | — | Solo meses abreviados en español |
| K19 | `form_revisa_checadas.py:931-932` `_MESES_ABBR`; `exportar_reporte.py:21` `_MESES` | meses abreviados | Etiquetas de reportes | — | Duplicados |
| K20 | `exportar_reporte.py:82-92` `es_dia_laborable` | «cualquier día que no sea descanso es laborable» | Detectar falta | HO05 | No distingue festivo, vacaciones, incapacidad ni día no programado |
| K21 | `form_revisa_checadas.py:861-868` | `vacias_consecutivas < 3` | Detectar fin de datos al exportar | — | Heurística de fin de hoja |
| K22 | `helpers.py:326`, `:335`, `crear_bd.py` columnas, `modelo_empleados.py:135-138` | Columnas Excel 5/6/7/8, «DIA DE DESCANSO», «HORA ENTRADA», «HORA SALIDA» | Layout del catálogo | Cap. 13.2 | Posicional + por encabezado (ver §5) |

No se localizaron: tabla de límites art. 66/68 (9 h, 4 h, 3 h), jornada nocturna/mixta (480/420/450 min), franja nocturna 06:00–20:00, ni descanso de 30 min. **No localizado** (buscado en `*.py` no generados con los patrones `480|420|450|540|2880|60`).

- **Comportamiento observado (Comprobado):** la única constante «legal» es la tabla de horas semanales (K01) y se usa solo para mostrar un excedente informativo. El cálculo de tiempo extra no depende de ningún límite legal: depende de la **jornada del catálogo** y de `HORAS_FINDE`.
- **Requisito esperado:** NL01–NL06: catálogo versionado, selección por fecha efectiva, no editable por usuarios operativos, bloqueo del cálculo definitivo si falta versión.
- **Estado:** **no cumple** (K01–K03, K06, K10 y K12).
- **Riesgo:** **Alto** — cualquier usuario con acceso a `config.json` puede alterar el umbral; el sábado fijo de 8 h genera extras que dejarían de serlo (o viceversa) en 2027 en adelante.
- **Propuesta V2:** normatividad como datos versionados en SQLite (NL) con restricciones, vigencia por fecha trabajada y alta con fundamento/autorizador; eliminar K06/K10; HORAS_FINDE se sustituye por horarios por día y vigencia (HO01); el umbral informativo K04 se sustituye por la clasificación semanal doble/triple del cap. 5.3.

### A02 — Cálculo diario/semanal y orden de clasificación

Hay **dos flujos de revisión** que comparten el cálculo diario pero difieren en entradas y presentación.

**Flujo 1 — Revisión checada por checada («Revisar Checadas»), `forms/form_revisa_checadas.py`:**

1. Seleccionar empresa y semana (`:288-310`, semanas por `lista_semanas_laboradas`, `helpers.py:167-202`).
2. `_on_buscar_archivo` (`:382-501`): abre un `.xlsx/.xls` (`QFileDialog`, `:390-394`); lo reconoce como **canónico** (`Department/Name/No./Date/Time`) o como reporte (`Ver Fichaje de Asistencia`, `Timecard`/`Informe de tarjetas horarias`, `NGTeco`, `Employee Timecard`, `RELOJ CEDIS`) (`helpers.py:209-253`); valida que la **fecha mínima del archivo coincida con el inicio de la semana elegida** (`:433-459`); si no es canónico, lo **convierte y escribe un nuevo `.xlsx`** `ACS{NN}_{EMPRESA}_{YYMMDD}_A_{YYMMDD}.xlsx` junto al original (`helpers.py:550-768`, nombre en `:565-571`).
3. `_on_buscar_nombre` (`:503-566`): carga el catálogo de empleados (Excel) que **debe estar en la misma carpeta** del archivo de checadas con el nombre `nombre_catalogo` de la empresa (`:533-547`).
4. `_on_empleado_encontrado` (`:568-617`): `carga_checadas_del_empleado` (`helpers.py:470-541`) filtra por número (col 3) o nombre, **descarta dobles checadas ≤30 min**, y la vista las restringe a `[inicio, fin]` de la semana (`:602-606`).
5. El operador marca con las teclas **E** y **S** una fila como entrada y otra como salida (`:627-656`), y pulsa Calcular (`:658-720`).
6. `calcula_horas_jornada` (`helpers.py:399-434`) toma el día **de la fecha de entrada**, determina `es_descanso` y `es_finde`, y llama a `calcula_tiempo_extra` (`calculo_te.py:89-161`).
7. «Enviar a revisadas» (`:722-794`) guarda el turno en memoria (`EmpleadoRevisado`), elimina las dos checadas usadas de la lista, y recalcula totales (`:939-957`); advertencia a >18 h (`:711`).
8. «Exportar» (`:796-928`) añade un bloque de 7 filas al libro `RTE_{EMPRESA}_SEM{NN}_{ini}_A_{fin}.xlsx` solo si `horas_extras > 0`; pregunta si sobrescribe un bloque existente (`:839-855`). «PDF» (`:1038-1163`) **relee el Excel exportado** y genera el PDF.

**Flujo 2 — Reporte de Tiempo Extra por empleado (`tiempo_extra/Vistas/vista_tiempo_extra.py`):**

1. Pestañas Catálogo/Tiempo extra sobre la BD SQLite de la empresa (`form_tiempo_extra_ventana.py:23-52`); lista solo empleados `calcula_te = 1 AND activo = 1` (`modelo_empleados.py:81-94`).
2. Opcional: cargar el archivo canónico (`reloj_generico.cargar`, `reloj_generico.py:62-111`): agrupa por **(número, fecha calendario)** (`:91`), ordena y descarta checadas ≤30 min (`:96-104`).
3. `_precarga_reloj` (`:279-287`) reduce cada día a `[entrada, salida]` con `arma_dia` (`calculo_te.py:68-86`): 0 checadas → vacío; 1 checada → al lado más cercano de la jornada; 2+ → **la más temprana y la más tardía** (se ignoran las intermedias).
4. El supervisor puede editar las horas «autorizadas» (`entrada_aut`/`salida_aut`) en una grilla de 7 días (`:484-637`) y guardar (`:639-658`) en `registro_diario` (`modelo_registro_diario.py:36-69`); si hay reloj cargado y el valor difiere, se inserta una fila de auditoría (`:660-674`).
5. Totales: `calcula_tiempo_extra` por día y `neto_semana` (`calculo_te.py:164-176`): **T.E. neto = max(0, ΣT.E. diario − Σfaltante)**; solo se reportan empleados con T.E. neto > 0 (`exportar_reporte.py:95-175`, `_construir`).

**Regla diaria de `calcula_tiempo_extra` (`calculo_te.py:89-161`), en el orden en que se evalúa:**

| Paso | Regla | Línea |
|---|---|---|
| 1 | Sin entrada ni salida → día vacío (0) | `:103-104` |
| 2 | Falta un lado → `incompleto`, 0 horas | `:106-109` |
| 3 | `adj_ent = round(entrada + 0.33)`; `adj_sal = round(salida − 0.33)`; si `adj_sal < adj_ent` suma 24 (cruce de medianoche) | `:111-114` |
| 4 | `horas_trabajadas = adj_sal − adj_ent` (enteras) | `:116-119` |
| 5 | Día de descanso del catálogo → **todas** las horas son extra | `:121-127` |
| 6 | Sábado/domingo (no descanso) → umbral fijo `HORAS_FINDE` = 8 h; otro día → `jornada_sal − jornada_ent` (ajusta +24 si la jornada cruza medianoche) | `:133-148` |
| 7 | `extra = horas − umbral`; si `>0` es T.E.; si no y trabajó algo, `faltante = umbral − horas` | `:149-160` |
| 8 | Semana: el `faltante` se **descuenta** del T.E. total (sin bajar de 0) | `:164-176` |

**Ejemplos reproducibles** (jornada de catálogo 07:00–15:00, día entre semana no descanso; se reprodujo la fórmula del código en un script aislado fuera de V1, sin ejecutar V1):

| Checadas reales | Presencia real | Horas que calcula V1 | T.E. V1 | Observación |
|---|---|---|---|---|
| 07:00–15:00 | 8,00 h | 8 | 0 | |
| 06:40–15:00 | 8,33 h | 8 | 0 | Se pierden 20 min previos |
| 06:10–15:00 | 8,83 h | 9 | 1 | Entra a las 06:10: cuenta desde 06:00 |
| 06:11–15:00 | 8,82 h | 8 | 0 | Un minuto después, cuenta desde 07:00 y **desaparece** la hora extra |
| 07:10–15:00 | 7,83 h | 8 | 0 | Hasta 10 min tarde, sin faltante |
| 07:11–15:00 | 7,82 h | 7 | 0 (faltante 1) | 11 min tarde cuesta una hora completa de faltante |
| 07:00–15:49 | 8,82 h | 8 | 0 | Hasta :49 no cuenta la hora siguiente |
| 07:00–15:50 | 8,83 h | 9 | 1 | A las :50 cuenta una hora |
| 07:00–16:49 / 16:50 | 9,82 / 9,83 h | 9 / 10 | 1 / 2 | Salto de 1 h por 1 min |

Conclusión **Comprobada**: V1 no mide minutos; redondea cada día a **horas enteras** con un sesgo +0,33/−0,33 h (≈ 20 min). Esto incumple RE07 («no redondear cada intervalo en perjuicio del trabajador»), TO05 y TO06, y hace el resultado altamente sensible a 1 minuto. **Hipótesis:** cuando la decimal conserva segundos (`helpers.py:76`), un valor exacto de `n+0,17 h` podría caer en un empate de `round` (que redondea a par), dando resultados distintos en entrada 06:10:12 y 07:10:12; no se verificó ejecutando.

- **Estado:** **no cumple** (cap. 5): no hay segmentación por horario/descansos/vigencias, ni clasificación doble/triple, ni tope diario/semanal legal; la compensación de faltantes contra extras (`neto_semana`) contradice §1.1 («No compensar automáticamente horas extras de un día con faltantes de otro») y cap. 5.3 («Mantener faltantes separados»).
- **Riesgo:** **Alto**.
- **Propuesta V2:** motor puro por minutos o segundos enteros con segmentación de intervalos (cap. 5.2–5.3); reutilizar de V1 (a) la estructura de «resultado diario con banderas» (`DiaTE`), (b) la lógica de cruce de medianoche, (c) la convención de color para incidencias, (d) las pruebas de `test_horas_jornada.py` como **pruebas de caracterización** (no como oráculo legal).

### A03 — Horarios, asignaciones, días de descanso y vigencias

- **Comprobado:** el horario de cada empleado son **tres columnas** en `empleados` — `hora_entrada_jornada`, `hora_salida_jornada`, `dia_descanso` (`tiempo_extra/Database/crear_bd.py:37-51`); equivalen a `Empleados` en `models.py:21-30` para el catálogo Excel. Un único bloque de horas para todos los días hábiles, un único día de descanso (obligatorio desde `bc7f5fd`; `vista_empleados.py:177-213`, `modelo_empleados.py:96-160`).
- **No localizado:** horarios por día, turnos partidos, descansos computables/no computables, tipo de jornada (diurna/nocturna/mixta), vigencia/historial de asignación, centro, zona horaria, referencia de acuerdo (búsqueda de tablas en `crear_bd.py` y de campos en `models.py`).
- **Consecuencias (Comprobado):** cambiar la jornada de un empleado reescribe la fila (`modelo_base.actualizar`) y **modifica retroactivamente** el cálculo de semanas anteriores, porque el T.E. se recalcula en pantalla con el catálogo actual (`vista_tiempo_extra.py:423-437`) y solo se guardan las horas autorizadas (`registro_diario`).
- **Estado:** **no cumple** (HO01–HO07).
- **Riesgo:** **Alto**.
- **Propuesta V2:** entidades Horario / HorarioDia / AsignaciónHorario con vigencia; reutilizar de V1 el **parseo y validación de hora HH:MM** (`FuncionesDT.validar_hhmm`, `fechas.py:69-95`) y la validación de formulario.

### A04 — Tolerancias y redondeos

- **Comprobado:** una sola regla fija e interna: +0,33 h a la entrada y −0,33 h a la salida seguidos de `round()` a hora entera (`calculo_te.py:111-112`); doble checada ≤30 min descartada (`helpers.py:520-526`; `reloj_generico.py:101`). No existe configuración por empresa/horario, ni vigencia, ni límite 0–15, ni distinción entre diferencia real y administrativa.
- **Efecto sobre tiempo real:** reduce o aumenta tiempo efectivo hasta ~50 min por jornada (ver tabla A02); `fechas.py:29-34` descarta segundos deliberadamente («la unidad del reloj es el minuto»).
- **Estado:** **no cumple** TO01–TO07.
- **Riesgo:** **Alto**.
- **Propuesta V2:** política de tolerancias 0–15 min, entera, por empresa/centro/horario con vigencia, que registre «diferencia real» y «diferencia administrativa» por separado sin alterar el evento.

### A05 — Importación y emparejamiento de checadas

Resumen (detalle en §4):
- **Comprobado:** V1 **no se conecta al reloj**. Lee archivos Excel exportados desde el software del reloj (formatos canónico y 4 formatos de reporte). Sin lectura ni borrado de registros del dispositivo.
- **Emparejamiento:** manual (teclas E/S, Flujo 1) o por heurística «más temprana/más tardía por día calendario» (`arma_dia`, Flujo 2). **No** emparejan secuencias entrada/salida/comida ni turnos nocturnos que cruzan fecha en el Flujo 2.
- **Idempotencia y evidencia:** no se persisten las checadas; no hay lotes, clave de origen ni huella de archivo. Dobles checadas ≤30 min se descartan en memoria.
- **Zona horaria:** **No localizado** (los datetimes son «naive»; Excel con locale es-MX, `helpers.py:789-797`, `:1157-1182`).
- **Estado:** **no cumple** (cap. 5.1 y cap. 14: persistencia inmutable de originales, lotes, zona horaria).
- **Riesgo:** **Alto**.

### A06 — Alertas y validaciones legales

- **Comprobado:** solo hay validaciones de captura y avisos: «Horas excesivas» si >18 h (`form_revisa_checadas.py:711`); «Entrada mayor a salida» (`:682-690`); «Horas iguales» (`:676-680`); «Registro duplicado» por misma entrada (`:739-743`); «Inconsistencia en catálogo» si difieren nombres (`:583-600`); día incompleto en amarillo y falta en rojo (`vista_tiempo_extra.py:589-607`); catálogo sin descanso (`modelo_empleados.py:150-160`). Todo se muestra de forma síncrona a quien captura.
- **No localizado:** AL01–AL12 (límites legales, art. 66/68, descanso semanal AL08, horario futuro AL09, deduplicación de alertas, destinatarios).
- **Estado:** **no cumple** (solo AL10 parcial: checada incompleta).
- **Riesgo:** **Medio-Alto**.
- **Propuesta V2:** servicio de alertas derivado de NL; reutilizar de V1 el **esquema de colores** (falta/incompleta/corto/alterado) y los avisos de integridad.

### A07 — Correcciones y autorizaciones

- **Comprobado:** (1) El supervisor puede **editar libremente** entrada/salida «autorizadas» de cualquier día (`vista_tiempo_extra.py:484-637`); (2) `ModeloRegistroDiario.guardar` hace **upsert/DELETE**: sobrescribe el valor previo y elimina la fila si ambos son vacíos (`modelo_registro_diario.py:36-58`); (3) la bitácora append-only `log_alteraciones_reloj` (`crear_bd.py:82-92`) solo se escribe si **había reloj cargado en la sesión** (`vista_tiempo_extra.py:660-674`; retorno en `:663`), por lo que una captura manual sin reloj **no deja huella**; (4) el «usuario» registrado es el texto `reporto` de la **empresa**, no un usuario autenticado (`:668`); (5) **No localizado**: roles, permisos, autorizador, estados pendiente/autorizado/rechazado, evidencia, conformidad del trabajador.
- **Tensión con el plan:** el plan (cap. 14) establece que las checadas originales no se modifican ni se agregan manualmente. V1 las trata como **borrador editable** y reemplaza la hora, lo que cap. 14 sustituye por incidencias separadas.
- **Estado:** **no cumple** (cap. 14, 16–18).
- **Riesgo:** **Alto**.
- **Propuesta V2:** conservar la idea de bitácora append-only (patrón reutilizable) pero para incidencias en entidad distinta (cap. 14) y con usuario real.

### A08 — Reportes, exportación e integraciones

| Salida | Ruta:símbolo | Columnas/estructura | Unidades | Dependencias |
|---|---|---|---|---|
| Excel «bloque por empleado» (Flujo 1) | `form_revisa_checadas.py:796-928` `_on_exportar_excel` | Bloques de 7 filas: Nombre, Categoría, días L–D, hora entrada, hora salida, total horas día, horas extras día, totales | Horas decimales enteras; HH:MM | openpyxl |
| PDF de ese Excel | `:1038-1163` `_on_imprimir_pdf` (+`_leer_bloques_reporte :993`) | Misma estructura | idem | reportlab; `os.startfile` (`:1152`, solo Windows) |
| Excel/PDF «TE semanal» (Flujo 2) | `exportar_reporte.py:235` `exportar_excel`, `:447` `exportar_pdf`, `_construir :95` | Concentrado por empleado: por día H. ENT., H. SAL., T.E.; total; HRS. DESC.; Autorizó (nombre corto de empresa) | Horas con 2 decimales (valores enteros) | openpyxl, reportlab |
| Conversión de formatos | `helpers.py:550-768,854-905,1005-1086` | Genera `ACS*.xlsx` canónico | — | openpyxl |

- **Integraciones:** no hay API, servidor ni exportación a nómina; solo archivos. Las firmas son campos de texto `reporto`/`autorizo` en `empresas.json` (sin firma, folio ni versión).
- **No localizado:** folio, versionado, reimpresión exacta, acta, exportación para autoridad (cap. 15), consulta histórica (cap. 18).
- **Estado:** **parcial** (existen reportes semanales utilizables como referencia de maquetación; faltan requisitos de actas/histórico/folio).
- **Riesgo:** **Medio**. El PDF del Flujo 1 depende de reabrir el Excel (frágil: `_buscar_bloque_existente`, `:959-984`, identifica bloques por texto).

### A09 — Resultados históricos y cierres

- **Comprobado:** V1 **no almacena resultados calculados** ni la versión de reglas. En SQLite solo se guardan `entrada_aut`/`salida_aut` (`crear_bd.py:60-67`) y la bitácora; el resto se recalcula con el catálogo y el código vigentes (`vista_tiempo_extra.py:423-437`). Los reportes `RTE_*.xlsx` y `TE_*.xlsx` son los únicos «cierres» y viven en carpetas del usuario.
- **No localizado:** cierre de semana, bloqueo de periodo, huella/hash, versión de norma o de política aplicada, reproducción de un cálculo anterior (búsqueda de tablas de resultados y campos de versión en `crear_bd.py` y `modelo_*.py`).
- **Estado:** **no cumple** (A09; cap. 1.1: «aplicar la versión de las reglas a la fecha trabajada»).
- **Riesgo:** **Alto**: cambiar jornada de catálogo, código o `config.json` altera cálculos históricos al reabrirlos.

### A10 — Seguridad, rendimiento y recuperación

- **Seguridad (Comprobado):** sin autenticación, roles ni permisos; `config.json`/`empresas.json` en claro y editables; empleados con **borrado físico** (`vista_empleados.py:236-248` → `ModeloBase.eliminar` → `DELETE`), sin baja lógica con historial ni reactivación; `activo` existe pero no preserva historial (`crear_bd.py:48`). Consultas con parámetros enlazados en valores; los nombres de tabla/columna se interpolan en f-strings desde código propio (`conexion_sqlite.py` `insertar/actualizar/consulta_dinamica`); **Hipótesis:** riesgo bajo mientras no reciban texto del usuario como nombre de columna.
- **Integridad de datos (Comprobado):** `PRAGMA foreign_keys=ON` pero **sin ninguna FK ni CHECK** declarados (`crear_bd.py:37-95`); `UNIQUE(numero)` por BD; el `numero` del empleado es a la vez el **código del reloj** (sin relación separada con vigencias, contra cap. 13.1).
- **Recuperación:** **No localizado** en código: respaldo, restauración, `integrity_check`, WAL/`synchronous`, backup API; BD en la carpeta de la app (`tiempo_extra/Empresas/<id>/`). `.gitignore` excluye `*.db` y respaldos (positivo). **Comprobado por listado de directorio (solo nombres):** existen copias manuales junto a las BD (`tiempo_extra_respaldo_<fecha>.db`, `*.db.bak_debug_<fecha>`), es decir, el respaldo es una copia de archivo hecha a mano, en la misma carpeta y sin manifiesto; **Hipótesis:** no consistente si hubo escrituras en curso.
- **Código muerto (Comprobado, 0 referencias fuera de su definición):** `FuncionesDT.obtiene_fechas_semana_laboral`, `hora_redondeada`, `TrabajoConArchivos.copiar_archivo`, `ModuloDeClases.proxima_fila_vacia` y `configurar_dgv_columnas` (`helpers.py`), y `fix_encoding.py` solo lo invocan los scripts de compilación.
- **Rendimiento (Hipótesis):** acceso fila por fila a openpyxl (`get_cell_value_as_*`) y escaneos lineales por empleado (`busca_fila_empleado_por_numero`, `helpers.py:461-467`) → O(empleados × filas) por selección; aceptable para pocos empleados, no medido.
- **Estado:** **no cumple** (A10; cap. 22).
- **Riesgo:** **Alto** para datos de producción.

## 4. Lectura del reloj (A05 — crítico, cap. 0)

### 4.1 Respuesta directa

**V1 no lee el reloj. No consume ni borra registros del dispositivo: no hay en V1 ningún código de comunicación con él.**

- **Comprobado.** Búsqueda en todos los `*.py` no generados de V1 (excluyendo `.claude/worktrees/`) con los patrones `socket|pyzk|zk|tcp|serial|requests|urllib|http|usb|sdk|dll`: **sin coincidencias en código de lectura de dispositivo**. Las únicas entradas de datos son archivos `.xlsx/.xls` elegidos con `QFileDialog` (`form_revisa_checadas.py:390-394`, `vista_tiempo_extra.py:306-309`).
- **Comprobado:** el único «origen» operativo son archivos exportados por el software del reloj; nada garantiza (ni V1 comprueba) cómo se generaron esos archivos.
- **No localizado (y crítico para V2):** el modelo de reloj, el protocolo y si **el software de exportación** consume o borra los registros en el dispositivo. Esto **no puede determinarse desde el código de V1**. La nota `MODIFICACION DE LEJOJ CHECADOR PARA BATAB.docx` es de requerimientos, no de protocolo (ver 6.3). Cap. 0: no conectar un segundo importador a un dispositivo hasta aclararlo con el propietario (pregunta Q01).
- **Consecuencia para V2:** el primer adaptador debe ser **«importar archivo de checadas»** (mismo formato que ya produce el flujo actual), no conexión directa, hasta verificar el protocolo.

### 4.2 Formatos de entrada y normalización

| Formato | Detección | Estructura (columnas, sin datos) | Conversión | Ruta |
|---|---|---|---|---|
| **Canónico** | Fila 1: B=`Name`, C=`No.`, D=`Date/Time` | A=Departamento, B=Nombre, C=Número, D=Fecha/hora, E=`Location ID` (solo en convertidos) | Ninguna | `helpers.py:209-225`; `reloj_generico.py:44-59` |
| **Ver Fichaje de Asistencia** | Fila 2: A «id de persona», B «nombre», C «fecha», D «asistencia/fichaje» | A ID, B Nombre, C Fecha (MM/DD/YYYY con fallbacks), D Hora; orden descendente | `_convertir_fichaje_asistencia` ordena por (No., fecha-hora) | `helpers.py:810-905` |
| **Timecard / Informe de tarjetas horarias** (ES/EN) | Título en fila 1 o bloque «Empleado» + «Fecha/ENTRADA/SALIDA» | Bloques por empleado: «Nombre (número)», filas día con ENTRADA/SALIDA; turno partido en 2 filas | `_convertir_timecard_blocks` genera hasta 2 checadas por fila y arrastra la última fecha | `helpers.py:931-1086` |
| **NGTeco / Employee Timecard / RELOJ CEDIS** | Nombre de hoja, o `YYYYMMDD-YYYYMMDD` en D2 + «Empleado» en A3 | Cols detectadas por encabezado (fecha/hora/nombre/número/depto) | Rama genérica en `convertir_reporte_a_reloj` | `helpers.py:228-253,583-768` |

- **Claves de identidad:** número de empleado (col C) y, si no coincide, **búsqueda por nombre** (`carga_checadas_del_empleado`, `helpers.py:480-486`). El plan (cap. 13.1) prohíbe asignar por aproximación de nombre: **no cumple** (se cae a nombre si el número no se encuentra).
- **Fechas/horas:** múltiples formatos (`_parse_datetime_flexible`, `helpers.py:1157-1182`, con meridiano es-MX «a. m./p. m.», `:789-797`); valores sin zona horaria.
- **Efecto lateral:** convertir un reporte **escribe un archivo nuevo** en la carpeta del archivo origen (`helpers.py:565-571`); no modifica el original.
- **Validación de periodo:** el archivo debe iniciar el mismo día que la semana seleccionada (`form_revisa_checadas.py:445-459`; `fecha_inicio_archivo`, `helpers.py:256-273`); las checadas fuera de semana se ignoran (`:602-606`).

### 4.3 Emparejamiento de checadas

| Flujo | Mecanismo | Limitaciones (Comprobado) |
|---|---|---|
| 1 (checada por checada) | Humano marca E y S sobre la lista; admite entrada y salida en fechas distintas (`:745-751`) | Manual; un turno por pareja; no fuerza orden; el total semanal es suma de turnos revisados |
| 2 (TE por empleado) | `arma_dia`: primera y última checada del **día calendario**; 1 checada → lado más cercano a la jornada (`calculo_te.py:54-86`) | Ignora intermedias (comida); un turno nocturno (22:00–06:00) se parte en 2 días incompletos porque se agrupa por fecha (`reloj_generico.py:91`); **Hipótesis:** el operador lo corrige a mano |

## 5. Excel de empleados (catálogo)

Hay **dos catálogos coexistentes** (duplicidad):

| Aspecto | Catálogo Excel por carpeta (Flujo 1) | Catálogo SQLite por empresa (Flujo 2) |
|---|---|---|
| Lectura | `RutinasDeReloj.carga_catalogo_de_empleado`, `helpers.py:304-361`, con openpyxl | `ModeloEmpleados.importar_excel`, `modelo_empleados.py:96-160`; CRUD en `vista_empleados.py:160-266` |
| Ubicación | Archivo con el nombre `nombre_catalogo` de la empresa, **en la misma carpeta** del archivo de checadas (`form_revisa_checadas.py:533-547`) | `tiempo_extra/Empresas/<id>/tiempo_extra.db`, tabla `empleados` |
| Columnas usadas | A No., B Nombre, C Departamento; por encabezado «DIA DE DESCANSO», «HORA ENTRADA», «HORA SALIDA» (default E, F, G) (`:323-333`) | A No., B Nombre, C Departamento, D Categoría, E Entrada, F Salida, G ¿Calcular T.E.?, H Día de descanso, I Empresa base (`modelo_empleados.py:1-20,128-139`) |
| Parseo | `parsea_hora_decimal`, `parsea_dia_descanso` (`helpers.py:364-396`) | `_parse_hora`, `_parse_si`, `_parse_dia_descanso` (`modelo_empleados.py:26-65`) |
| Validación | Filas sin nombre se omiten; excepciones se tragan en silencio (`except: continue`, `:357-358`) | Descanso obligatorio; número único; `calcula_te` ligado a `activo` y a jornada (`vista_empleados.py:177-213`) |
| Plantilla | — | `tiempo_extra/Plantillas/Catalogo_Empleados.xlsx` y generador `crear_plantilla_empleados.py` |
| Consumo | Selección del empleado (`FrmBuscaEmpleado`), jornada y descanso del cálculo (`form_revisa_checadas.py:1224-1230`) | Lista de la grilla de T.E., cálculo, reportes (`vista_tiempo_extra.py:243-249`) |

**Brechas frente al cap. 13 (Comprobado):** sin ID interno distinto del número de reloj; sin vigencias; sin baja lógica/reactivación ni historial; sin bitácora de altas/ediciones; borrado físico; importación Excel con *upsert* por número (`importar_excel`, `:96-160`) sin lote, vista previa ni informe de conciliación ni idempotencia por lote; errores de fila se cuentan pero no se detallan (`except Exception: errores += 1`, `:~150-155`). Se omiten con aviso las filas sin día de descanso (`sin_descanso`, `filas_sin_descanso`).

## 6. Reglas implícitas y casos especiales detectados

### 6.1 Reglas implícitas (todas Comprobadas salvo nota)

1. **Día evaluado = fecha de entrada.** Un turno nocturno se asigna íntegramente al día en que entra (`helpers.py:406-420`); `es_finde` y `es_descanso` se evalúan solo por ese día. Una jornada que cruza medianoche hacia domingo se evalúa como día laborable normal.
2. **Domingo y sábado = fin de semana por calendario** (no por horario). El domingo es «especial» solo en cuanto a umbral 8 h; no hay prima dominical ni alerta (cap. 2.1, art. 71).
3. **Faltante** = jornada − horas, solo si vino y no cubrió; **se resta del T.E. semanal** (`neto_semana`). Si no vino, no hay faltante (`calculo_te.py:155-160`).
4. **Día laborable sin checadas = falta** (rojo) salvo descanso (`exportar_reporte.py:82-92`); los **festivos no se detectan** (lo dice el propio comentario, `:88-89`).
5. **Doble checada ≤30 min** del mismo día se descarta (la primera gana) (`helpers.py:520-528`, `reloj_generico.py:96-104`); la regla es por día, no por turno, así que una salida y reentrada en ≤30 min también se pierde.
6. **Empresa base** es solo informativa (`crear_bd.py:26-35`): el reporte depende de `calcula_te`/`activo`. Los empleados importados se cargan todos sin importar su empresa (`modelo_empleados.py:97-110`).
7. **El catálogo manda sobre el reloj** solo en jornada/descanso; el nombre del reloj se compara con el del catálogo y pide confirmación si difiere (`form_revisa_checadas.py:583-600`).
8. **Semana de pago = semana de la empresa:** 7 días iniciando el día de la semana de `fecha_inicio` (`tiempo_extra/Config/empresas.py:46-53`); la «semana sugerida» es la anterior a la actual (`vista_tiempo_extra.py:140-145`).
9. **Sin jornada de catálogo (Flujo 1)** se usa 00:00–08:00 como jornada (`helpers.py:425-426`); en Flujo 2, sin jornada, no se calcula extra (`calculo_te.py:146-147`). Las dos rutas **se comportan distinto** sin jornada.
10. **Horas enteras:** todo el cálculo opera en horas enteras (A02/A04).
11. **Seguimiento de alteraciones al minuto:** `difiere_minuto` compara redondeando a minuto para evitar falsos positivos por segundos del reloj (`modelo_registro_diario.py:86-97`).
12. **Segundos:** `helpers.fecha_hora_a_decimal` conserva segundos (`helpers.py:76`) mientras `tiempo_extra/ClasesComunes/fechas.py:34` los descarta; en el Flujo 1 los segundos se pierden de hecho porque la hora se pasa por texto `%H:%M` (`form_revisa_checadas.py:670-673,1248-1249`). **Hipótesis:** inocuo en uso normal, pero es una divergencia entre dos implementaciones del mismo concepto.
13. **El «Autorizó» del reporte TE es el nombre corto de la empresa** (`exportar_reporte.py:_construir`, variable `aut`); no hay persona autorizadora.
14. **Calendario:** no hay festivos, vacaciones, incapacidades ni permisos (RE02, RE06): **No localizado**.

### 6.2 Casos especiales

- Empleado con jornada nula: se acepta si `calcula_te=0` (`vista_empleados.py:177-213`).
- `activo=0` fuerza `calcula_te=0` (`vista_empleados.py:19`, probado en `tests/tiempo_extra/test_vista_empleados_logica.py`).
- Archivo con periodo distinto a la semana → se rechaza (no se calcula).
- Bloque de empleado ya exportado para la semana → confirma sobrescritura (`form_revisa_checadas.py:839-855`).
- «Reporte sin extras» no se genera (no hay evidencia de semanas sin tiempo extra).
- Si el empleado no existe en el reloj por número, busca por nombre (riesgo de coincidencia parcial: `nombre.upper() in cat_upper`, `helpers.py:456`).

### 6.3 Nota de requerimientos pendientes (Hipótesis)

`MODIFICACION DE LEJOJ CHECADOR PARA BATAB.docx` registra necesidades de un usuario de una empresa: (a) marcar por día con T.E. a qué alimentos tiene derecho el trabajador (desayuno/almuerzo/cena), condicionado a haber generado tiempo extra; (b) personal de reparto que inicia a las 2:00 a. m. y no puede checar hasta llegar a la planta, por lo que se pide poder modificar manualmente la checada. **No se localizó implementación** en el código (búsqueda de `desayuno|almuerzo|cena|alimento` sin resultados). (b) apunta al caso del cap. 17 (jornadas por contingencia) y es relevante para el diseño de incidencias; se desconoce si se aprobó.

## 7. Resumen de estado por hallazgo

| ID | Tema | Estado | Riesgo |
|---|---|---|---|
| A01 | Constantes laborales | No cumple | Alto |
| A02 | Cálculo diario/semanal | No cumple | Alto |
| A03 | Horarios y vigencias | No cumple | Alto |
| A04 | Tolerancias y redondeos | No cumple | Alto |
| A05 | Importación y emparejamiento | No cumple (parcial en formatos de lectura) | Alto |
| A06 | Alertas y validaciones | No cumple | Medio-Alto |
| A07 | Correcciones y autorizaciones | No cumple | Alto |
| A08 | Reportes y exportación | Parcial | Medio |
| A09 | Resultados históricos | No cumple | Alto |
| A10 | Seguridad, rendimiento, recuperación | No cumple | Alto |

Los estados «no cumple» no son defectos de V1 en su contexto original: V1 se diseñó antes de la reforma y de este plan; se miden contra el plan, y **una coincidencia con V1 no prueba cumplimiento legal** (cap. 0, punto 6).

## 8. Activos de V1 con valor para V2 (síntesis; detalle en el doc. 13)

- Lectura/conversión de archivos de reloj y detección de formato (`helpers.py:209-253, 550-1182`): reutilizable con refactor (separar de Qt, eliminar el descarte de checadas, persistir originales).
- `lista_semanas_laboradas` y fechas de semana: reutilizable.
- `calculo_te.py`: pura, **reemplazar** el algoritmo, conservar estructura de resultado y casos de prueba como caracterización.
- Reportes Excel/PDF (`exportar_reporte.py`): adaptar maquetación y paleta; cambiar datos.
- Catálogo/empresas/UI: adaptar a MVC SSD con `ModeloBase` y migraciones.
- Pruebas: 34 casos reutilizables como caracterización.

## 9. Preguntas abiertas para el propietario

| # | Pregunta | Por qué importa |
|---|---|---|
| Q01 | ¿Qué modelo de reloj es, con qué software se exportan los Excel, y ese software **borra o marca como leídos** los registros del dispositivo al exportar? | Cap. 0: define si V2 puede leer el reloj en paralelo a V1. **Respuesta (24/11/2026):** V2 no se conecta a los relojes; seguirá recibiendo los reportes emitidos por el reloj de cada empresa (formato propio por empresa) y convirtiéndolos al formato Genérico como V1. Ver matriz R001–R003 |
| Q02 | ¿Existe una fuente cruda (dump/archivo original del reloj) o solo los reportes en Excel? ¿Se conservan los Excel originales? | Cap. 14: checadas originales inalterables y lotes. **Respuesta (24/11/2026):** el reporte emitido por el reloj es la evidencia primaria que la autoridad puede requerir. V2 debe: (1) conservar el archivo original byte a byte (copia administrada, hash SHA-256, nunca modificado); (2) tratar la conversión al Genérico como dato derivado que preserva exactamente fecha y hora de cada registro (incluidos segundos si la fuente los trae); (3) guardar las checadas en SQLite solo-inserción, vinculadas a archivo y fila de origen; (4) emitir informe de filas leídas/convertidas/rechazadas (V1 oculta rechazos con `except: continue`) |
| Q03 | ¿Los empleados checan entrada/salida de comida? ¿El reloj distingue entrada/salida o solo marca «checada»? | Emparejamiento, descansos computables. **Respuesta (24/11/2026):** hasta ahora solo se checa entrada y salida. V2: el descanso se toma del horario asignado (computable o no computable), marcado como «descanso según horario, sin checada»; el motor y el emparejamiento deben admitir 4 checadas diarias si en el futuro se agregan |
| Q04 | ¿La regla «+0,33/−0,33 h con redondeo a hora entera» es una política formal (reglamento interno) o una convención histórica? ¿Debe replicarse en paralelo para comparar? | A04; define las pruebas comparativas con V1. **Respuesta (24/11/2026):** la empresa emitirá un nuevo reglamento interno; las tolerancias quedan configurables (0–15 min por política versionada con vigencia, caps. 4.3 TO01–TO07). El redondeo ±0,33 h de V1 no se replica como regla de V2; solo se usa como referencia de caracterización al comparar con V1 |
| Q05 | ¿La compensación de faltantes contra tiempo extra semanal (`neto_semana`) es política aprobada de la empresa? | Contradice el plan (§1.1); requiere decisión. **Respuesta (24/11/2026, provisional):** criterio «semanal con acuerdo»: extra = máx(0, confirmado de la semana − tope vigente), asignada a los excesos diarios más recientes para evaluar art. 66/68; parámetro versionado sujeto a reglamento STPS y dictamen. Ver plan §5.2 y documento 14 §5 |
| Q06 | ¿El sábado y el domingo siguen con jornada estándar de 8 h para el pago de extras, o cambiará con la reforma (sábado 6 h en 2027, etc.)? ¿Cómo se asignan los horarios de 2027? | A01/A03: K06. **Respuesta (24/11/2026):** no hay jornada fija de fin de semana; los horarios se asignan por trabajador/grupo y por año (esquema previsto 2027: 5 × 8 + 6), cálculo en minutos. Plan §4.2 |
| Q07 | ¿Se necesita que V2 reproduzca resultados históricos de V1 o basta con que calcule hacia adelante? ¿Desde qué fecha? | A09. **Respuesta (24/11/2026):** solo hacia adelante desde 01/01/2027; el histórico de V1 queda para consulta y V1 sigue como respaldo durante la operación paralela |
| Q08 | ¿Las 3 empresas comparten empleados/códigos de reloj, o los códigos pueden repetirse entre empresas/relojes? ¿Qué es «Empresa base»? | Cap. 13.1 (ID del reloj no único). **Respuesta (24 y 26/11/2026):** los usuarios administran los códigos; en un reloj compartido el código es único. V2 identifica por (reloj, código, vigencia) → empleado. «Empresa base» (`empresa_base`, informativo en V1) es el patrón IMSS del trabajador; AEI fue la primera empresa del sistema. Un trabajador puede checar en una empresa y tener otra como patrón; V2 los guarda por separado con vigencia (plan §13.1) |
| Q09 | ¿Existe un calendario de festivos y descansos obligatorios de uso actual? ¿Quién lo mantiene? | RE02, HO05. **Respuesta (26/11/2026):** no existe; en V2 será obligatorio un calendario por año. Sin calendario confirmado, las semanas del año quedan provisionales (sin cierre ni exportación); precarga sugerida del art. 74 que RH confirma (plan RE02) |
| Q10 | ¿Quién es el «Jefe de personal» y quién autoriza hoy los tiempos extra (los campos `reporto`/`autorizo` son texto)? ¿Cuántos usuarios y roles tendrá V2? | Cap. 16, 22, 28. **Respuesta parcial (26/11/2026):** cada empresa designa a su autorizador (AEI: dirección; CATAB: jefe de producción); autoriza la empresa donde se trabajó la extra, aunque el patrón sea otra (plan RE03). Usuarios por empresa: auxiliar administrativo (elabora y captura aclaraciones), autorizador (aprueba; no lo que él capturó) y RH (revisa y cierra); Dirección da Vo.Bo. Reporte con 4 firmas (plan §6 y §7.4) |
| Q11 | ¿Se aprobaron los requerimientos de la nota BATAB (alimentos por T.E.; modificar checadas de repartidores que inician a las 2:00 a. m.)? | Diseño de incidencias/contingencia (cap. 17). **Respuesta (26/11/2026):** ambos aprobados y vigentes para V2. Reparto 2:00 a. m. → aclaración aprobada (plan cap. 17.1); alimentos por T.E. → reglas configurables por empresa y vigencia, solo donde apliquen (plan cap. 17.1) |
| Q12 | ¿`datos/catalogo_te.db` (raíz de V1) está en uso o es un residuo? ¿Hay otras BD de producción además de `tiempo_extra/Empresas/*/tiempo_extra.db`? | Alcance de la migración. **Respuesta (26/11/2026):** no aplica. V2 empieza de cero: las empresas arrancan en blanco y no se migran las BD de V1; solo se reutiliza el código de V1 que funcione (matriz 13). El histórico queda en V1 (Q07). Única excepción: el catálogo de empleados se importa una vez desde Excel (plan §13.2) |
| Q13 | ¿Cuántos empleados por empresa y qué antigüedad de datos se espera consultar? ¿Una o varias PC? | Cap. 22 (SQLite, concurrencia, rendimiento) |
| Q14 | ¿Hay trabajadores con turnos nocturnos/mixtos, menores de edad o con jornadas parciales? | Cap. 2.1, 5.2 |
| Q15 | ¿Cuál es la política de respaldo actual de las BD y de los Excel generados? | A10 |

## 10. Verificación de no modificación de V1

Se ejecutó `git -C "D:/Proyectos/app_revisar_checadas" status --short` al finalizar; el resultado se reporta en el informe de entrega y debe coincidir con la línea base (`M config.json` y `?? APP_REVISAR_CHECADAS_TE_AEI_260720.xlsx`).
