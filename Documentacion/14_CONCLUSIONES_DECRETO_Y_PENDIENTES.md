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
   - Cada semana guarda qué criterio usó. Mientras no haya dictamen, se recomienda calcular y mostrar **ambos** resultados.
4. Siempre: tope diario 12 h, 4 h/día y 4 días/semana de extra art. 66, excedente art. 68 y descanso semanal, como alertas independientes que nunca borran tiempo.

## 5. Preguntas para mañana

1. ¿Qué esquemas de jornada usan hoy o quieren usar (5 × 8 + sábado, 6 × 7:40, 4 × 12, turnos nocturnos)? ¿Cuáles tienen acuerdo firmado?
2. ¿Aceptan que el criterio de inicio de extra sea configurable y que el asesor laboral elija la lectura (A) o (B) y el criterio de Q05?
3. ¿Mostramos ambos cálculos en paralelo mientras llega el dictamen?
4. Siguientes preguntas de la auditoría: Q06 (sábado y domingo fijos en 8 h), Q07 a Q15 (ver `01_AUDITORIA_SISTEMA_ACTUAL.md` §9).
