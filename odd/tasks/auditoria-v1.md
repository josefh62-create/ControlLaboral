# Auditoría inicial de V1 (app_revisar_checadas)

## Objetivo
Producir el diagnóstico verificable de V1 y la matriz de reutilización inicial que exigen el plan maestro (caps. 0, 3, 19) y AGENTS.md, como base para la propuesta de arquitectura de ControlLaboral V2.

## Restricciones
- V1 (`D:\Proyectos\app_revisar_checadas`) es estrictamente de solo lectura: no modificar, compilar, instalar, ejecutar pruebas ni abrir sus BD en modo escritura.
- Ignorar `.claude/worktrees/` de V1 (copia de trabajo duplicada); auditar la rama principal (HEAD `bc7f5fd`).
- No extraer datos personales ni secretos; citar rutas y símbolos, no contenidos sensibles.
- Stack de V2 ya decidido (AGENTS.md «Estándar técnico»); la auditoría decide reutilizar/adaptar/reemplazar, no tecnología.
- Distinguir hechos comprobados de hipótesis.

## Tareas
- [x] T1 — Inventario y diagnóstico A01–A10 → `Documentacion/01_AUDITORIA_SISTEMA_ACTUAL.md` (ruta: delegado, disparador 4+ archivos)
- [x] T2 — Matriz de reutilización inicial → `Documentacion/13_MATRIZ_DE_REUTILIZACION.md` (ruta: delegado junto con T1)
- [x] T3 — Revisión del orquestador y presentación al usuario
- [ ] T3b — Respuestas del propietario a Q01–Q15 (bloquea decisiones de R001, R006–R008, R011–R014)
- [ ] T4 — Propuesta de arquitectura V2 (pendiente de aprobación del diagnóstico)

## Criterios de aceptación
- Cada hallazgo A01–A10 con ruta, símbolo, comportamiento observado, estado y riesgo.
- Matriz con una fila por componente relevante de V1 y decisión justificada.
- Ningún archivo de V1 modificado (`git status` de V1 sin cambios nuevos).

## Verificación
- `git -C D:\Proyectos\app_revisar_checadas status --short` igual antes y después.

## Progreso
- 2026-11-24: documento creado; T1+T2 delegados.
- 2026-11-24: T1+T2 entregados (01: 53 KB; 13: 29 KB, 47 componentes + 22 «desarrollar»). Verificado por orquestador: `git status` de V1 idéntico a la base (` M config.json`, `?? APP_REVISAR_CHECADAS_TE_AEI_260720.xlsx`); hallazgo de redondeo ±0.33 y `neto_semana` confirmados en `tiempo_extra/ClasesComunes/calculo_te.py:111-112,164-176`; sección C de la matriz consistente.
- 2026-11-24: respondidas Q01 (sin conexión al reloj; reportes por empresa → Genérico), Q02 (conservar archivo original byte a byte + hash), Q03 (solo entrada/salida; descanso según horario), Q04 (nuevo reglamento; tolerancias 0–15 configurables). Q05 en discusión: el propietario sostiene «completar 46 h antes de extras»; se leyó el decreto literal (`Documentacion/00_FUENTE_LEGAL_DECRETO_2026-05-01.md`) y se redactaron conclusiones (`Documentacion/14_CONCLUSIONES_DECRETO_Y_PENDIENTES.md`).
- 2026-11-24: Q05 (provisional), Q06, Q07 y Q08 parcial resueltas; commit 8a3dbf7; PR #1 fusionado en main sin las correcciones no bloqueantes.
- 2026-11-26: rama docs/correcciones-q05-q08: ejemplo de compensación corregido, regla de horario incompatible (remanente a los últimos minutos programados + HO03, decisión del propietario), fechas 25→24/11, docs 01 §9, 13 §D y 14 §4.3/§6 actualizados.
- 2026-11-26: Q08 resuelta: «Empresa base» = patrón IMSS del trabajador (AEI, primera empresa); patrón y centro de trabajo separados con vigencia (plan §13.1).
- 2026-11-26: varias empresas por trabajador: empleado único, emparejamiento sobre secuencia unificada de relojes, acumulación por trabajador+patrón+semana (plan §5.1-4, §5.3, §13.1).
- Siguiente: decidir tiempo de traslado entre centros; Q09–Q15; luego T4.
