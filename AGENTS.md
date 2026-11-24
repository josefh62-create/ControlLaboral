# AGENTS.md — ControlLaboral V2.0

## Autoridad y alcance
- Proyecto editable: `D:\Proyectos\ControlLaboral`.
- Proyecto de referencia exclusivamente de lectura: `D:\Proyectos\app_revisar_checadas`.
- Leer íntegramente `ControlLaboral_Plan_Maestro_v3.0.md` antes de diseñar o implementar. Si hay contradicciones, documentarlas y solicitar resolución; no inventar requisitos.
- Responder y documentar en español. El lenguaje, framework, arquitectura y estándar de UI ya están decididos (ver «Estándar técnico»); las dependencias adicionales (PDF, Excel, etc.) se eligen tras la auditoría y con aprobación del responsable.

## Estándar técnico (decisión del propietario, 24/11/2026)
Esta decisión prevalece sobre cualquier redacción del plan maestro que indique no elegir tecnología antes de la auditoría. Fuentes obligatorias: `D:\Proyectos\CLAUDE.md` (reglas del SSD) y `VS_SIVEMA_MVC_PY/ARQUITECTURA_APPS_PYTHON.md` (documento maestro de arquitectura). Leerlas antes de cualquier cambio de arquitectura, nomenclatura o diseño.
- **Runtime:** Python 3.14.7 portátil `PyPortable314`, referenciado siempre de forma relativa (`run.bat`, `compilar_ui.bat`, `.vscode/settings.json`). Sin `venv`. Verificar en PyPI el soporte 3.14 de cada dependencia antes de agregarla.
- **Framework:** PySide6 para Desktop; SQLite como base administrativa local.
- **Patrón MVC estricto** con la nomenclatura del SSD: `Vistas/frm_<modulo>.ui`, `Vistas/frm_<modulo>.py` (generado, nunca editar), `Vistas/vista_<modulo>.py` (`Vista<Modulo>`), `Modelos/modelo_<modulo>.py` (`Modelo<Modulo>`, hereda `ModeloBase`), `Controladores/controlador_<modulo>.py` (`Controlador<Modulo>`), más `Servicios/` y repositorios según el documento maestro §3.
- **Motor de cálculo de jornada:** capa de servicio/dominio en Python puro, sin importar PySide6 ni SQLite, con datos de entrada explícitos (horario, norma, tolerancias, checadas) para que sea determinista y se pueda probar con datos sintéticos (plan maestro caps. 19 y 22).
- **UI:**
  - Toda la interfaz se diseña en archivos `.ui` con Qt Designer; nunca construir formularios por código. Recompilar después de cada edición.
  - Compilar con `compilar_ui.bat` usando los binarios reales `PyPortable314\Lib\site-packages\PySide6\uic.exe` y `rcc.exe` con `-g python`; nunca los wrappers `pyside6-uic.exe`/`pyside6-rcc.exe` (Windows App Control los bloquea). Recursos en `Recursos/Imagenes/<app>.qrc` → `<app>_rc.py`.
  - Soporte obligatorio de modo claro y oscuro.
  - Secciones y grupos de controles dentro de `QFrame` o `QGroupBox`, cada uno con su propio layout; no amontonar todo en un layout raíz.
  - Prefijos de widgets (`qbtn/qlbl/qtxt/qcmb/qspn/qdte/chk/qtbl/grp/…`), colores, zonas y control activo/inactivo conforme al documento maestro §5–§7.
- **Distribución:** paquete con `D:\Proyectos\_instaladores\empaquetar.ps1` e `instalador.json`; la BD de producción nunca se sobrescribe y los cambios de esquema van por migraciones idempotentes al arrancar.

## Protección de la aplicación existente
- Prohibido modificar, crear, borrar, renombrar o mover archivos, configuraciones, bases de datos y repositorios de la aplicación original. No ejecutar compilaciones, restauraciones, instalaciones, migraciones, pruebas ni comandos que puedan escribir allí o afectar producción.
- No conectar con relojes físicos, bases de producción ni servicios remotos durante la auditoría sin autorización específica. No extraer secretos ni datos personales innecesarios.
- Antes de cada funcionalidad, inspeccionar la implementación equivalente anterior, incluidos algoritmos, interfaces, reportes, validaciones y casos especiales. Priorizar reutilizar, adaptar o refactorizar código compatible en V2; justificar cualquier reemplazo u omisión.
- Mantener `Documentacion/13_MATRIZ_DE_REUTILIZACION.md` con módulo, ruta y símbolo original, comportamiento, decisión, justificación, destino, pruebas y estado. No tratar la auditoría como actividad única.

## Primera fase: auditoría sin implementación
- Inventariar estructura, tecnologías, dependencias, entrada de checadas, Excel, datos, horarios, tolerancias, cálculo diario/semanal, interfaz, reportes, seguridad y pruebas existentes.
- Identificar constantes laborales, supuestos, acoplamientos, reglas implícitas, riesgos y brechas frente al plan maestro. Citar rutas y símbolos concretos; distinguir hechos comprobados de hipótesis.
- Elaborar diagnóstico, matriz de reutilización inicial, propuesta de arquitectura, estrategia de migración, pruebas comparativas y plan por fases. La propuesta de arquitectura se diseña sobre el «Estándar técnico» ya aprobado; la auditoría decide qué se reutiliza, adapta o reemplaza de V1, no el lenguaje ni el framework. No escribir código de aplicación. Esperar aprobación explícita antes de implementar.

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
