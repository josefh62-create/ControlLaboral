# E1 — Motor de jornada (Dominio núcleo)

## Objetivo
Motor de cálculo puro en `Dominio/` — `calcular_semana(EntradaSemana) -> ResultadoSemana` — que convierte las checadas de una semana en tiempo efectivo, ordinario, extraordinario (doble/triple), pendientes, alertas e invariantes verificados, conforme al plan maestro §4–§5 y al doc 03 §8. Sin UI, sin BD, sin fecha del sistema.

## Problema y por qué
Es la parte donde un error cuesta dinero o una multa: decide dónde empieza la hora extra, el cruce doble/triple y las alertas legales de la reforma 2027–2030. Debe quedar validado con la matriz P-01…P-50 (plan cap. 9) antes de mediados de diciembre de 2026 (doc 03 §13, riesgo marcado) para arrancar la operación paralela el 01/01/2027.

## Alcance autorizado
- Módulos de `Dominio/` listados en doc 03 §4.1 y la tubería de doc 03 §8.2.
- Pruebas en `tests/dominio/`.
- Fuera de alcance: servicios, repositorios, SQL, UI (E2–E4). Los casos P de nivel servicio (P31 importación, P37 permisos, P42–P44 versiones/respaldo/exportación, P48 persistencia de alertas) se cubren aquí solo en su parte pura (p. ej. clave de deduplicación, huella de entrada) y se completan en E3/E4.
- V1 (`D:\Proyectos\app_revisar_checadas`) estrictamente de solo lectura; se puede leer como referencia (doc 13), nunca escribir ni ejecutar.

## Restricciones
- `Dominio/` solo stdlib (más `zoneinfo`/`tzdata`); sin PySide6, sqlite3, E/S ni `now()/today()/time()` — lo vigila `tests/arquitectura/test_pureza_dominio.py`.
- Segundos enteros internamente; parámetros en minutos ×60; sin redondeo en perjuicio del trabajador (RE07).
- Dataclasses inmutables (`frozen=True`); resultados deterministas (mismo resultado con entradas permutadas).
- Los valores legales vienen de datos versionados por fecha trabajada (`resolver_vigente`), nunca constantes en el código del cálculo. Las semillas legales (topes 2026–2030, 9 h, 12 h, franja nocturna, etc.) viven en un módulo de datos del dominio con su fundamento (doc 00).
- Lo no resuelto legalmente (semana de transición 28/12/2026–03/01/2027, minutos fuera de distribución art. 66) queda `provisional`/`pendiente` con alerta, nunca se inventa criterio.
- Identificadores de prueba: `P-xx` para el plan cap. 9 (doc 03 §12).

## TDD y pruebas
- Modo TDD: **activado** (fuente: elección explícita del propietario, 26/11/2026).
- Ciclo obligatorio por comportamiento: RED observado (prueba falla por la razón correcta) → GREEN mínimo → REFACTOR, con la salida de pytest como evidencia en el reporte del writer.
- Runner: `..\PyPortable314\python.exe -m pytest -q` desde la raíz del repo.

## Tareas
Rutas: todas delegadas (disparador: 2+ archivos no triviales + lectura de preparación del plan/doc 03/doc 00).

- [x] T1 — Tiempo y normatividad: `tiempo.py` (segundos, intervalos, HH:mm / HH:mm:ss), `modelos.py` (dataclasses base), `normatividad.py` (`resolver_vigente`, `FaltaParametro`, `ParametroAmbiguo`, semilla de topes 2026–2030 y límites NL), `regimenes.py` (estrategias diurna/nocturna/mixta/parcial/menores con topes y prohibiciones). Casos: P-36, P-39, P-40, P-49, P-50 (resolución), NL02, NL05, NL06.
- [ ] T2 — Checadas y emparejamiento: `checadas.py` (orden por instante, marcas duplicado/futura/desfase sin descartar), `emparejamiento.py` (secuencia unificada multi-reloj, impar/ambigua/traslape, traslado entre empresas con tope versionado). Casos: P-30, P-31 (parte pura), P-32, P-45.
- [ ] T3 — Calendario, horarios y tolerancias: `calendario.py` (semana laboral, jornada lógica por día de inicio, festivo/descanso/domingo, calendario faltante → provisional), `horarios.py` (minutos ordinarios HO02, compatibilidad HO03/HO06, descansos computables/no computables, complementos aprobados), `tolerancias.py` (TO01–TO07). Casos: P-18–P-25, P-29, P-33, P-41.
- [ ] T4 — Segmentación y clasificación base: `segmentacion.py` (fronteras horario/descanso/medianoche/semana/vigencia), clasificación dentro de horario / exceso diario, diurna/nocturna/mixta, etiquetas domingo/festivo/descanso trabajado. Casos: P-26, P-27, P-29.
- [ ] T5 — Extra semanal y tramos: `criterios_extra.py` (Protocol + registro; `semanal_con_acuerdo`, asignación a excesos más recientes, remanente + HO03), `tramos_extra.py` (doble hasta tope art. 66, resto triple; 4 h/día, 4 días/semana, 12 h/día; exceso legal; `extra_pendiente_clasificacion`). Casos: P-01–P-17, P-35, P-38, P-46, P-47 y ejemplos plan §5.2.
- [ ] T6 — Alertas, alimentos e invariantes: `alertas.py` (AL01–AL13 + clave de deduplicación), `alimentos.py` (regla configurable por empresa y vigencia), `invariantes.py` (plan §5.4). Casos: P-28, P-48 (clave), AL01–AL13.
- [ ] T7 — Composición: `motor_jornada.py` (`calcular_semana`, `estado` calculado/provisional, versiones usadas, huella de entrada SHA-256 canónica), semana de transición P-34, pruebas de propiedades con semillas fijas (permutación P-32, duplicados P-31, sin minutos duplicados ni negativos), caso multi-empresa extremo a extremo.

## Criterios de aceptación (doc 03 §13, E1)
- P-01…P-50 en su parte pura pasan; los de nivel servicio quedan anotados como diferidos a E3/E4 con su razón.
- Ejemplos del plan §5.2 pasan (06:50/12:00/13:00/16:25; 5×8+6 con compensación; horario 48 h → HO03).
- Prueba de pureza del dominio y de dirección de capas en verde.
- Ninguna constante legal en el código de cálculo; todo por `resolver_vigente`.

## Verificación (comandos)
- `..\PyPortable314\python.exe -m pytest -q -W error`
- `git -C D:\Proyectos\app_revisar_checadas status --short` igual a la base (` M config.json`, `?? APP_REVISAR_CHECADAS_TE_AEI_260720.xlsx`).

## Entrega
- Estrategia `ask-on-risk`; cadena ya elegida para el proyecto: **PR apilados hacia `main`** (`stacked-to-main`).
- Pronóstico: ~3 500–4 500 líneas de autoría (mitad pruebas) → muy por encima de ~400 por PR. Corte propuesto: un PR por tarea (E1-1…E1-7), apilados sobre `feat/e0-ventana` (PR #6).
- Rama E1-1: `feat/e1-tiempo-normatividad`.
- Commits Conventional, al menos uno por tarea; pruebas junto con el comportamiento.

## Progreso
- 2026-11-26: E0 aprobado visualmente por el propietario. TDD activado por el propietario. Documento creado; rama `feat/e1-tiempo-normatividad` desde `feat/e0-ventana`.

- 2026-11-26: T1 `acbafd5` (delegado, TDD con RED/GREEN observado por grupo). `pytest -q -W error`: 143 passed, 2 skipped (repetido por el orquestador). ~978 líneas (492 de `Dominio/`). Riesgo: alto (evaluación no evaluable por archivo sin seguimiento → alto) → verificador independiente: PASS-WITH-FINDINGS, sin bloqueos; valores sembrados conformes al doc 00. Hallazgos para una corrección acotada: edades 15/16/18 fijas en `regimenes.py` (deben venir de la semilla), convención de >86400 s para el límite de 22:00 sin documentar/probar, `clasificar_jornada` sin validar negativos, tope 8 h de `menor_16_18` como supuesto no documentado. Huecos legales anotados (sin inventar): art. 68 y total 12 h sin valor previo a 01/05/2026 → `FaltaParametro` (los consumidores T4/T5 deben producir `provisional` + AL12); art. 61 previo a la reforma asumido igual; parcial sin tope legal propio; código de alerta para prohibiciones de menores → pregunta al propietario. V1: aparece ` M empresas.json` con fecha anterior a la tarea (no lo tocó E1).

- 2026-11-26: propietario elige **AL13 «Prohibición para menores»** (crítico); agregado al plan §4.4 y rango AL01–AL13 en doc 03. Corrección acotada `b547350` (TDD, RED 19 fallos → GREEN): AL13 para toda prohibición de menores, edades 15/16/18 en la semilla vía `resolver_vigente`, convención >86400 s documentada y probada (rechazo fuera de 0..172800), `clasificar_jornada` rechaza negativos y 0/0, campo `supuesto` en `menor_16_18`. `pytest -q -W error`: 155 passed, 2 skipped (repetido por el orquestador). ~1 086 líneas. PR E1-1.

## Siguiente paso
T2 — checadas y emparejamiento (delegado, TDD), rama `feat/e1-checadas` apilada sobre E1-1.
