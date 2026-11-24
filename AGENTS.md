# AGENTS.md — ControlLaboral V2.0

## Autoridad y alcance
- Proyecto editable: `D:\Proyectos\ControlLaboral`.
- Proyecto de referencia exclusivamente de lectura: `D:\Proyectos\app_revisar_checadas`.
- Leer íntegramente `ControlLaboral_Plan_Maestro_v3.0.md` antes de diseñar o implementar. Si hay contradicciones, documentarlas y solicitar resolución; no inventar requisitos.
- Responder y documentar en español. No elegir lenguaje, framework ni dependencias definitivas antes de la auditoría y aprobación del responsable.

## Protección de la aplicación existente
- Prohibido modificar, crear, borrar, renombrar o mover archivos, configuraciones, bases de datos y repositorios de la aplicación original. No ejecutar compilaciones, restauraciones, instalaciones, migraciones, pruebas ni comandos que puedan escribir allí o afectar producción.
- No conectar con relojes físicos, bases de producción ni servicios remotos durante la auditoría sin autorización específica. No extraer secretos ni datos personales innecesarios.
- Antes de cada funcionalidad, inspeccionar la implementación equivalente anterior, incluidos algoritmos, interfaces, reportes, validaciones y casos especiales. Priorizar reutilizar, adaptar o refactorizar código compatible en V2; justificar cualquier reemplazo u omisión.
- Mantener `Documentacion/13_MATRIZ_DE_REUTILIZACION.md` con módulo, ruta y símbolo original, comportamiento, decisión, justificación, destino, pruebas y estado. No tratar la auditoría como actividad única.

## Primera fase: auditoría sin implementación
- Inventariar estructura, tecnologías, dependencias, entrada de checadas, Excel, datos, horarios, tolerancias, cálculo diario/semanal, interfaz, reportes, seguridad y pruebas existentes.
- Identificar constantes laborales, supuestos, acoplamientos, reglas implícitas, riesgos y brechas frente al plan maestro. Citar rutas y símbolos concretos; distinguir hechos comprobados de hipótesis.
- Elaborar diagnóstico, matriz de reutilización inicial, propuesta de arquitectura, estrategia de migración, pruebas comparativas y plan por fases. No escribir código de aplicación ni elegir tecnologías irreversiblemente. Esperar aprobación explícita antes de implementar.

## Reglas funcionales no negociables
- SQLite local como fuente administrativa inicial; catálogo CRUD de empleados con bajas lógicas e historial, migración validada desde Excel, sin dependencia operativa posterior.
- Horarios y asignaciones por vigencia; límites legales versionados; tolerancias de 0 a 15 minutos por política interna, sin borrar tiempo efectivamente trabajado. Clasificar horas ordinarias y extraordinarias por jornada y semana, sin duplicación ni compensación indebida. Alertas diarias y semanales. Verificar LFT y disposiciones STPS vigentes antes de codificar reglas definitivas; no asumir formatos oficiales pendientes.
- Checadas originales de cualquier origen inalterables. Incidencias y movimientos complementarios separados, incluyendo jornadas completas por contingencia. Registrar evidencia, responsables, estados y efectos sobre resultados.
- Una sola acta lógica por empleado y semana de pago con incidencias; ninguna si no existen. Firmas del empleado y jefe de personal; conservar PDF emitido y firmado, rectificaciones versionadas, reimpresión exacta y trazabilidad. No negar reconocimiento de trabajo efectivo por ausencia de firma.
- Consultas y reportes históricos por periodo, empleado, empresa, centro, departamento, tipo, estado, fechas laborales y de captura, responsables y folio. Mostrar antes/después y diferencias. Exportaciones y respaldo consistente de datos y documentos. No incluir procesamiento de nómina.

## Arquitectura por fases
- Desktop: administración y cálculo local SQLite. Lógica de negocio independiente del almacenamiento; migraciones versionadas, transacciones, integridad referencial, pruebas de respaldo y restauración.
- Supabase: publicación unidireccional de datos autorizados desde Desktop, incremental, idempotente, auditable y consistente. Portal Web inicialmente solo lectura de datos laborales, con autenticación y RLS, Storage privado y permisos por alcance. No exponer claves privilegiadas ni datos personales innecesarios.
- Móvil (fase futura): dispositivos personales y compartidos; identificación facial, huella o código según viabilidad y evaluación de privacidad. Registrar ubicación al checar, precisión, hora original, zona horaria, dispositivo y origen. Guardar primero en SQLite incluso con conexión; UUID estable, cola persistente, reintentos y confirmación del servidor antes de marcar sincronizada. No sustituir hora original por recepción ni perder registros por falta de GPS o Internet. Alertar inconsistencias, no inventar coordenadas. Recepción en Supabase e importación controlada a Desktop; no sincronización indiscriminada bidireccional. No desarrollar fase móvil antes de autorización.

## Calidad y gobierno
- Trabajar por etapas pequeñas, con plan, criterios de aceptación, pruebas automatizadas y comparaciones con V1 cuando corresponda. Usar datos sintéticos o anonimizados. No afirmar que una prueba pasó sin ejecutarla.
- Mantener documentación y matriz de reutilización actualizadas; informar cambios, archivos, pruebas, riesgos y pendientes al terminar cada tarea. Evitar cambios ajenos al alcance.
- Nunca incluir secretos, bases reales, actas firmadas o evidencias personales en Git. No publicar repositorios, desplegar, usar servicios de producción ni elevar privilegios sin autorización expresa.
- No sustituir V1 hasta completar operación paralela, explicar diferencias, probar restauración y obtener aprobación del responsable.
