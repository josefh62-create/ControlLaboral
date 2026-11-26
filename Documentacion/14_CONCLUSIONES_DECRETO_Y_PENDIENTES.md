# Conclusiones sobre el decreto y pendientes de discusión (24/11/2026)

Base: texto literal del decreto en `00_FUENTE_LEGAL_DECRETO_2026-05-01.md`. Interpretaciones marcadas; requieren validación del asesor laboral.

## 1. Lo que el decreto establece sin ambigüedad

- Tope semanal ordinario (art. 59 + transitorio 2.º): 48 h (2026), **46 h (2027)**, 44, 42, 40 h (2030 en adelante), desde el 1 de enero de cada año.
- Horas extra al doble (art. 66 + transitorio 4.º): 9 h/semana en 2026–2027, 10, 11, 12 h; **máximo 4 h por día y máximo 4 días por semana**.
- Excedente sobre el art. 66 (art. 68): hasta 4 h/semana más, pagadas al triple.
- **Tope diario absoluto (art. 68): ordinaria + extra ≤ 12 h.**
- Jornada diaria (art. 61, reformado pero con las mismas cifras): 8 h diurna, 7 h nocturna, 7.5 h mixta.
- Distribución (art. 58, nuevo 2.º párrafo): la jornada puede distribuirse **de común acuerdo** entre empresa y trabajador.
- Descanso: 1 día por cada 6 trabajados (art. 69). Prima dominical 25 % (art. 71).
- Registro electrónico de inicio y fin de jornada obligatorio (art. 132 XXXIV); las reglas de la STPS entran en vigor el 01/01/2027; multa de 250 a 5000 UMA (art. 994 IV Bis).
- Entrada en vigor del decreto: 01/05/2026. El plan maestro v3.0 coincide con todo lo anterior.

## 2. Sobre el ejemplo de 4 días × 12 h

- Semana de 48 h en 2027: **46 h ordinarias + 2 h extra** si se acepta la distribución por acuerdo del art. 58 (el tope semanal de 46 h manda). Esto coincide con lo que dicen «los que saben».
- **Interpretación (abierta):** el art. 58 permite distribuir, pero el art. 61 sigue diciendo 8 h diarias. El texto no aclara si con acuerdo se pueden tener 12 h *ordinarias* en un día. Hay dos lecturas:
  - (A) Con acuerdo art. 58, el horario pactado define lo ordinario del día; el límite real es 46 h/semana y 12 h/día.
  - (B) El art. 61 sigue fijando 8 h diarias ordinarias; lo que pase de 8 h en el día es extra aunque haya acuerdo.
- Consecuencias que no dependen de la lectura:
  - Un día de 12 h agota el tope del art. 68: **ese día no cabe ni un minuto de extra legal**; cualquier minuto adicional debe alertarse como exceso, sin borrarlo.
  - Bajo la lectura (B), 4 días × 12 h darían 16 h extra en la semana con 4 h/día; rebasa las 9 h del art. 66 en 2027 y entra en el tramo del art. 68 → la lectura (B) hace prácticamente inviable el esquema 4 × 12.

## 3. Sobre Q05 (¿completar 46 h antes de pagar extras?)

- El decreto **no dice** cuándo empieza el tiempo extraordinario (art. 66 solo dice «podrá prolongarse»). Ni la postura del propietario («completar 46 h») ni la del plan (P07: lo que excede el horario del día es extra) están escritas literalmente en la ley.
- Lo que sí aplica: con horario pactado por acuerdo (art. 58), lo ordinario es lo pactado, con el tope semanal. Quien trabaja su horario completo no genera extra hasta rebasarlo.
- El caso dudoso es el día **largo** que se compensa con un día **corto** (lunes 10 h, martes 6 h, horario de 8 h). Ahí se separan las dos posturas.

## 4. Propuesta de diseño para V2 (a discutir)

1. **Horarios por día sin forma fija:** cualquier distribución semanal (5 × 8 + 6, 6 × 7:40, 4 × 12, etc.) con vigencia y referencia al acuerdo art. 58 (ya previsto en HO01).
2. **Validación del horario (HO03):** si un día supera 8/7/7.5 h ordinarias, exigir que el horario tenga capturado el acuerdo art. 58; si supera 12 h, rechazar como ordinario. Si la suma semanal supera el tope del año, alertar (AL09).
3. **Criterio de inicio de extra como parámetro normativo versionado,** no código:
   - «Diario y semanal» (plan, P07): extra = lo que excede el horario del día o el tope semanal, lo que ocurra primero.
   - «Semanal con acuerdo» (postura del propietario): extra = lo que excede el tope/horario semanal; los días cortos se compensan con los largos dentro de la misma semana.
   - Cada semana guarda qué criterio usó.
   - *Actualización 24/11/2026:* el propietario eligió «semanal con acuerdo» (§5); ya no se calculan ni muestran ambos criterios en paralelo. El criterio sigue siendo un parámetro versionado por si el reglamento STPS o el asesor laboral lo cambian.
4. Siempre: tope diario 12 h, 4 h/día y 4 días/semana de extra art. 66, excedente art. 68 y descanso semanal, como alertas independientes que nunca borran tiempo.

## 5. Decisiones del 24/11/2026

- Se rehacen contratos y reglamento. Esquema previsto: 5 × 8 + 6 (46 h). El registro electrónico espera las disposiciones STPS (01/01/2027).
- Todos los topes 2027–2030 son configurables; la distribución del horario puede cambiar cada año (p. ej. 2028: 5 × 7 h 36 min + 6 h = 44 h). Cálculo en minutos. Plan §4.2 actualizado.
- **Q05 resuelta (provisional):** criterio «semanal con acuerdo». La semana determina cuánta extra hay (lo que excede el tope vigente); la extra se asigna a los excesos diarios más recientes para evaluar art. 66/68. Plan §5.2–5.3 actualizado. Se revisará si el reglamento STPS o el asesor laboral establecen otra regla.

- **Q06 resuelta:** sábado y domingo dejan de tener jornada fija de 8 h; los horarios se asignan por trabajador/grupo y por año (plan §4.2).
- **Q07 resuelta:** V2 calcula solo hacia adelante, desde el 01/01/2027 (tope 46 h y reglas STPS del registro electrónico). No reproduce resultados históricos de V1; el histórico de V1 se conserva para consulta. Riesgo: quedan ~5 semanas; V1 debe seguir disponible como respaldo durante la operación paralela (plan §20).
- **Q08 (parcial):** los usuarios administran los códigos; en un reloj compartido por varias empresas el código es único. V2 identifica por (reloj, código, vigencia) → empleado y bloquea solapamientos (plan §13.1). Si el reglamento STPS cambia la identificación (CURP/NSS), solo cambia esa relación.
- **Q08 resuelta (26/11/2026):** «Empresa base» es el patrón IMSS del trabajador (AEI fue la primera empresa del sistema). Un trabajador puede checar en una empresa y estar dado de alta con otra; V2 guarda patrón y centro de trabajo por separado, con vigencia (plan §13.1).
- **Horario incompatible con el tope (26/11/2026):** si la extra semanal supera la suma de excesos diarios (horario acordado por encima del tope), el remanente se asigna a los últimos minutos programados de la semana y se emite HO03. No se bloquea el cálculo (plan §5.2).
- **Varias empresas por trabajador (26/11/2026):** un trabajador puede checar en relojes de distintas empresas en la misma semana e incluso en la misma jornada (entrada en CATAB, salida en AEI). V2 usa un solo registro de empleado, empareja checadas sobre la secuencia unificada de todos los relojes y acumula por trabajador, patrón y semana contra un solo tope; cada segmento conserva su empresa y reloj de origen; los traslapes entre relojes generan alerta y no se cuentan doble (plan §5.1 paso 4, §5.3 y §13.1).
- **Traslado entre empresas (26/11/2026):** el hueco entre una salida en una empresa y la entrada en otra el mismo día cuenta como tiempo efectivo, etiquetado «traslado entre empresas»; si supera el máximo configurable (inicial 60 min) queda pendiente de revisión. Interpretación del art. 58 LFT (tiempo a disposición del patrón), cuyo primer párrafo no está transcrito en el documento 00: requiere validación del asesor laboral.
- **Q09 resuelta (26/11/2026):** hoy no existe calendario de festivos. En V2 es obligatorio uno por año: sin él, las semanas son provisionales (no se cierran ni exportan) y se alerta desde el 1 de diciembre previo. Se precargan como sugerencia los descansos del art. 74 LFT, que RH confirma; la lista debe verificarse contra la LFT vigente (plan RE02).

## 6. Preguntas pendientes

1. ¿Qué otros esquemas de jornada usarán además de 5 × 8 + 6 (turnos nocturnos, 4 × 12, etc.)? ¿Cuáles tendrán acuerdo art. 58 firmado? (Relacionada con Q14.)
2. Validar con el asesor laboral la lectura (A)/(B) y el criterio de Q05 cuando haya dictamen o reglamento STPS.
3. Siguientes preguntas de la auditoría: Q10 a Q15 (ver `01_AUDITORIA_SISTEMA_ACTUAL.md` §9).
