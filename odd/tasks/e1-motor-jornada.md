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
- [x] T2 — Checadas y emparejamiento: `checadas.py` (orden por instante, marcas duplicado/futura/desfase sin descartar), `emparejamiento.py` (secuencia unificada multi-reloj, impar/ambigua/traslape, traslado entre empresas con tope versionado). Casos: P-30, P-31 (parte pura), P-32, P-45.
- [x] T3 — Calendario, horarios y tolerancias: `calendario.py` (semana laboral, jornada lógica por día de inicio, festivo/descanso/domingo, calendario faltante → provisional), `horarios.py` (minutos ordinarios HO02, compatibilidad HO03/HO06, descansos computables/no computables, complementos aprobados), `tolerancias.py` (TO01–TO07). Casos: P-18–P-25, P-29, P-33, P-41.
- [x] T4 — Segmentación y clasificación base: `segmentacion.py` (fronteras horario/descanso/medianoche/semana/vigencia), clasificación dentro de horario / exceso diario, diurna/nocturna/mixta, etiquetas domingo/festivo/descanso trabajado. Casos: P-26, P-27, P-29.
- [x] T5 — Extra semanal y tramos: `criterios_extra.py` (Protocol + registro; `semanal_con_acuerdo`, asignación a excesos más recientes, remanente + HO03), `tramos_extra.py` (doble hasta tope art. 66, resto triple; 4 h/día, 4 días/semana, 12 h/día; exceso legal; `extra_pendiente_clasificacion`). Casos: P-01–P-17, P-35, P-38, P-46, P-47 y ejemplos plan §5.2.
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

- 2026-11-26: T2 `9857ad3` + `da8acbd` (delegado, TDD con RED/GREEN observado). `pytest -q -W error`: 207 passed, 2 skipped (repetido por el orquestador). ~888 líneas. Riesgo alto → verificador independiente: PASS-WITH-FINDINGS con 2 importantes: (B1) salida faltante sin `sentido` desplaza el emparejamiento y cuenta intervalos de 24 h como normales → falta un máximo de duración de intervalo versionado (pregunta al propietario, propuesta 16 h); (B2) comida en el mismo reloj ≤30 min se marca duplicado y pierde el bloque de la tarde → duplicado solo si no rompe el emparejamiento/roles. Nit N1: hueco entre empresas que cruza medianoche no genera traslado ni incidencia (contra «nunca descartar en silencio»). Huecos anotados: desfase sin umbral documentado, futura solo con instante de referencia, empate de instantes arbitrario pero determinista.

- 2026-11-26: propietario fija **máximo de 16 h por intervalo, configurable por empresa**. Correcciones `3266882` (B1: `intervalo_max_s` patronal por empresa, incidencia `intervalo_excedido` no contada y reinicio de roles; `VersionParametro.empresa` con precedencia empresa > general, legales siempre globales; B2: duplicado sin `sentido` solo si conserva la paridad del día; N1: `traslado_pendiente_q_f`) y `9cbc62a` (hallado por el orquestador: 08:00/08:02/12:00/17:00 perdía ~4 h sin incidencia → marca `cercana_sin_resolver` + incidencia `ambigua`; una comida de ≤30 min en el mismo reloj también queda para revisión, sin pérdida). TDD RED→GREEN en cada una. `pytest -q -W error`: 233 passed, 2 skipped (repetido por el orquestador). PR E1-2.

- 2026-11-26: T3 `d74a132`, `95feb2b`, `fca0020`, `e2750c5` (delegado, TDD; RED de colección reforzado con mutaciones). `pytest -q -W error`: 339 passed, 2 skipped (repetido por el orquestador). ~1 956 líneas (≈1 000 código, ≈950 pruebas; supera la heurística por cohesión calendario-horarios-tolerancias). Verificador independiente: PASS-WITH-FINDINGS sin bloqueos: (I1) complemento no aprobado dentro de un descanso computable se cuenta dos veces; (I2) configuración inválida/ambigua (tolerancia >15, dos horarios vigentes, dos calendarios del año) lanza excepción y aborta el cálculo en lugar de provisional+AL12; nits: constantes del art. 74/transmisión en `calendario.py` (a la semilla), día de empresa sin trabajo cuenta como ausencia, `zona` inconsistente posible. Hueco #2: sin tolerancias configuradas lo fuera de horario se contaba confirmado → se cambiará a pendiente (TO06). Pendiente pregunta al propietario: día de inicio de la semana laboral (Q-A; sembrado lunes como supuesto).

- 2026-11-26: propietario confirma **semana laboral lunes–domingo en AEI y CATAB** (Q-A; configurable por empresa). Corrección acotada `11dfa2f` (TDD, RED 16 fallos → GREEN): I1 sin doble conteo (+ prueba de propiedades con 400 semillas), I2 configuración inválida/ambigua → provisional+AL12 conservando piezas, sin tolerancias → pendiente, art. 74 en la semilla legal, día de empresa no es ausencia, zona del propio horario. `pytest -q -W error`: 355 passed, 2 skipped (repetido por el orquestador). PR E1-3.

- 2026-11-27: T4 `23e2ab1` (delegado, TDD: RED de colección → GREEN 24; una mutación sobrevivió → prueba añadida, 25). `segmentar()` corta en medianoche local y en la banda nocturna versionada (semana y vigencia caen en medianoche); clase dentro_de_horario/exceso_diario/sin_clasificar, banda diurna/nocturna, etiquetas por día lógico + fecha real; parámetro faltante → provisional+AL12 sin excepción. Propiedades: 300 semillas (suma, sin traslape) + 100 (permutación). `pytest -q -W error`: 380 passed, 2 skipped (repetido por el orquestador). 608 líneas (≈245 código). Riesgo: medio (`gentle-ai review assess`) → autoverificación del writer + revisión puntual; RDD off. Preguntas al propietario: (Q-B) ¿la clasificación diurna/nocturna/mixta del art. 60 incluye el exceso? (hoy solo tiempo confirmado dentro de horario); (Q-C) ¿alerta si `regimen_declarado` difiere del calculado? Notas: banda en hora local (revisar si hubiera horario de verano); `segmentacion.py` importa privados de `horarios.py` (limpieza futura). PR E1-4.

- 2026-11-27: propietario decide **Q-B: el tipo de jornada se configura en el horario** (el exceso nunca lo cambia; el tope art. 61 sale del tipo declarado) y **Q-C: alerta AL14 «Tipo de jornada declarado no coincide con el art. 60»**, nivel Configuración, no bloquea (agregada al plan §4.4; rango AL01–AL14 en doc 03). Corrección acotada `6099dc4` (delegada, TDD: RED por símbolo `AL14` inexistente → GREEN): `JornadaClasificada.tipo_efectivo` = régimen declarado; sin régimen → provisional+AL12 (`falta:regimen_declarado`); `verificar_regimen_declarado()` pura en `horarios.py` (reutilizable al guardar el horario) clasifica las horas programadas sin descansos no computables; parcial/menores no se comparan; banda faltante → AL12, no AL14. `pytest -q -W error`: 387 passed, 2 skipped (repetido por el orquestador). 159/7 líneas. Riesgo: medio → autoverificación + revisión puntual. Notas: AL14 en `segmentar()` solo aparece en días con jornada (al guardar lo cubre la función); un horario que cruza medianoche usa la banda de `fecha`; el fixture P-27 (17:00–23:30 declarado mixta) ahora genera AL14 (por horas es nocturna) — revisar ese fixture al tocar T5. T5 debe leer el tope art. 61 de `tipo_efectivo`.

- 2026-11-27: PR #10 (E1-4) abierto, base `feat/e1-horarios`.

- 2026-11-27: T5 `fffa48c` (fixture P-27 declarado nocturna), `fa0d490` (`criterios_extra`: Protocol + registro, `semanal_con_acuerdo`, extra a excesos más recientes, remanente a últimos minutos programados + HO03), `1d4793a` (`tramos_extra`: doble hasta tope art. 66, triple el resto, `exceso_legal` art. 68 y 12 h/día, fuera de distribución 4 h/4 días → `extra_pendiente_clasificacion`, autorización solo etiqueta, AL02–AL07; tope art. 61 de `tipo_efectivo` solo informativo). Delegado, TDD (RED de colección + mutaciones: 50 mutantes, sobrevivientes equivalentes o fijados con pruebas). Propiedades 400+400+150+150 semillas. `pytest -q -W error`: 453 passed, 2 skipped (repetido por el orquestador). 1 633 líneas (~2/3 pruebas). Riesgo: medio → autoverificación + revisión puntual. Divergencias con la matriz cap. 9: P-06 (40 h contrato) y P-07 dan 0 extra con el criterio semanal. Preguntas al propietario: (Q-D) tope semanal = mín(legal, horas del horario) según plan §4.2 l.117 → P-06 = 2 extra; (Q-E) categoría neutra de pendiente para lo no-extra; (Q-F) semana de transición acotada (tope menor, diferencia ≤2 h pendiente + AL12); (Q-G) minutos fuera de distribución art. 66 → pendiente (validar con asesor); (Q-H) alerta por exceso del tope diario art. 61; (Q-I) sembrar 60 min de anticipación preventiva (AL03).

## Siguiente paso
Resolver Q-D…Q-I con el propietario (una a la vez), corrección acotada de T5; push y PR E1-5; luego T6.
