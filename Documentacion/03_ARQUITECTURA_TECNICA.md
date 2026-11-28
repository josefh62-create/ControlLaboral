# 03 — Arquitectura técnica de ControlLaboral V2.0

**Estado:** Aprobada por el propietario el 26/11/2026 (las 9 decisiones del §14 con la recomendación) · **Fecha:** 26/11/2026 · **Tarea:** T4 (`odd/tasks/auditoria-v1.md`)
**Alcance:** estructura, capas, módulos, motor de jornada, seguridad, pruebas y plan de entregas. **No** incluye DDL (pertenece a `04_BASE_DE_DATOS`), reglas de negocio detalladas (`05`) ni código.

**Fuentes leídas (todas en esta sesión):**
`D:\Proyectos\CLAUDE.md` (reglas del SSD) · `VS_SIVEMA_MVC_PY\ARQUITECTURA_APPS_PYTHON.md` v1.1 (en adelante **«doc. maestro»**, §n) · `AGENTS.md` · `ControlLaboral_Plan_Maestro_v3.0.md` (en adelante **«plan»**, caps. 0–30 completos) · `Documentacion/01` (auditoría V1, §9 Q01–Q15) · `13` (matriz R001–R047, D01–D22) · `14` (conclusiones, §5) · `00` (fuente legal, solo índice y «Consecuencias para el diseño»). V1 se consultó solo para confirmar símbolos (`grep` de lectura); no se modificó, ejecutó ni compiló nada de V1. No se leyó código de `Mi_Tiendita` ni de `ControlDeAlmacen` más allá de listar carpetas y `Mi_Tiendita\Modelos\modelo_base.py` (ver §15, riesgo R9).

**Convención de evidencia:** *Hecho* = verificado en archivo citado. *Propuesta* = diseño nuevo de este documento. *Requiere aprobación del propietario* = se aparta del doc. maestro o de AGENTS.md (regla 3 del SSD).

---

## 1. Resumen ejecutivo

1. V2 es una aplicación de escritorio PySide6 sobre Python 3.14.7 (`PyPortable314`), con **MVC estricto del SSD como carcasa externa** y una sola base SQLite local (una PC, 3 empresas, 40–200 empleados cada una).
2. La tensión «MVC con SQL en `Modelo<X>`» (doc. maestro §3.2, §11.1) frente a «el motor no conoce SQL ni SQLite» (plan §22.1; AGENTS.md) se resuelve con un paquete **`Dominio/` puro** (Python estándar, sin PySide6 ni `sqlite3`) que contiene el motor legal y de jornada; los `Modelo<X>` y `Servicios/` lo alimentan con datos explícitos y los `Controlador<X>` lo invocan a través de ellos.
3. El motor es una **tubería de funciones puras** (emparejar → segmentar → clasificar → asignar extra semanal → tramos doble/triple → alertas → invariantes). Recibe horario, norma, política y checadas como datos; devuelve un resultado versionado. Se prueba sin Qt ni SQLite con la matriz P01–P50.
4. Los parámetros legales y políticas son **datos versionados por fecha efectiva**; cada resultado guarda el criterio, la versión de norma/política, la versión del motor y una huella SHA-256 de sus entradas (reproducible, plan A09/D12).
5. Las checadas, los archivos originales, las versiones de acta y la bitácora son **solo-inserción** (triggers + permisos + auditoría); toda corrección es una aclaración con separación de funciones auxiliar → autorizador → RH.
6. Respaldo con la Online Backup API de SQLite, destino elegido por el usuario, manifiesto con hashes y verificación; migraciones idempotentes al arrancar con respaldo previo; empaquetado con `_instaladores\empaquetar.ps1` (el script ya soporta `runtime` por proyecto, `empaquetar.ps1:79-81`).
7. **Riesgo principal:** al 26/11/2026 faltan 36 días naturales para el 01/01/2027. El plan de entregas (§13) separa un núcleo mínimo (E0–E4 + usuarios básicos + respaldo) del resto, que madura durante la operación paralela con V1 como respaldo (Q07).
8. Se proponen **9 decisiones** para el propietario (§14); las desviaciones del doc. maestro son pocas y están marcadas (§4.2).

---

## 2. Principios y restricciones

| # | Principio / restricción | Fuente |
|---|---|---|
| P1 | MVC estricto; sin SQL en vistas ni controladores; vistas sin reglas de negocio | CLAUDE.md SSD reg. 1; doc. maestro §2.1, §2.9, §3.3, §22 |
| P2 | UI solo en `.ui` de Qt Designer; `frm_*.py` generado, nunca editado; recompilar con `uic.exe`/`rcc.exe` reales y `-g python` | CLAUDE.md SSD reg. 4 y «Compiladores»; doc. maestro §6.1, §10 |
| P3 | Claro y oscuro; secciones en `QFrame`/`QGroupBox` con layout propio | CLAUDE.md SSD reg. 5–6; doc. maestro §6.2, §7 |
| P4 | Runtime `PyPortable314` referenciado en relativo, sin `venv`; no instalar nada en `PyPortable311` | CLAUDE.md SSD «Migración en curso»; AGENTS.md «Estándar técnico» |
| P5 | Motor de jornada en Python puro, con datos de entrada explícitos, determinista y sin conocer SQL/SQLite/PySide6 | AGENTS.md; plan cap. 19.2, §22.1; Q05 |
| P6 | No fijar en código valores laborales cambiantes; sí el algoritmo y las restricciones de integridad | plan §1.1, NL01–NL07, HO06 |
| P7 | Aplicar la versión de reglas de la **fecha trabajada**, no la de consulta; mismos datos y versiones → mismo resultado | plan §1.1, §5.4, A09, P36, P43 |
| P8 | Checadas originales inalterables (UI, servicios, BD); archivo original byte a byte con SHA-256; conversión al formato Genérico como dato derivado | plan cap. 14, A10, S05; Q02 |
| P9 | Corrección = aclaración (cap. 14); separación auxiliar → autorizador → RH; el autorizador no aprueba lo que capturó; Dirección da Vo.Bo. sin usuario propio | plan §6, RE03, §7.4; Q10 |
| P10 | Un solo registro de empleado para todas las empresas; código por reloj con vigencia; patrón IMSS ≠ centro de trabajo; emparejamiento sobre la secuencia unificada de todos los relojes | plan §5.1-4, §13.1; Q08 |
| P11 | Tiempo siempre en enteros (minutos para parámetros y horarios; ver decisión 2); nunca horas decimales | plan §4.2, RE07, P39 |
| P12 | Alertas y pendientes nunca borran ni ocultan tiempo; faltantes separados; sin compensación automática salvo el criterio «semanal con acuerdo» | plan §1.1, §5.2–5.4; Q05 |
| P13 | Contemplar **todos** los regímenes de la LFT (diurna, nocturna, mixta, parcial, menores, descansos y festivos), habilitables por configuración | plan NL07; Q14 |
| P14 | SQLite local solo en disco fijo (no red, no carpeta sincronizada); FK ON, WAL evaluado, `synchronous=FULL`, `busy_timeout`; respaldo por Online Backup API | plan §22.1–22.3; doc. maestro §11.2; Q13, Q15 |
| P15 | Migraciones idempotentes al arrancar; una actualización nunca sobrescribe la BD; esquema versionado | CLAUDE.md SSD «Instalación»; doc. maestro §12 |
| P16 | Sin conexión directa a relojes: la fuente es el reporte que emite el reloj de cada empresa | plan cap. 0 (último párrafo); Q01 |
| P17 | Calendario de descansos obligatorio por año; sin él, las semanas son provisionales | plan RE02; Q09 |
| P18 | Reutilizar de V1 lo compatible y justificar lo demás (matriz 13); V1 es de solo lectura | plan cap. 0, 19.3; AGENTS.md |
| P19 | Supabase/portal/móvil son fases posteriores y **no autorizadas**; Desktop no depende de ellas | plan §23.2, §30.3; AGENTS.md |
| P21 | Foto del empleado opcional (archivo o cámara web), solo para identificación visual; sin reconocimiento facial ni plantillas biométricas; dato personal con aviso y consentimiento; redimensionada, con hash y versión; en el respaldo; no se publica; sin cámara nunca bloquea el alta | plan §13.1 «Foto del empleado»; cap. 28 |
| P20 | V2 calcula solo desde 01/01/2027; sin migrar BD de V1; única importación: catálogo de empleados desde Excel, con unión de personas confirmada por RH | Q07, Q12; plan §13.2 |

---

## 3. Resolución de la tensión MVC del SSD ↔ motor puro del plan

**Hechos.**
- El doc. maestro define `Modelo<X>(ModeloBase)` como sede de «reglas de negocio» y de datos (§3.2), pero también admite **Servicios** (§3.5) y **Repositorios** (§3.6) «cuando la complejidad lo justifique» y que MVC «nunca se omite» (§4). La carpeta `Repositorios/` ya existe en `ControlDeAlmacen` (listado verificado).
- El plan exige separar «presentación, casos de uso, dominio y persistencia mediante interfaces de repositorios y una unidad transaccional» y que el motor «no conocerá SQL ni SQLite» (§22.1); la prueba S15 pide resultados idénticos con un repositorio de prueba. AGENTS.md pide «capa de servicio/dominio en Python puro».
- La matriz 13 ya asignó `Dominio/` como destino tentativo del motor (encabezado y filas R005–R016, R043).

**Propuesta (una sola estructura).**

| Capa | Dónde | Qué contiene | Sabe de… |
|---|---|---|---|
| Presentación | `Vistas/` (`frm_*.ui`, `vista_*.py`) | Widgets, estado visual, señales | Nada de datos |
| Coordinación | `Controladores/` | Secuencia de operaciones, permisos de pantalla, confirmaciones | Modelos y Servicios |
| Modelo (carcasa MVC) | `Modelos/` — `Modelo<X>(ModeloBase)` | Validación de captura, CRUD de catálogos, formato `{exito, resultado, mensaje, campo}`; para módulos del motor, **fachada delgada** | Repositorios, `Dominio` (tipos) |
| Servicios | `Servicios/` | Casos de uso multi-entidad: importar, calcular semana, emitir acta, respaldar, exportar | Repositorios, `Dominio` |
| Repositorios | `Repositorios/` | SQL parametrizado y mapeo fila ↔ entidad de `Dominio`; implementan los puertos | `Database/`, tipos de `Dominio` |
| **Dominio (puro)** | `Dominio/` | Reglas legales, calendario, emparejamiento, segmentación, clasificación, alertas, invariantes, **puertos** (`Protocol`) | Solo biblioteca estándar (`datetime`, `zoneinfo`, `dataclasses`, `enum`, `typing`, `hashlib`) |
| Infraestructura | `Database/` | Conexión con PRAGMAs, unidad de trabajo, migraciones | `sqlite3` |

**Cómo se cumplen ambos mandatos.**
1. *SSD:* toda pantalla conserva su trío `frm_/vista_/modelo_/controlador_`; el modelo del módulo hereda `ModeloBase`; ninguna vista ni controlador toca SQL (doc. maestro §3.4, §11.1). Los catálogos simples (empresas, centros, relojes, festivos) usan `ModeloBase` con CRUD directo, como en `Mi_Tiendita`.
2. *Plan:* el cálculo vive en `Dominio/`; `ServicioCalculoSemana` (o el `ModeloRevision` que lo envuelve) carga los datos por repositorios, construye `EntradaSemana`, llama a `Dominio.motor_jornada.calcular_semana(...)` y persiste el resultado en una unidad de trabajo. El dominio no importa nada de `Modelos/`, `Servicios/`, `Repositorios/`, `Database/`, `PySide6` ni `sqlite3`.
3. *Verificación estructural:* una prueba (`tests/dominio/test_pureza.py`) importa `Dominio` con `PySide6` y `sqlite3` bloqueados en `sys.modules` y recorre el AST para prohibir `datetime.now()`, `date.today()`, `open()` y `random` sin semilla (plan cap. 9: las pruebas no dependen del reloj ni de la fecha del equipo).

**Desviaciones respecto del doc. maestro (todas requieren aprobación del propietario).** Ver §4.2, DV1–DV2.

---

## 4. Estructura de carpetas propuesta

### 4.1 Árbol

```text
ControlLaboral/                         (raíz del repositorio; V2, independiente de V1)
├── main.py                             compone la aplicación (inyección de repositorios, tema, sesión)
├── run.bat · compilar_ui.bat           PyPortable314 en relativo; uic.exe/rcc.exe reales, -g python
├── instalador.json · requirements.txt · pytest.ini · .gitignore · README.md · AGENTS.md
├── .vscode/settings.json               intérprete y PATH relativos a ..\PyPortable314; rutas PYQT relativas al archivo
├── controllaboral_rc.py                GENERADO desde Recursos/Imagenes/controllaboral.qrc
├── Config/
│   └── config.py                       rutas, nombre de app, versión de esquema soportada. SIN valores laborales
├── Controladores/
│   ├── controlador_base.py             barra global: nuevo/guardar/buscar/cancelar/refrescar_datos (doc. maestro §3.4)
│   ├── controlador_principal.py        ventana principal, sidebar, `modulos_disponibles`, permisos de navegación
│   └── controlador_<modulo>.py         uno por módulo (ver §6)
├── Modelos/
│   ├── modelo_base.py                  ModeloBase (copiado del patrón de Mi_Tiendita; ver DV5)
│   └── modelo_<modulo>.py              Modelo<Modulo>(ModeloBase)
├── Vistas/
│   ├── frm_<modulo>.ui                 diseño Qt Designer (QFrame/QGroupBox, prefijos doc. maestro §5.2)
│   ├── frm_<modulo>.py                 GENERADO, no editar
│   └── vista_<modulo>.py               Vista<Modulo>: presentación, tema, propiedades dinámicas
├── Dominio/                            PURO: sin PySide6, sin sqlite3, sin E/S, sin fecha del sistema
│   ├── tiempo.py                       segundos/minutos, intervalos, HH:mm, conversiones (de R042)
│   ├── modelos.py                      dataclasses inmutables: Checada, Horario, Norma, Politica, Segmento, Resultado…
│   ├── puertos.py                      Protocol de repositorios y de ProveedorFecha (para Servicios y dobles de prueba)
│   ├── normatividad.py                 resolución de versión vigente por fecha, topes por régimen (NL01–NL07)
│   ├── regimenes.py                    diurna/nocturna/mixta, parcial, menores: restricciones por régimen
│   ├── calendario.py                   semana laboral, día festivo/descanso/domingo (de R009, R016)
│   ├── checadas.py                     orden, marcado de duplicados/futuras/desfases (sin descartar)
│   ├── emparejamiento.py               secuencia unificada multi-reloj, traslado entre empresas, ambigüedades
│   ├── horarios.py                     minutos ordinarios diarios/semanales, compatibilidad (HO01–HO07)
│   ├── segmentacion.py                 fronteras: horario, descansos, medianoche, vigencia, topes
│   ├── criterios_extra.py              criterio «semanal con acuerdo» (estrategia registrable por código)
│   ├── tramos_extra.py                 doble/triple, límites art. 66/68, exceso legal, pendiente
│   ├── tolerancias.py                  diferencia real vs administrativa (TO01–TO07)
│   ├── alertas.py                      AL01–AL14 como funciones puras + clave de deduplicación
│   ├── alimentos.py                    derecho a alimentos por T.E. según reglas configuradas
│   ├── invariantes.py                  invariantes de plan §5.4
│   └── motor_jornada.py                `calcular_semana(EntradaSemana) -> ResultadoSemana` (composición)
├── Servicios/
│   ├── servicio_importacion.py         archivo original + hash + lote + parser + checadas (insert-only)
│   ├── formatos/                       un parser por formato de reporte → filas canónicas (de R002–R005)
│   ├── servicio_calculo_semana.py      carga → motor → persistencia versionada (unidad de trabajo)
│   ├── servicio_alertas.py · servicio_calendario.py (precarga art. 74)
│   ├── servicio_migracion_excel.py     importación única del catálogo (vista previa, lote, conciliación)
│   ├── servicio_actas.py · servicio_reportes.py (xlsx/pdf) · servicio_exportacion_autoridad.py (diferido)
│   ├── servicio_autenticacion.py · servicio_bitacora.py
│   ├── servicio_respaldo.py            Online Backup API, manifiesto, restauración validada
│   └── publicacion/                    DIFERIDO (Supabase); no se crea hasta autorización
├── Repositorios/
│   └── repositorio_<entidad>.py        SQL parametrizado; implementan los puertos de Dominio
├── Validadores/                        validador_hhmm, validador_curp_rfc, validador_archivo, validador_codigo_reloj…
├── ClasesComunes/                      formato.py (fmt_*), mensaje.py, permisos.py, temas.py, contexto_sesion.py
├── Database/
│   ├── conexion_sqlite.py              abre conexión con PRAGMAs verificados (FK, WAL, synchronous, busy_timeout)
│   ├── unidad_trabajo.py               transacción explícita (BEGIN IMMEDIATE / commit / rollback)
│   ├── crear_bd.py                     `_aplicar_migraciones` (patrón Mi_Tiendita, doc. maestro §12.1)
│   └── migraciones/                    NNNN_descripcion.sql (doc. maestro §5.1)
├── Recursos/ Imagenes/(controllaboral.qrc) · Estilos/(base.qss, light.qss, dark.qss) · Fuentes/
├── Plantillas/                         plantillas de reporte y de importación de empleados
├── data/                               solo desarrollo, fuera de Git: BD y archivos (ver decisión 4 para producción)
├── logs/ · backups/                    fuera de Git
├── tests/                              ver §12
├── Documentacion/                      00…14 (ya existente; se conserva el nombre en lugar de `docs/`)
└── odd/                                tareas ODD
```

Nomenclatura: módulos en plural según los ejemplos del doc. maestro (`modelo_empleados.py`, `ModeloEmpleados`, §5.1); la matriz 13 usó singular en algunos destinos y se ajustará. Prefijos de widgets: ver decisión 9.

### 4.2 Desviaciones y ajustes frente al doc. maestro

| ID | Desviación | Dónde choca | Justificación | Estado |
|---|---|---|---|---|
| DV1 | Carpeta nueva `Dominio/` (no figura en el árbol de §4, que permite agregar capas «cuando la complejidad lo justifique») | doc. maestro §4 | Hace estructural la pureza exigida por plan §22.1 y AGENTS.md; la matriz 13 ya la usaba | **Requiere aprobación del propietario** (decisión 1) |
| DV2 | Para módulos del motor, `Modelo<X>` es **fachada delgada** (valida captura y delega); las reglas legales no están en el Modelo | doc. maestro §3.2 («reglas de negocio» en el modelo) | Las reglas legales son puras y deben probarse sin `ModeloBase` (que arrastra SQLite) | **Requiere aprobación del propietario** (decisión 1) |
| DV3 | `ModeloChecada`, `ModeloBitacora`, `ModeloArchivoOriginal`, `ModeloActaVersion` **sobrescriben** `actualizar`/`eliminar` para rechazarlos | doc. maestro §3.2 (`ModeloBase` expone CRUD completo) | Tablas solo-inserción (plan §22.2, A10, S05) | Ajuste interno; informar al aprobar DV1 |
| DV4 | `Database/unidad_trabajo.py` y conexión con PRAGMAs (V1/`Mi_Tiendita` abren una conexión por operación sin transacción multi-sentencia; R030) | doc. maestro §11.1–11.2 pide transacciones y `foreign_keys=ON` por conexión | Atomicidad de importación, cálculo, emisión y cierre (plan cap. 19.2) | Cumple el doc. maestro; solo amplía el patrón |
| DV5 | Se **copia** `ModeloBase`/`OperacionesSqlite` al proyecto en lugar de compartirlos entre proyectos | — (el doc. maestro no define paquete común) | Proyectos independientes; sin dependencia cruzada | Informativo |
| DV6 | Runtime 3.14.7 / PySide6 6.11.2 en lugar de 3.11.9 / 6.11.1 | doc. maestro §2.5, §8, §9.1, §16.3, §23 aún dicen `PyPortable311` | Migración en curso declarada en CLAUDE.md SSD; el doc. maestro está desactualizado | Sin aprobación necesaria; **actualizar el doc. maestro** |
| DV7 | Una sola BD con `empresa_id` en lugar de una BD por empresa | doc. maestro §12.3 (solo aplica «si cada empresa tiene BD propia») | Un empleado único y checadas unificadas entre relojes (plan §13.1, §5.1-4) lo exigen; V1 sí usaba una BD por empresa (`01 §1.5`) | Coherente con el doc. maestro; decisión ya tomada por el propietario |
| DV8 | Carpeta `Documentacion/` en vez de `docs/` | doc. maestro §4 | Ya existe y está referenciada en AGENTS.md | Informativo |
| DV9 | `tests/dominio/`, `tests/comparativas/`, `tests/caracterizacion/` además de `unit/integration/ui/fixtures` | doc. maestro §16.1 | Matriz P01–P50 y comparación con V1 (plan caps. 20–21) | Informativo |

---

## 5. Capas y dependencias

```mermaid
flowchart TD
  V[Vistas<br/>frm_*.ui + vista_*.py] -->|señales y datos de captura| C[Controladores]
  C --> M[Modelos<br/>Modelo&lt;X&gt;(ModeloBase)]
  C --> S[Servicios]
  M --> R[Repositorios<br/>SQL + mapeo]
  M -. tipos .-> D
  S --> R
  S --> D[Dominio PURO<br/>motor + puertos]
  R -. entidades .-> D
  R --> DB[Database<br/>conexión, UoW, migraciones]
  DB --> SQL[(SQLite local)]
  S --> FS[(data/archivos<br/>originales y PDF)]
  main[main.py<br/>composición] -.-> C & M & S & R
```

**Reglas de importación (se verifican con una prueba de arquitectura, `tests/unit/test_arquitectura.py`).**

| Capa | Puede importar | NO puede importar |
|---|---|---|
| `Vistas` | `PySide6`, `ClasesComunes`, tipos/enums de `Dominio` (solo presentación) | `Modelos`, `Servicios`, `Repositorios`, `Database`, `sqlite3`, funciones del motor |
| `Controladores` | `Vistas`, `Modelos`, `Servicios`, `ClasesComunes`, `PySide6` (señales) | `Repositorios`, `Database`, `sqlite3` |
| `Modelos` | `Repositorios`, `Database` (vía `ModeloBase`), `Dominio`, `Validadores` | `PySide6`, `Vistas`, `Controladores` (doc. maestro §4.2) |
| `Servicios` | `Repositorios`, `Dominio`, `Validadores`, biblioteca estándar, `openpyxl`/`reportlab` | `PySide6` (un servicio no manipula widgets, §3.5), `Vistas`, `Controladores` |
| `Repositorios` | `Database`, tipos de `Dominio` | `PySide6`, `Modelos`, `Servicios`, mensajes de usuario (§3.6) |
| `Dominio` | solo biblioteca estándar | todo lo demás, incluida cualquier E/S y `datetime.now()` |
| `main.py` | todas (compone) | — (ninguna capa importa `main.py`, §4.2) |

**Dónde vive el motor y cómo se prueba.** `Dominio/motor_jornada.py` expone una función pura. Las pruebas construyen `EntradaSemana` con constructores sintéticos (`tests/fixtures/semanas.py`) y comparan con tablas de resultados esperados escritas **a mano e independientes de V1** (plan cap. 0, punto 6). Los servicios reciben los repositorios y un `ProveedorFecha` (puerto) por inyección; las pruebas de servicio usan dobles en memoria que implementan los mismos `Protocol` (S15: mismo resultado con repositorio de prueba y con SQLite). El término «reloj» se reserva al checador físico; la fuente de tiempo se llama `ProveedorFecha` para evitar confusión.

**Identidad de la sesión.** Un objeto `ContextoSesion` (usuario, empresa activa, roles vigentes) se pasa explícitamente a controladores y servicios; no hay variables globales (doc. maestro §22).

---

## 6. Módulos funcionales

Cada fila crea (cuando aplica) `Vistas/frm_<m>.ui`, `frm_<m>.py` (generado), `Vistas/vista_<m>.py`, `Modelos/modelo_<m>.py`, `Controladores/controlador_<m>.py`. «Motor» indica que además intervienen `Dominio/` y `Servicios/`. Registro en la ventana principal mediante `modulos_disponibles` + sidebar (paso mecánico, CLAUDE.md SSD «Flujo para CRUDs»).

| `<modulo>` | Archivos MVC | Responsabilidad | Plan | Matriz |
|---|---|---|---|---|
| `principal` | `frm_principal`, `vista_principal`, `controlador_principal` | Ventana, sidebar por permisos, barra global, tema, estado de respaldo/calendario faltante | §7.1, RE02 | R033, R036, R040 |
| `empresas` | `modelo_empresas` (+ centros y relojes en el mismo módulo: `frm_empresas`, `frm_editar_empresa`) | Empresas (patrón y/o centro), centros de trabajo, relojes (zona IANA, empresa dueña), `dia_inicio_semana` explícito, ID estable, baja lógica | §13.1, RE01 | R009, R028, R029, R035 |
| `empleados` | `modelo_empleados`, `frm_empleados`, `frm_importar_catalogo`, **`frm_foto_empleado`** (diálogo propio: elegir archivo o tomar con la cámara web, vista previa, recorte) | Registro único; códigos por reloj con vigencia (`modelo_empleado_codigos`); patrón y centro con vigencia; baja lógica y reactivación; fecha de nacimiento (alerta de menor); búsqueda; importación única desde Excel con propuesta de unión de personas; **foto opcional** (`ServicioFotoEmpleado`: `QtMultimedia`/`QtMultimediaWidgets` solo en la vista; el servicio recibe bytes, redimensiona, comprime, calcula hash y versiona; sin cámara o sin permiso informa y ofrece cargar archivo, nunca bloquea el alta) | cap. 13; NL07 | R017–R020, R034, R038, R039; D05, D06 |
| `horarios` | `modelo_horarios`, `frm_horarios`, `frm_asignaciones` | Horario por día en minutos (trabajo/descanso computable/no computable), tipo de jornada, asignación por trabajador/grupo con vigencia y referencia del acuerdo art. 58; validación HO03; reporte de incompatibilidad con años futuros (HO07/AL09) | HO01–HO07, §4.2 | R015; D16, D21 |
| `calendario` | `modelo_calendario`, `frm_calendario` | Calendario anual obligatorio: precarga art. 74, días de empresa, confirmación por RH; estado borrador/confirmado; descansos específicos | RE02, HO05 | R016; D15 |
| `normatividad` | `modelo_normatividad`, `frm_normatividad` | Parámetros normativos versionados (topes 2026–2030, art. 66/68, 12 h, franja nocturna, criterio de extra, traslado máx. 60 min…); alta solo por perfil autorizado, con fundamento; sin solapes ni huecos | cap. 2, NL01–NL07, §5.2 | R013; D01 |
| `politicas` | `modelo_politicas`, `frm_politicas` | Tolerancias 0–15 min, ventana de duplicados, umbrales de alerta, semana de acumulación, reglas de comida y de **alimentos por T.E.** por empresa y vigencia | cap. 4.3–4.5, §17.1 | R014, R027; D03 |
| `importacion` | `modelo_importacion`, `frm_importacion` | Cargar reporte del reloj: copia administrada + SHA-256, detección de formato, conversión a Genérico, informe leídas/convertidas/rechazadas, lote idempotente, validación de periodo | §5.1-1–2, cap. 14 | R001–R006; D04 |
| `checadas` | `modelo_checadas`, `frm_checadas` | Visor de checadas originales (solo lectura), marcas de duplicado/huérfana/impar, asociación a empleado por (reloj, código, fecha) | §5.1, cap. 14 | R007, R008; D04 |
| `revision` | `modelo_revision`, `frm_revision_diaria`, `frm_revision_semanal` | Motor de jornada: recalcular, ver segmentos con instante exacto, colores §7.3, resumen de límites, versión y criterio, estado provisional/cerrado | §5, §7.2–7.3 | R011, R012, R033, R037; D02, D12 |
| `incidencias` | `modelo_incidencias`, `frm_incidencias`, `frm_contingencia` | Aclaraciones (cap. 14) y contingencias (cap. 17) como eventos auditables; evidencia con hash; reparto de madrugada | cap. 14, 17 | R021; D07, D08 |
| `autorizaciones` | `modelo_autorizaciones`, `frm_autorizaciones` | Aprobación de aclaraciones y de T.E. por empresa donde se trabajó; Vo.Bo. de Dirección; RH valida/cierra; 4 firmas del reporte; separación de funciones | RE03, §6, §7.4 | R021; D13 |
| `actas` | `modelo_actas`, `frm_actas` | Un folio lógico por empleado-patrón-semana; versiones, PDF emitido congelado, firmas, ejemplar firmado digitalizado, estados | caps. 16, 18 | D09 |
| `consulta_historica` | `modelo_consulta_historica`, `frm_consulta_historica` | Consulta y reportes de incidencias/actas con filtros combinables; fecha laboral vs fecha de operación; fotografía al cierre | cap. 18 | D10 |
| `reportes` | `modelo_reportes`, `frm_reportes` | Reporte semanal de T.E. (xlsx/pdf), concentrado de incidencias, revisión diaria/semanal, colores con leyenda; reimpresión exacta | §7.4, §18.3 | R023–R026; D10 |
| `alertas` | `modelo_alertas`, `frm_alertas` | Bandeja AL01–AL14 con deduplicación por trabajador+periodo+regla+versión, reconocimiento sin borrado | §4.4 | D03, D21 |
| `usuarios` | `modelo_usuarios`, `frm_usuarios`, `frm_inicio_sesion`, `frm_bitacora` | Cuentas, roles por empresa y vigencia, permisos, inicio de sesión, consulta de bitácora | §6, §22.1, cap. 28 | R022; D13 |
| `respaldo` | `modelo_respaldo`, `frm_respaldo` | Herramientas → Respaldar/Restaurar, destino elegido, respaldo automático, alerta de respaldo antiguo | §22.3, Q15 | D14 |
| `configuracion` | `modelo_configuracion`, `frm_configuracion` | Tema claro/oscuro/sistema, ubicación de datos, preferencias locales (fuera de Git) | doc. maestro §7 | R027, R032; D18 |
| `exportacion_autoridad` | *(diferido)* | Registro electrónico entregable; esperar lineamientos STPS | cap. 15 | D11 |

Servicios transversales sin pantalla propia: `servicio_calculo_semana`, `servicio_calendario`, `servicio_bitacora`, `servicio_autenticacion`. Módulos diferidos y **no autorizados**: `publicacion` (Supabase), portal, móvil (plan caps. 23–27; D19, D20).

---

## 7. Modelo de datos de alto nivel

*Una sola BD SQLite.* Convención propuesta: clave `id` entera + columna `uuid` (texto) en entidades publicables (decisión 5); fechas ISO; duraciones en enteros; textos para códigos con ceros (doc. maestro §11.1, §14). **«IO» = solo-inserción** (triggers `BEFORE UPDATE/DELETE → RAISE(ABORT)` + sin ruta de modificación en `Modelo<X>`; plan §22.2). Los triggers no protegen frente a quien controla el archivo: se complementan con permisos del SO, bitácora y respaldos (plan §22.2).

| Grupo | Entidades (alto nivel) | Relaciones clave | Reglas de inmutabilidad / integridad |
|---|---|---|---|
| Organización | `empresa`; `centro_trabajo`→empresa; `reloj`→centro (zona IANA); `departamento`, `puesto` | Una empresa puede ser patrón y centro | Baja lógica; ID estable (no posición, R029) |
| Personas | `empleado` (único); `empleado_patron`, `empleado_centro` (vigencias); `empleado_codigo_reloj` (reloj, código **texto**, vigencia); `empleado_periodo_laboral` (ingreso/baja/reactivación); `empleado_foto` (empleado, versión, `documento_id`, hash, fecha, usuario, `vigente`, consentimiento registrado) | Sin solapes de (reloj, código) ni de patrón/centro en una fecha (trigger) | Nunca `DELETE` con dependencias; historial conservado; **IO**: `empleado_foto` (el reemplazo agrega versión y conserva la anterior); sin uuid de publicación ni outbox (no se publica) |
| Normativa | `parametro_normativo_version` (clave, valor, vigencia, fundamento, autorizador, estado); `regimen_laboral` | Vigencia `[desde, hasta)` sin solape ni hueco por clave | **IO** una vez activada; cambio = nueva versión |
| Políticas | `politica_version` (tolerancias 0–15 `CHECK`, ventana duplicados, umbrales alerta, semana, traslado máx., comida); `regla_alimento_version` | Ámbito empresa/centro/horario; prioridad explícita | Versionada; `CHECK` de rangos (S03) |
| Horarios | `horario`; `horario_dia`; `horario_intervalo` (tipo: trabajo / descanso computable / no computable); `asignacion_horario` (empleado o grupo, vigencia, acuerdo) | Asignaciones sin traslape ambiguo (HO04) | Cambiar vigencia no reescribe historia; sin horario → cálculo pendiente (HO06) |
| Calendario | `calendario_anual` (año, estado, confirmó, fecha); `dia_inhabil` (fecha, legal/empresa, fundamento); `descanso_excepcion` | Un calendario por año y empresa | Semanas sin calendario confirmado = provisionales |
| Evidencia | `archivo_original` (SHA-256, ruta relativa, tamaño, formato, empresa/reloj, usuario); `lote_importacion` (archivo, conteos); `fila_rechazada`; `checada` (reloj, código, `ocurrido_local`, zona, `ocurrido_utc`, archivo, fila, lote, `origen`); `documento` (PDF/escaneo, hash) | `checada.empleado_id` **no se guarda**: se resuelve por (reloj, código, fecha) para que un código reutilizado no reescriba historia | **IO**: `archivo_original`, `fila_rechazada`, `checada`, `documento`; único por clave de origen compuesta (idempotencia, P31) |
| Incidencias | `incidencia`; `incidencia_evento` (estado, actor, motivo); `incidencia_evidencia`; `contingencia`, `contingencia_empleado`; `movimiento_complementario` (origen `ADMINISTRATIVO_*`) | Referencia a checada original cuando exista; nunca crea una checada | **IO**: `incidencia_evento`, `movimiento_complementario` versionado; trigger `aprobador ≠ capturista` |
| Resultados | `resultado_semana` (empleado, patrón, semana, **versión**, estado, `version_motor`, `criterio_codigo`, `norma_version_id`, `politica_version_id`, `huella_entradas`); `segmento_resultado`; `alerta`; `alerta_reconocimiento`; `semana_cierre` | Una versión nueva por recálculo; vigente = máxima | **IO**: `resultado_semana`, `segmento_resultado`; el cierre no se sobrescribe (P42) |
| Autorización y reporte | `autorizacion_extra` (empresa donde se trabajó, segmento, estado, evento); `reporte_semanal` (folio, versión); `reporte_firma` (cuatro roles) | Autoriza la empresa del reloj de origen del segmento (RE03) | **IO** por eventos |
| Actas | `acta` (único: patrón+empleado+periodo de pago); `acta_version` (único acta+número); `acta_detalle`; `acta_firma_validacion`; `acta_evidencia` | Rectificación = nueva versión del mismo folio | **IO**: `acta_version`, `acta_detalle` tras emitir; sin reutilizar firmas |
| Alimentos | `derecho_alimento_dia` (empleado, fecha, desayuno/almuerzo/cena, regla usada) | Solo si hubo T.E. y existe regla configurada | Derivado versionado con el resultado |
| Seguridad | `usuario`; `rol`; `usuario_rol_empresa` (vigencia); `permiso`; `bitacora` | Roles por empresa y vigencia | **IO**: `bitacora` (actor de la aplicación, equipo, valores antes/después) |
| Sistema | `esquema_migracion` (id, nombre, checksum, fecha); `configuracion`; `respaldo_registro` | — | `PRAGMA user_version` espejo de la última migración |
| Reservado (diferido) | `outbox_publicacion`; `evento_movil` | UUID estable | No se crea hasta autorización (decisión 5) |

**Dos semanas.** El plan distingue «semana de pago» (acta, §18.1) de «semana de acumulación legal» (§5.3, RE01) «cuando difieran». Se modelan ambas con identificador estable y, por defecto, coinciden (pregunta abierta Q-A, §15).

---

## 8. Motor de jornada

### 8.1 Contratos

`calcular_semana(entrada: EntradaSemana) -> ResultadoSemana`, función pura. **No** lee la BD, el sistema de archivos ni la fecha del equipo.

`EntradaSemana` (todo explícito): empleado (id, fecha de nacimiento si aplica), patrón, semana laboral (inicio/fin con zona), checadas originales de **todos los relojes** de la semana con empresa/reloj de origen, complementos administrativos **aprobados** (marcados con su origen), aclaraciones pendientes, asignaciones de horario vigentes en cada día, versiones de norma/política/calendario aplicables por día, versión del motor y criterio. `ResultadoSemana`: segmentos, totales por categoría, pendientes, alertas, invariantes verificados, versiones usadas y `estado` (`calculado` | `provisional`).

### 8.2 Tubería (pasos del plan §5.1–5.3 como funciones)

| # | Plan | Función (módulo de `Dominio/`) | Entrada → salida |
|---|---|---|---|
| 1 | §5.1-3 | `ordenar_checadas` (`checadas`) | checadas → tupla ordenada por **instante**, no por importación (P32) |
| 2 | §5.1-2/3 | `marcar_checadas` (`checadas`) | → marcas `posible_duplicado` (ventana configurable; V1 fijaba 30 min y descartaba, R006), `futura`, `desfase`; **ninguna se elimina** |
| 3 | §5.1-4 | `emparejar` (`emparejamiento`) | secuencia unificada multi-reloj → intervalos entrada/salida + incidencias `impar`/`ambigua`/`traslape`; sin hora ficticia (P30); hueco entre empresas el mismo día → intervalo etiquetado «traslado entre empresas» o `pendiente` si excede el máximo versionado |
| 4 | §5.1-5 | `asignar_jornada_logica` (`calendario`) | intervalos → jornada lógica por día de inicio; separa segmentos por fecha real para vigencias y festivos (P26) |
| 5 | §5.1-6 | `resolver_contexto` (`normatividad`, `horarios`, `tolerancias`) | fecha trabajada → horario, norma, política, calendario; si falta alguno → `provisional` + AL12 (NL04, P33) |
| 6 | §5.2 | `construir_intervalos_efectivos` (`horarios`) | aplica descansos del horario (computable suma; no computable resta, «descanso según horario, sin checada», Q03); incorpora complementos aprobados; lo no confirmado queda **pendiente** |
| 7 | §5.2 | `segmentar` (`segmentacion`) | fronteras: inicio/fin de horario, descansos, medianoche, fin de semana, cambio de vigencia, agotamiento de topes; cada segmento conserva inicio, fin, duración, categoría base, etiquetas, regla y empresa/reloj de origen |
| 8 | §5.2 | `clasificar_base` (`regimenes`, `calendario`) | `dentro_de_horario` / `exceso_diario`; diurna/nocturna/mixta; etiquetas domingo, festivo, descanso trabajado (no se asumen extras, P29) |
| 9 | §5.2-1 | `extra_semanal` (`criterios_extra`) | `max(0, confirmado − tope_semanal_vigente)` (criterio «semanal con acuerdo») |
| 10 | §5.2-2 | `asignar_extra` (`criterios_extra`) | asigna la extra a los **excesos diarios más recientes** (consumo en orden cronológico inverso, división exacta de segmentos); si sobra, al final de los minutos programados + alerta HO03; nunca se pierde tiempo |
| 11 | §5.3 | `repartir_tramos` (`tramos_extra`) | cronológico: doble hasta el tope art. 66, resto triple; evalúa por separado 4 h/día, 4 días/semana y 12 h/día; exceso legal como etiqueta; minutos fuera de la distribución art. 66 → `extra_pendiente_clasificacion` (*propuesta*: el plan §5.3 pide «revisión jurídica» pero no fija la categoría; validar con asesor) |
| 12 | §4.3, §4.4 | `evaluar_tolerancias`, `evaluar_alertas` | diferencia real y administrativa por separado (TO05); AL01–AL14 con clave de deduplicación |
| 13 | §4.5, §17.1 | `derivar_alimentos` (`alimentos`) | solo con T.E. y regla configurada |
| 14 | §5.4 | `verificar_invariantes` (`invariantes`) | presencia = efectivo + descansos/no laborado + pendiente; efectivo = ordinario + extra + especial; sin totales negativos ni minutos duplicados; falla ⇒ error de programación visible, no resultado silencioso |

Pasos 1–2 de §5.1 («importar con idempotencia») **no** son motor: son `ServicioImportacion` (IO, hash, lotes). El motor recibe checadas ya persistidas.

**Criterio de inicio de extra como estrategia.** `criterios_extra` define un `Protocol` y un registro por código; hoy solo existe `semanal_con_acuerdo` (decisión del propietario 24/11/2026; `14 §5`). Si el reglamento STPS o el asesor lo cambian se agrega otra implementación y una versión de parámetro, **sin tocar el resto** (plan §5.2-4).

**Semana que cruza vigencias (28/12/2026–03/01/2027).** El plan §8 declara pendiente el criterio. El motor no prorratea ni aplica 46/48 a toda la semana: resuelve la norma por día, devuelve `estado=provisional` y alerta; la política «transición» es un parámetro versionado cuyo valor inicial es `provisional` (P34).

### 8.3 Resolución de parámetros versionados por fecha efectiva

`resolver_vigente(versiones, clave, fecha_trabajada)`: exactamente una versión cuyo `[desde, hasta)` contiene la fecha. Cero → `FaltaParametro` (resultado `provisional`, AL12; se conservan los datos). Más de una → `ParametroAmbiguo` (error; además lo impide un trigger de BD). La fecha es **la fecha trabajada del segmento**, no la de consulta (P36, P40, P50). Los valores salen siempre de datos: topes 2026–2030, 9/4 h, 12 h, 210 min nocturnos, 480/420/450, traslado 60 min, ventana de duplicados.

### 8.4 Persistencia del resultado

`ServicioCalculoSemana` ejecuta en **una unidad de trabajo**: cargar entradas → `calcular_semana` → insertar `resultado_semana` (versión n+1) + `segmento_resultado` + `alerta` (deduplicada) → bitácora. Cada resultado guarda `criterio_codigo`, `norma_version_id`, `politica_version_id`, `version_motor`, `huella_entradas` (SHA-256 de la serialización canónica de `EntradaSemana`) y `calculado_en`. Un recálculo no sobrescribe: crea versión nueva; una semana cerrada conserva su cierre y su fotografía y muestra la versión posterior como evento (P42, D17 del plan). Reproducir = volver a ejecutar con las mismas versiones y comparar huellas (P43, S15).

**Unidad interna (propuesta, decisión 2).** Instantes con segundos; el motor opera en **segundos enteros**; parámetros y horarios se guardan en minutos (decisión del propietario) y se multiplican ×60; los totales se **persisten en segundos** y se **muestran** HH:mm (o HH:mm:ss según la precisión de la fuente) sin redondear en perjuicio del trabajador (RE07). Razón: TO03 distingue 07:10 de 07:10:01 y Q02 exige conservar segundos.

### 8.5 Regímenes (NL07)

`regimenes.py` es una tabla de **estrategias por régimen** (general diurna, nocturna, mixta, parcial/reducida, menor 15–16, menor 16–18) que declara topes diarios, franja, prohibiciones (p. ej. menores: sin extra, domingos, descansos obligatorios, ni después de las 22:00; `00`, «Menores») y qué alertas dispara. Todos los regímenes están **modelados y probados** desde el inicio; su habilitación en operación es por configuración (Q14: no se esperan menores, pero se alerta si la fecha de nacimiento/CURP indica menos de 18).

---

## 9. Reutilización de V1

Rutas relativas a `D:\Proyectos\app_revisar_checadas` (símbolos confirmados por `grep` de lectura el 26/11/2026). «Dest.» = destino V2 propuesto; **negrita** = ajuste respecto del destino de la matriz.

| R | V1 `ruta:símbolo` | Decisión | Destino V2 |
|---|---|---|---|
| R001 | — (sin lector de reloj; Q01) | no aplica | — |
| R002 | `tiempo_extra/ClasesComunes/reloj_generico.py:62 cargar`; `helpers.py:209 es_formato_canonico`, `:218 seleccionar_hoja_canonica`, `:470 carga_checadas_del_empleado` | refactorizar | `Servicios/servicio_importacion.py` + `Servicios/formatos/canonico.py`; quitar filtro por empleado, persistir lote e idempotencia |
| R003 | `helpers.py:228 detectar_formato_reporte`, `:550 convertir_reporte_a_reloj`, `:854`, `:1005` conversores | refactorizar | `Servicios/formatos/{fichaje,timecard,ngteco}.py` (un parser por formato → filas canónicas); sin escribir `ACS*.xlsx`; informe de rechazos |
| R004 | `helpers.py:256 fecha_inicio_archivo`, `:1096 _parse_periodo_str`, `:1114`, `:1127`, `:1140` | adaptar | `Servicios/formatos/periodo.py` |
| R005 | `helpers.py:1157 _parse_datetime_flexible`, `:794 _normaliza_meridiano`, `:27 tiempo_12_a_24` | reutilizar | **`Servicios/formatos/parseo_fecha.py`** (entrada de texto = adaptación, no dominio); añadir zona |
| R006 | `helpers.py:520-526`; `reloj_generico.py:26,96-104` descarte ≤30 min | reemplazar | `Dominio/checadas.py::marcar_checadas` (marca, no descarta) |
| R007 | `forms/form_revisa_checadas.py:627 _on_dgv_reloj_keypress`, `:722` | reemplazar | `Dominio/emparejamiento.py` |
| R008 | `tiempo_extra/ClasesComunes/calculo_te.py:68 arma_dia` | reemplazar | `Dominio/emparejamiento.py` |
| R009 | `helpers.py:167 lista_semanas_laboradas`; `tiempo_extra/ClasesComunes/fechas.py:98`; `empresas.py:120` | reutilizar | `Dominio/calendario.py`; día de inicio como dato de `empresas` |
| R010 | `vista_tiempo_extra.py:140 _inicio_semana_sugerida` | reutilizar | `Controladores/controlador_revision.py` |
| R011 | `calculo_te.py:89 calcula_tiempo_extra`, `:40 DiaTE` | reemplazar | `Dominio/motor_jornada.py` (se conserva la **forma** del resultado diario con banderas) |
| R012 | `calculo_te.py:164 neto_semana` | reemplazar | `Dominio/criterios_extra.py`, `tramos_extra.py` |
| R013 | `config.py:26 DEFAULT_HORAS_MAX`, `:59 horas_max_para_anio` | reemplazar | `Modelos/modelo_normatividad.py` + migración semilla (datos) |
| R014 | `calculo_te.py:111-112`; `helpers.py:412-413`; `fechas.py:29-34` | reemplazar | `Dominio/tolerancias.py` + `modelo_politicas.py` |
| R015 | `tiempo_extra/Database/crear_bd.py:37 tabla empleados`; `models.py:21 Empleados` | reemplazar | `modelo_horarios.py` y asignaciones |
| R016 | `exportar_reporte.py:82 es_dia_laborable` | adaptar | `Dominio/calendario.py` (descanso/festivo/no programado/ausencia) |
| R017 | `tiempo_extra/Modelos/modelo_empleados.py:55 ModeloEmpleados`; `Vistas/vista_empleados.py:25 VistaEmpleados` | adaptar | `modelo_empleados.py`, `frm_empleados.ui`, `controlador_empleados.py` con baja lógica |
| R018 | `helpers.py:304 carga_catalogo_de_empleado` | reemplazar | — (solo migración, R019) |
| R019 | `modelo_empleados.py:96 importar_excel`, `_parse_hora :26`, `_parse_si :37`, `_parse_dia_descanso :43`; `dlg_importar_catalogo.py` | refactorizar | `Servicios/servicio_migracion_excel.py` + `Validadores/` |
| R020 | `tiempo_extra/Plantillas/crear_plantilla_empleados.py` | adaptar | `Plantillas/` |
| R021 | `modelo_registro_diario.py:36 guardar`, `:60 guardar_semana` | reemplazar | `modelo_incidencias.py` (nunca edita checadas) |
| R022 | `modelo_registro_diario.py:70 registrar_alteracion`, `:99 campos_alterados`, `:86 difiere_minuto` | adaptar | `Servicios/servicio_bitacora.py` / `modelo_usuarios` (usuario real) |
| R023–R024 | `form_revisa_checadas.py:796 _on_exportar_excel`, `:1038 _on_imprimir_pdf` | reemplazar | `Servicios/servicio_reportes.py` desde datos, no desde Excel |
| R025–R026 | `exportar_reporte.py:235 exportar_excel`, `:447 exportar_pdf`, `:95 _construir` | adaptar | `servicio_reportes.py` (paleta, logos y colores de incidencia; datos nuevos) |
| R027 | `config.py` (`obtener`, `actualizar`) | reemplazar | `modelo_configuracion.py`; preferencias locales fuera de Git |
| R028–R029 | `empresas.py` (`cargar_empresas`, `guardar_empresa`, `location_id_empresa :105`) | adaptar / reemplazar | `modelo_empresas.py` con ID estable |
| R030 | `tiempo_extra/Database/conexion_sqlite.py OperacionesSqlite`; `Modelos/modelo_base.py` | adaptar | `Database/conexion_sqlite.py` + `unidad_trabajo.py` (DV4) |
| R031 | `crear_bd.py:100 _MIGRACIONES`, `:109 _migrar` | adaptar | `Database/crear_bd.py::_aplicar_migraciones` + `esquema_migracion` |
| R032 | `style.qss`; `helpers.py:1233` | adaptar | `Recursos/Estilos/{base,light,dark}.qss` con propiedades dinámicas de estado |
| R033–R040 | `form_revisa_checadas.py`, `form_busca_empleado.py`, `form_admin_empresas.py`, `form_editar_empresa.py`, `form_tiempo_extra_ventana.py`, `vista_tiempo_extra.py`, `mensaje.py` | reemplazar / adaptar / refactorizar | Pantallas MVC de §6; se reutilizan flujos de usuario y patrón maestro-detalle |
| R041 | `excel_helpers.py:13 SLDocument`; `tiempo_extra/ClasesComunes/excel_sl.py:15 SLDocument` | refactorizar | `Servicios/` (una sola utilidad sobre `openpyxl`) |
| R042 | `fechas.py:69 validar_hhmm`, `:49 hhmm_a_decimal`, `:37 decimal_a_hhmm`; `dominio.py:33 cs_dayofweek` | reutilizar | `Dominio/tiempo.py` en minutos/segundos (sin convención C#) |
| R043 | `models.py` (`DatosReloj`, `Empleados`, `EmpleadoRevisado`, `ResultadoHorasCalculadas`) | reemplazar | `Dominio/modelos.py` (dataclasses con ID y versión) |
| R044–R046 | `instalador.json`; `compilar.ps1`, `build.ps1`; `main.py:47 _manejar_excepcion` | adaptar / reemplazar | `instalador.json`, `compilar_ui.bat`, `main.py` con log a archivo sin datos personales |
| R047 | `tests/` (34 funciones) | reutilizar | Valores esperados como **tabla de caracterización** en `tests/caracterizacion/`; no se importa código de V1 |

Requisitos sin equivalente (D01–D22) se asignan a los módulos de §6 (columna «Matriz»). **Restricción:** ninguna prueba de V1 se ejecuta desde V2; la comparación V1↔V2 usa exportaciones de una copia aislada y datos sintéticos (plan caps. 20–21; matriz 13 R047). Dependencias a validar antes de aprobar R025/R026/R041: ver decisión 6.

---

## 10. Seguridad, bitácora y respaldo

### 10.1 Cuentas y separación de funciones (PC compartida, Q13)

| Rol (por empresa y vigencia) | Puede | No puede |
|---|---|---|
| Auxiliar administrativo (elabora) | Cargar reportes del reloj, capturar aclaraciones y contingencias, generar el reporte semanal | Aprobar lo que capturó; cerrar; editar normativa |
| Autorizador (designado por la empresa) | Aprobar/rechazar aclaraciones y T.E. de los segmentos **trabajados en su empresa** | Aprobar lo que él capturó; cerrar la semana |
| RH (revisa) | Validar y cerrar el reporte; confirmar calendario; validar firmas de acta | Aprobar aclaraciones propias |
| Dirección (Vo.Bo.) | Firma el reporte; sin usuario propio (en AEI coincide con el autorizador) | — |
| Perfil normativo *(decisión 8)* | Crear versiones de parámetros normativos con fundamento | Operar el día a día |

Controles: **identidad de la aplicación** en la bitácora (no el usuario de Windows, plan §22.1); hash de contraseña con sal (decisión 6) y bloqueo por intentos; permisos validados en controlador **y** servicio **y** modelo para operaciones críticas (doc. maestro §19) y por trigger donde sea posible (`aprobador ≠ capturista`, vigencia de rol). Los botones deshabilitados no son seguridad.

### 10.2 Bitácora

`bitacora` es **IO** con: fecha/hora, usuario, empresa, equipo, módulo, registro, acción, valor anterior y nuevo, motivo (doc. maestro §15; plan §6, cap. 28). Se escribe en la **misma unidad de trabajo** que el cambio. *Opcional (propuesta):* cadena de hash entre filas como evidencia de manipulación; complementa y no sustituye controles (plan §28). Registrar también exportaciones, descargas y reimpresiones (cap. 18.4).

### 10.3 Respaldo y restauración (Herramientas → Respaldar/Restaurar, Q15)

1. `sqlite3.Connection.backup()` (Online Backup API) hacia un archivo temporal en el **volumen de destino**; nunca copiar el `.db` en caliente ni con WAL pendiente (plan §22.3; doc. maestro §11.2).
2. Sobre la copia: `PRAGMA integrity_check`, `PRAGMA foreign_key_check`, conteos por tabla.
3. Incluir en el mismo punto lógico `data/archivos/` (originales del reloj con hash, PDF emitidos, escaneos, **fotos de empleados con su historial**), calendarios, horarios, parámetros y bitácora; **manifiesto** JSON con ruta, tamaño y SHA-256 de cada pieza, versión de esquema y versión de app.
4. Escritura atómica: temporal → verificación → renombrado; registro en `respaldo_registro` (doc. maestro §13.3).
5. Destino elegido por el usuario (USB, OneDrive, otra unidad); V2 lo recuerda, avisa si el último respaldo **fuera del equipo** es antiguo y rechaza como destino de la BD **activa** una ruta UNC o sincronizada (S11); el respaldo sí puede ir a una carpeta sincronizada (plan §22.3). Cifrado: ver pregunta abierta Q-E.
6. Respaldo automático diario y **antes de cada migración o cierre**; rotación configurable.
7. Restauración: valida versión de esquema, `integrity_check` y hashes; crea primero un respaldo de seguridad de la BD actual; nunca restaura «a ciegas» datos posteriores (plan §10 migración, cap. 20-8).
8. Retención: V2 **no borra nada automáticamente** (art. 804 LFT, `00`; STPS puede fijar otro plazo).

### 10.4 Archivos

Originales del reloj, PDF emitidos, escaneos firmados y fotos de empleados (redimensionadas, p. ej. JPEG comprimido; tamaño y calidad configurables) se guardan como **archivos direccionados por hash** (`data/archivos/<sha256[:2]>/<sha256>`) con metadatos y SHA-256 en BD, escritura temporal → verificación → publicación y recuperación de operaciones interrumpidas (S14). Alternativa BLOB en decisión 3. El hash es control técnico, no firma legal (plan cap. 15–16).

---

## 11. Migraciones, versión de BD y empaquetado

**Migraciones (doc. maestro §12.1, §5.1; patrón `Mi_Tiendita`, R031).**
- Archivos `Database/migraciones/NNNN_descripcion.sql`; tabla `esquema_migracion(id, nombre, checksum, aplicada_en)` + `PRAGMA user_version`.
- `crear_bd.py::_aplicar_migraciones` al arrancar: abre con PRAGMAs, toma **respaldo automático si hay migraciones pendientes** (S10), ejecuta cada migración en transacción, es **idempotente** (registro + `IF NOT EXISTS`; probada dos veces, doc. maestro §18.3) y no borra datos sin proceso explícito y respaldado.
- Si `user_version` de la BD > la soportada por la app (instalación más antigua), **se niega a abrir** y avisa, sin tocar nada.
- Semillas normativas (2026–2030, art. 74) viajan como migración de **datos** con `estado='propuesta'` y `fundamento` citando el decreto, para que el perfil normativo las confirme (NL03). Los textos legales definitivos se verifican contra DOF/LFT antes de liberar (plan §30.4).
- Arranque de instancia única (`QLockFile`) para respetar «una PC, un escritor» (S06).

**Empaquetado (CLAUDE.md SSD «Instalación»; doc. maestro §18).**
- `instalador.json` con `"runtime": "PyPortable314"` (soportado, `_instaladores\empaquetar.ps1:79-81`), excluye `*.db`, `data/`, `tests/`, `Documentacion/`, `odd/`; versión `minor` por función, `patch` por corrección.
- `Instalar.ps1` copia con `robocopy /XF *.db`: jamás sobrescribe una BD; solo siembra una semilla si no hay ninguna. Ubicación de datos: decisión 4.
- Paquete ZIP «SAC-proof» con `pythonw.exe`, sin `.exe` propio ni Inno Setup, instalación por usuario en `%LOCALAPPDATA%\Programs\MisApps\ControlLaboral`.
- Criterios de liberación: UI/QRC recompilados, pruebas aprobadas, migraciones probadas dos veces, BD real excluida, instalación limpia **y** actualización verificadas (doc. maestro §18.3).
- `compilar_ui.bat` y `.vscode/settings.json` calcados del patrón del doc. maestro (§9–§10) apuntando a `PyPortable314`.

---

## 12. Estrategia de pruebas

Runner: `PyPortable314\python.exe -m pytest -q` (pytest 9.1.1 verificado en el portátil; `pytest-qt` **no** está instalado: las pruebas de UI crean `QApplication` con `QT_QPA_PLATFORM=offscreen`, doc. maestro §7.5). Sin dependencia del reloj del equipo ni de la fecha actual (plan cap. 9): el dominio no llama a `now()`; los servicios reciben `ProveedorFecha`.

```text
tests/
├── dominio/            P-01…P-50 (plan cap. 9) + A/B/C/D aplicables; sin Qt ni SQLite; pureza (§3)
├── unit/               modelos, validadores, arquitectura de importaciones, controladores con dobles
├── integration/        repositorios, migraciones (BD vacía, existente, repetida), importación, respaldo, concurrencia
├── ui/                 creación de pantalla, widgets obligatorios, claro y oscuro (offscreen + grab())
├── comparativas/       V1↔V2 sobre semanas sintéticas (diferencias explicadas; plan caps. 20–21)
├── caracterizacion/    valores esperados derivados de V1 (R047), como referencia y no como oráculo legal
├── fixtures/           semanas sintéticas, Excel sintéticos por formato (nunca datos reales)
└── conftest.py
```

| Nivel | Qué prueba | Casos del plan |
|---|---|---|
| Dominio (tabla) | Matriz P01–P50 (2026–2030, tramos doble/triple en 9/10/11/12 h, tolerancias, descansos, nocturna/mixta, duplicados, orden, sin horario, cruce de año, recálculo, histórico) y los ejemplos del §5.2 (06:50/12:00/13:00/16:25; 5×8+6 con compensación; horario 48 h → HO03) | P01–P50; C02–C03, C08 |
| Dominio (propiedades) | Invariantes §5.4 con semillas fijas (`random.Random(seed)`; `hypothesis` no está instalado): permutar el orden de entrada no cambia el resultado (P32); duplicar lote no cambia totales (P31); sin minutos duplicados; sin totales negativos | P31, P32, P44 |
| Dominio (multi-empresa) | Dos relojes, entrada en una empresa y salida en otra, traslado ≤/> máximo, traslape, autorización por empresa del segmento | P45; plan §5.1-4 |
| Servicios/repositorios | SQL, parámetros, transacciones; `ServicioCalculoSemana` con repositorio SQLite **y** en memoria (mismo resultado, S15); idempotencia de importación; Excel sintéticos por formato con conteo leídas/rechazadas | S02, S06, S15; A07–A09 |
| Migraciones | BD vacía, existente y repetida; migración fallida con restauración; BD más nueva que la app | S10 |
| Integridad | Triggers: intentar `UPDATE`/`DELETE` de checada, bitácora, acta emitida → rechazo; `CHECK` de tolerancia; unicidad de acta; solapes de vigencia | S03–S05; A10 |
| Seguridad | Roles, `aprobador ≠ capturista`, acceso denegado y auditado | P37; B13; C15; D21 |
| Respaldo | Con WAL activo; restaurar; hashes y conteos; actas y firmas recuperables | S08, S09; B15; D24 |
| UI | Pantalla se crea, nombres con prefijo, claro/oscuro, estado vacío, colores §7.3 por propiedad dinámica | doc. maestro §16.2-6 |
| Compilación | Todos los `.ui`/`.qrc` generan Python válido y importable | doc. maestro §16.2-8 |

**Identificadores.** Los IDs del plan chocan entre capítulos: `A01–A10` (cap. 3) vs `A01–A18` (§15.3) y `P01–P50` (§9) vs `P01–P12` (cap. 29). Se propone prefijar en archivos y reportes: `P-xx` (cap. 9), `PUB-xx` (cap. 29), `AUD-xx` (cap. 3), `ACL-xx` (§15.3); los capítulos B, C, D, E, S, W, M no colisionan.

**Criterio de terminado por módulo** (doc. maestro §16.4): compila, ejecuta con `PyPortable314`, pasa pruebas, sin errores de importación, conserva la arquitectura, claro/oscuro si toca UI, no altera una BD de producción. Pruebas de volumen: medir (≈ 200 empleados × 4 checadas/día × 365 ≈ 0,3 M filas/año/empresa, **estimación**) y fijar metas con el responsable técnico; sin inventar SLA (plan cap. 9).

---

## 13. Plan de construcción por entregas

**Realidad de calendario (Hecho).** Hoy es 26/11/2026; V2 debe calcular desde el 01/01/2027 (Q07) = **36 días naturales**. La semana 28/12/2026–03/01/2027 (si inicia lunes) es de transición y su criterio legal está **pendiente** (plan §8). No se estiman horas de esfuerzo aquí; se ordena por valor y riesgo, y se marca una **línea de corte**.

| Entrega | Rebanada vertical (coherente y demostrable) | Incluye | Criterio de salida |
|---|---|---|---|
| **E0** Esqueleto | Aplicación vacía que arranca | Árbol §4.1, `run.bat`, `compilar_ui.bat`, `.vscode`, `ModeloBase`, `Database/` + `crear_bd` + `esquema_migracion`, tema claro/oscuro, ventana principal con sidebar, `pytest.ini`, prueba de arquitectura | Arranca con `PyPortable314`; migración repetible; `.ui` compila |
| **E1** Dominio núcleo *(en paralelo con E0; sin UI)* | Motor completo y probado | `tiempo`, `normatividad`, `regimenes`, `calendario`, `checadas`, `emparejamiento`, `horarios`, `segmentacion`, `criterios_extra`, `tramos_extra`, `tolerancias`, `alertas`, `invariantes`, `motor_jornada` | P-01…P-50 pasan; prueba de pureza; ejemplos §5.2 |
| **E2** Catálogos | Capturar la estructura real | `empresas` (+ centros y relojes), `empleados` (códigos, patrón, baja lógica, foto opcional con cámara), importación única de Excel, `horarios` y asignaciones, `calendario` anual, `normatividad` (lectura + semilla), `politicas` | Una empresa de prueba capturada de punta a punta con datos sintéticos |
| **E3a** Conversión de formatos *(adelantada tras E1-T7; decisión del propietario, 28/11/2026)* | De archivo del reloj (Excel o CSV) a filas en formato Genérico, sin BD | Registro de formatos en `Servicios/Relojes/formatos/`: un módulo por formato (nombre, `reconoce()`, `convertir()`), agregar uno nuevo no toca los existentes; parten de los 5 detectores/conversores de V1 (R003) más CSV (V1 no lo lee). **Detección automática como en V1, nadie elige**, pero cada formato se evalúa por separado: exactamente uno coincide → se convierte y el informe nombra el formato detectado; ninguno → rechazo con mensaje; dos o más → se detiene y el usuario elige (V1 tomaba el primero en orden, lo que podría convertir con el formato equivocado en silencio). Informe de filas leídas/convertidas/rechazadas; pruebas con archivos sintéticos por formato | Cada formato reconocido y convertido con su archivo sintético; ambigüedad y no reconocido probados; ninguna fila descartada en silencio |
| **E3** Importación y checadas | De archivo del reloj a checadas inmutables | `servicio_importacion`, parsers (formato Genérico + los que use cada empresa), `checadas` (visor), triggers IO, hash y lotes | Reimportar no duplica (P31); informe de rechazos; original intacto (S05) |
| **E4** Revisión semanal *(primera rebanada operativa)* | Importar → calcular → revisar | `servicio_calculo_semana`, resultados versionados, `revision` diaria/semanal con colores §7.3, alertas básicas, usuarios y bitácora **mínimos**, **respaldo/restauración manual** | Una semana sintética 2027 calculada y reproducible; respaldo restaurable; ningún dato real sin respaldo |
| **E5** Aclaraciones y firmas | Flujo auxiliar → autorizador → RH | `incidencias` (aclaraciones), `autorizaciones`, reporte semanal xlsx/pdf con 4 firmas y colores, roles completos por empresa | Aclaración no altera la checada; autor ≠ aprobador; reporte reimprimible |
| **E6** Distribución | Instalable y actualizable | Respaldo automático, `empaquetar.ps1`, instalación limpia y actualización conservando BD, manual breve | Paquete probado; BD intacta tras actualizar |
| **E7** Actas e histórico | Caps. 16–18 | `actas` (folio único, versiones, PDF congelado, firmas), `consulta_historica`, contingencias (cap. 17), alimentos por T.E., exportación a autoridad **solo** si STPS publica formato | Casos B/C/D del plan |
| **E8+** Diferidos | Supabase, portal, móvil | `publicacion`, web, móvil | Requieren autorización expresa (AGENTS.md) |

**Línea de corte para el 01/01/2027 (propuesta, decisión 7):** E0–E4 + usuarios básicos + respaldo manual constituyen el mínimo para arrancar la **operación paralela** con V1 como respaldo (plan cap. 20; Q07). E5–E7 se completan durante la paralela, sin afectar la integridad de lo ya capturado porque cada entrega es aditiva (migraciones). Las pantallas son el cuello de botella probable: cada `.ui` se diseña a mano en Qt Designer (regla 4 del SSD) y no puede generarse por código.

**Riesgo marcado:** si E1 no queda validado con P-01…P-50 antes de mediados de diciembre, el arranque con datos reales de 2027 no es responsable; la alternativa es conservar V1 como sistema de registro para las primeras semanas y arrancar V2 en paralelo con semanas ya cerradas (decisión 7, alternativa).

---

## 14. Decisiones que requieren aprobación del propietario

1. **Paquete `Dominio/` puro para el motor, con `Modelo<X>` como fachada delgada en los módulos del motor** (DV1, DV2; se aparta del árbol del doc. maestro §4 y de «reglas de negocio en el modelo», §3.2). *Recomendación:* aprobar; el plan §22.1 y AGENTS.md lo exigen y la matriz 13 ya lo asumía. *Alternativa:* poner el motor en `Servicios/motor_jornada/` (sin carpeta nueva, cero desviación del árbol), puro por convención y vigilado por la prueba de pureza. *Tradeoff:* la alternativa evita pedir una excepción pero mezcla código puro con servicios que sí hacen E/S, y la pureza depende de disciplina en lugar de estructura. **Decisión del propietario (26/11/2026): aprobada la recomendación.**
2. **Unidad interna y de persistencia del cálculo: segundos enteros** (parámetros y horarios en minutos; presentación HH:mm). *Recomendación:* segundos. *Alternativa:* minutos enteros truncando al importar. *Tradeoff:* los minutos simplifican reportes y coinciden con «minutos como unidad», pero pierden los segundos que Q02 pide conservar y hacen imposible distinguir 07:10 de 07:10:01 (TO03). **Decisión del propietario (26/11/2026): aprobada la recomendación.**
3. **Archivos (originales del reloj, PDF emitidos, escaneos firmados y fotos de empleados; la foto sigue la misma elección, no es una decisión aparte): archivos direccionados por hash en `data/archivos/` con metadatos y SHA-256 en BD**. *Alternativa:* BLOB dentro de SQLite. *Tradeoff:* el BLOB da un único archivo y respaldo transaccional más simple, pero la BD crecerá con escaneos semanales por empleado, vuelve más lentos respaldo y restauración y complica abrir/reimprimir el PDF exacto; los archivos exigen manifiesto y recuperación de escrituras interrumpidas (plan §22.3 pide medir antes de elegir). **Decisión del propietario (26/11/2026): aprobada la recomendación.**
4. **Ubicación de la base y los archivos en producción: `%LOCALAPPDATA%\MisApps\ControlLaboral\data\`, fuera de la carpeta de instalación.** *Alternativa:* `data\` dentro de la carpeta instalada (como `ubicacion_bd.json` de `Mi_Tiendita`). *Tradeoff:* afuera, una reinstalación o desinstalación no puede tocar los datos y se bloquea por diseño cualquier ruta de red; dentro, se mantiene el patrón conocido y la portabilidad entre PC del desarrollador, pero depende de que `Instalar/Desinstalar.ps1` respete siempre `*.db` y `data\`. **Decisión del propietario (26/11/2026): aprobada la recomendación.**
5. **Costuras para Supabase/móvil desde el inicio: columna `uuid` estable en las entidades publicables; la tabla `outbox` se difiere.** *Alternativa:* agregarlo todo en la fase de publicación. *Tradeoff:* el UUID cuesta casi nada hoy y es muy caro reconstruir cuando ya hay historia firmada; el outbox sin consumidor es código muerto y su contrato aún no está aprobado (plan §24). **Decisión del propietario (26/11/2026): aprobada la recomendación.**
6. **Dependencias adicionales (AGENTS.md exige aprobación):** `openpyxl` 3.1.5 (Excel), `reportlab` 5.0.0 (PDF), `bcrypt` 5.0.0 (contraseñas) y `tzdata` (necesaria para `zoneinfo` en Windows); todas ya están en `PyPortable314`. *Salvedad verificada:* `openpyxl` declara clasificadores solo hasta 3.11 (CLAUDE.md SSD); funciona al ser Python puro, pero requiere prueba con 3.14. *Alternativa para contraseñas:* `hashlib.scrypt` de la biblioteca estándar (sin dependencia). *Tradeoff:* `bcrypt` es el estándar conocido y ya está disponible; `scrypt` evita una dependencia a costa de parámetros propios. **Decisión del propietario (26/11/2026): aprobada la recomendación.**
7. **Alcance mínimo para el 01/01/2027: E0–E4 + usuarios básicos + respaldo manual**; aclaraciones, firmas, actas, histórico y empaquetado completo se entregan durante la operación paralela con V1 como respaldo. *Alternativa:* no arrancar V2 con datos reales hasta tener también E5–E6 y usar V1 para las primeras semanas de 2027. *Tradeoff:* el recorte llega a tiempo pero V2 opera algunas semanas sin el flujo de aclaraciones firmadas (se compensa con la operación paralela); la alternativa es más completa pero prolonga la dependencia de V1 y retrasa la validación real del motor. **Decisión del propietario (26/11/2026): aprobada la recomendación.**
8. **Perfil que administra los parámetros normativos (NL03 pide «perfil autorizado» sin definirlo):** rol **«Administrador normativo»** asignado a una persona designada por el propietario, distinto de RH operativo y del auxiliar. *Alternativa:* asignarlo al rol RH de cada empresa. *Tradeoff:* un perfil único y auditado evita que cada empresa tenga versiones distintas de la ley; RH lo haría más ágil pero reparte una responsabilidad legal en tres personas. **Decisión del propietario (26/11/2026): aprobada la recomendación.**
9. **Prefijos de widgets: seguir la tabla del doc. maestro §5.2** (`qled` para `QLineEdit`, `qpte`, `qtxe`, `qfrm`, `grp`, `chk`…) *en lugar de* la lista abreviada de AGENTS.md y CLAUDE.md SSD (`qtxt`). *Alternativa:* adoptar `qtxt` y ampliar el doc. maestro. *Tradeoff:* el doc. maestro es más completo y tiene mayor precedencia (§1.1 lo coloca sobre el CLAUDE.md del SSD) y evita ambigüedad entre `QLineEdit` y `QTextEdit`; `qtxt` obligaría a modificar un documento común a todos los proyectos. **Decisión del propietario (26/11/2026): aprobada la recomendación.**

---

## 15. Riesgos y preguntas abiertas

### 15.1 Riesgos

| # | Riesgo | Mitigación propuesta |
|---|---|---|
| R1 | 36 días al 01/01/2027; diseño de `.ui` manual | Línea de corte (§13); E1 sin UI en paralelo; V1 como respaldo (Q07) |
| R2 | Criterios legales abiertos: Q05 provisional, lecturas (A)/(B) del art. 61, semana de transición, STPS sin publicar (`14 §2–§6`, plan §8, cap. 15) | Criterio como parámetro versionado; resultado `provisional` con alerta; no prorratear; dictamen del asesor antes de liberar |
| R3 | Formatos de reporte de CATAB y BATAB desconocidos (V1 cubre 4 formatos, R003) | Un parser por formato en `Servicios/formatos/`; pedir un Excel sintético o anonimizado por empresa antes de E3 |
| R4 | Emparejamiento con solo entrada/salida sin tipo de movimiento: una checada faltante desfasa todas las siguientes (Q03) | Marcar `impar`/`ambigua`, pedir aclaración, **no adivinar**; mostrar la causa en la revisión diaria |
| R5 | Una PC y un archivo SQLite = punto único de falla (Q13) | Respaldo automático + manual con destino externo; alerta de respaldo antiguo; UPS recomendado (plan §22.3) |
| R6 | Los triggers no protegen frente a quien controla el archivo | Permisos del SO, bitácora, respaldos y cadena de hash opcional (plan §22.2) |
| R7 | `openpyxl` sin soporte 3.14 declarado | Prueba de lectura/escritura sobre libros sintéticos en E3/E5 |
| R8 | Importación de empleados: la misma persona en varias empresas puede unirse mal | Vista previa con propuesta de unión; **confirma RH**; nunca automática (plan §13.2) |
| R9 | No se leyó el código de `Mi_Tiendita`/`ControlDeAlmacen` más allá de `modelo_base.py` y listados | Antes de E0, revisar `ControlDeAlmacen` (primero en `PyPortable314`, con `Repositorios/`, `permisos.py`, `temas.py`) como referencia de 3.14 y de repositorios |
| R11 | Foto: dato personal; cámara ausente, ocupada o sin permiso de Windows; `QtMultimedia` depende de los códecs de ffmpeg incluidos en el portátil | Aviso de privacidad y consentimiento registrados; fallback a archivo; permisos de consulta como el expediente; prueba de captura en la PC real en E2; la foto no sale en reportes publicados ni en Supabase |
| R10 | Un cambio en normativa llega con el sistema en producción | Nuevas versiones de parámetro sin tocar código; recálculo versionado, nunca sobrescribe cierres |

### 15.2 Preguntas abiertas

- **Q-A.** ¿La «semana de pago» (acta, §18.1) coincide con la «semana de acumulación legal» (RE01)? Si difieren, ¿quién define el calendario de pago?
- **Q-B.** El plan (cap. 16) habla de «jefe de personal» que firma el acta; los usuarios definidos en §6 son auxiliar, autorizador y RH. ¿«Jefe de personal» = RH?
- **Q-C.** ¿Qué formato exportan los relojes de CATAB y BATAB? (R3).
- **Q-D.** Ventana de duplicados: ¿se conserva el valor de 30 min de V1 como valor inicial configurable?
- **Q-E.** ¿Se cifra el respaldo que sale del equipo? Requeriría una biblioteca no instalada hoy (la biblioteca estándar no ofrece cifrado simétrico); se recomienda en plan §22.3.
- **Q-F.** «Mismo día» del traslado entre empresas: ¿se interpreta por jornada lógica cuando el turno cruza medianoche? (plan §5.1-4 no lo precisa).
- **Q-G.** Categoría de los minutos extra fuera de la distribución del art. 66 (paso 11): `extra_pendiente_clasificacion` es propuesta; validar con el asesor laboral.
- **Q-H.** Política de conservación y purga de evidencia: V2 no purga; falta el plazo definitivo (art. 804 y STPS).

### 15.3 Conflictos entre fuentes (para resolver sin inventar requisitos)

| # | Conflicto | Referencias |
|---|---|---|
| C1 | El doc. maestro fija **un único runtime `PyPortable311`/3.11.9/PySide6 6.11.1**; el SSD y AGENTS.md declaran la migración a 3.14.7/6.11.2 | doc. maestro §2.5, §8, §9.1, §16.3, §23 vs CLAUDE.md SSD «Migración» y AGENTS.md |
| C2 | CLAUDE.md SSD cita el doc. maestro como `VS_SivemaMVC_PY\…` «v1.0, 1159 líneas» y remite prefijos a «§2 y §4»; el archivo real está en `VS_SIVEMA_MVC_PY\` (la carpeta `VS_SivemaMVC_PY` existe pero está vacía), es v1.1 y los prefijos están en §5.2 | CLAUDE.md SSD vs doc. maestro cabecera, §5.2 |
| C3 | Prefijos: AGENTS.md y CLAUDE.md SSD listan `qtxt`; el doc. maestro usa `qled/qpte/qtxe` (no existe `qtxt`) | AGENTS.md «UI»; doc. maestro §5.2 (decisión 9) |
| C4 | AGENTS.md remite «colores, zonas y control activo/inactivo» al doc. maestro §5–§7: el control activo está en §5.3; los colores en §7.3 son semánticos y el doc. maestro no define «zonas» | AGENTS.md; doc. maestro §5.3, §7.3 |
| C5 | Plan cap. 0/§1/§12: «no elegir tecnología antes de la auditoría» vs AGENTS.md (stack decidido 24/11/2026, **prevalece**) | plan cap. 0 y §1 último párrafo vs AGENTS.md |
| C6 | IDs de prueba duplicados entre capítulos (A01–A10 vs A01–A18; P01–P50 vs P01–P12) | plan §3, §9, §15.3, cap. 29 (propuesta en §12) |
| C7 | Plan §22.1 pide **interfaces de repositorio** y «presentación, casos de uso, dominio y persistencia»; el doc. maestro §3.1 define Vista → Controlador → Modelo/Servicio → Repositorio, sin capa «dominio» | plan §22.1 vs doc. maestro §3.1 (resuelto en §3 con DV1–DV2) |
| C8 | Plan §22.2 prefiere `synchronous=FULL` y WAL «evaluado»; doc. maestro §11.2 pide WAL «cuando se justifique» y documentar el cierre seguro | plan §22.2 vs doc. maestro §11.2 (se adopta FULL + WAL; documentar cierre seguro y expulsión del SSD) |
| C9 | Plan cap. 14 original afirmaba que V1 no permite modificar checadas; la auditoría lo corrigió (R022) | plan cap. 14 «Corrección» vs `01` A07 |
