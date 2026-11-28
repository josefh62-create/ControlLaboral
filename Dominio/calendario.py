# -*- coding: utf-8 -*-
"""Calendario: semana laboral, jornada logica, art. 74 y clasificacion de dia.

Plan 4.5 RE01/RE02, 4.2 HO05, 5.1 pasos 5-6; doc. 03 8.2 pasos 4 y 8 (parte de calendario).

- RE01: la semana laboral tiene un dia de inicio configurable (politica patronal) y NO se
  reinicia por mes, anio ni corte de nomina (P-46, parte pura): es aritmetica de fechas.
- Jornada logica: un turno pertenece al dia en que EMPIEZA (turnos nocturnos); para vigencias
  y festivos se separa por fecha real a la medianoche local, sin duplicar segundos (P-26).
- RE02: el calendario de descansos obligatorios es obligatorio por anio. Sin calendario
  confirmado el resultado es provisional con AL12; nunca una excepcion que pierda datos.
  `sugerir_descansos_obligatorios` solo SUGIERE (art. 74 LFT); RH confirma.
- P-29: trabajar en domingo o descanso solo etiqueta; jamas se asume tiempo extra.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta, tzinfo

from Dominio import normatividad as n
from Dominio.checadas import clave_orden
from Dominio.modelos import ORIGEN_PATRONAL, Vigencia
from Dominio.normatividad import resolver_vigente
from Dominio.tiempo import Intervalo, fecha_local, instante_local

AL12 = "AL12"

# Etiquetas de dia (HO05, P-29).
PROGRAMADO = "programado"
DESCANSO_SEMANAL = "descanso_semanal"
NO_PROGRAMADO = "no_programado"
DOMINGO = "domingo"
DESCANSO_OBLIGATORIO = "descanso_obligatorio"
DIA_EMPRESA = "dia_empresa"
TRABAJADO = "trabajado"

PENDIENTES_MANUALES_ART74 = (
    "LFT art. 74 IX: jornada electoral de elecciones ordinarias; la fecha la fijan las leyes "
    "electorales federales y locales y no se puede calcular: RH la captura a mano.",
)


# ---------------------------------------------------------------------------
# Semana laboral (RE01)
# ---------------------------------------------------------------------------

def _dia_valido(dia) -> int:
    if isinstance(dia, bool) or not isinstance(dia, int) or not 0 <= dia <= 6:
        raise ValueError(f"dia de inicio de semana invalido (0=lunes ... 6=domingo): {dia!r}")
    return dia


def semana_laboral(fecha: date, dia_inicio: int) -> Vigencia:
    """Semana laboral [desde, hasta) que contiene `fecha` (0 = lunes ... 6 = domingo).

    Solo aritmetica de fechas: no hay reinicio por mes, anio ni periodo de pago (RE01).
    """
    atras = (fecha.weekday() - _dia_valido(dia_inicio)) % 7
    desde = fecha - timedelta(days=atras)
    return Vigencia(desde, desde + timedelta(days=7))


def dia_inicio_semana(versiones, fecha: date, empresa: str | None = None) -> int:
    """Dia de inicio de la semana laboral segun la politica patronal vigente (RE01)."""
    return _dia_valido(resolver_vigente(versiones, n.SEMANA_INICIO_DIA, fecha, ORIGEN_PATRONAL, empresa).valor)


# ---------------------------------------------------------------------------
# Calendario anual y art. 74 (RE02)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DescansoSugerido:
    fecha: date
    fundamento: str
    confirmado: bool = False


def _lunes(anio: int, mes: int, ordinal: int) -> date:
    """El `ordinal`-esimo lunes del mes."""
    primero = date(anio, mes, 1)
    return primero + timedelta(days=(0 - primero.weekday()) % 7 + 7 * (ordinal - 1))


# (clave de la semilla legal, texto de la fraccion, es_lunes): las fechas salen de la semilla
# legal versionada (art. 74 LFT), no del codigo.
_ART74 = (
    (n.ART74_I_ENERO, "I (1 de enero)", False),
    (n.ART74_II_FEBRERO, "II (primer lunes de febrero)", True),
    (n.ART74_III_MARZO, "III (tercer lunes de marzo)", True),
    (n.ART74_IV_MAYO, "IV (1 de mayo)", False),
    (n.ART74_V_SEPTIEMBRE, "V (16 de septiembre)", False),
    (n.ART74_VI_NOVIEMBRE, "VI (tercer lunes de noviembre)", True),
    (n.ART74_VIII_DICIEMBRE, "VIII (25 de diciembre)", False),
)


def sugerir_descansos_obligatorios(
    anio: int,
    versiones=n.SEMILLA_LEGAL,
    *,
    anio_base_transmision: int | None = None,
    periodo_anios: int | None = None,
) -> tuple[DescansoSugerido, ...]:
    """Descansos obligatorios del art. 74 LFT calculables para `anio`, como SUGERENCIA.

    Reglas y fechas vienen de `versiones` (semilla legal, `resolver_vigente`); si falta alguna
    se propaga `FaltaParametro`. Los argumentos con nombre sustituyen la regla de transmision
    del Ejecutivo (fraccion VII). RH revisa, agrega los dias propios de la empresa y confirma
    (RE02); hasta entonces el calendario no es valido. No incluye la jornada electoral
    (fraccion IX): ver `PENDIENTES_MANUALES_ART74`.
    """
    referencia = date(anio, 1, 1)
    base = "LFT art. 74"

    def valor(clave):
        return resolver_vigente(versiones, clave, referencia).valor

    dias = []
    for clave, texto, es_lunes in _ART74:
        v = valor(clave)
        mes, resto = divmod(v, 100)
        dias.append((_lunes(anio, mes, resto) if es_lunes else date(anio, mes, resto), f"{base} {texto}"))
    base_transmision = anio_base_transmision if anio_base_transmision is not None else valor(n.ART74_ANIO_BASE_TRANSMISION)
    periodo = periodo_anios if periodo_anios is not None else valor(n.ART74_PERIODO_TRANSMISION_ANIOS)
    if (anio - base_transmision) % periodo == 0:
        mes, dia = divmod(valor(n.ART74_VII_OCTUBRE), 100)
        dias.append((date(anio, mes, dia), f"{base} VII (1 de octubre, transmision del Ejecutivo Federal)"))
    return tuple(DescansoSugerido(f, fund) for f, fund in sorted(dias))


@dataclass(frozen=True)
class CalendarioAnual:
    """Calendario de un anio. Sin `confirmado` no es valido (RE02) y las semanas son provisionales."""

    anio: int
    descansos_obligatorios: frozenset[date]
    dias_empresa: frozenset[date] = field(default_factory=frozenset)
    confirmado: bool = False

    def __post_init__(self):
        if any(f.year != self.anio for f in (*self.descansos_obligatorios, *self.dias_empresa)):
            raise ValueError(f"hay fechas fuera del anio {self.anio}")


class CalendarioAmbiguo(ValueError):
    """Mas de un calendario para el mismo anio (error de configuracion)."""


def calendario_del_anio(calendarios, anio: int) -> CalendarioAnual | None:
    """Calendario del anio, o None si falta (el llamador marca provisional + AL12).

    Dos calendarios del mismo anio levantan `CalendarioAmbiguo`; quien calcula lo captura y
    degrada a provisional (`calendario_ambiguo`) en vez de abortar.
    """
    del_anio = [c for c in calendarios if c.anio == anio]
    if len(del_anio) > 1:
        raise CalendarioAmbiguo(f"hay {len(del_anio)} calendarios para {anio}")
    return del_anio[0] if del_anio else None


def calendario_siguiente_pendiente(fecha_referencia: date, calendarios) -> bool:
    """RE02: desde el 1 de diciembre se alerta si falta el calendario CONFIRMADO del anio siguiente."""
    if fecha_referencia.month != 12:
        return False
    try:
        siguiente = calendario_del_anio(calendarios, fecha_referencia.year + 1)
    except CalendarioAmbiguo:
        return True  # configuracion ambigua: no hay un calendario confirmado utilizable
    return siguiente is None or not siguiente.confirmado


@dataclass(frozen=True)
class ClasificacionDia:
    """Etiquetas de un dia. No contiene tiempo extra: trabajar en domingo o descanso no lo implica (P-29)."""

    fecha: date
    base: str  # programado | descanso_semanal | no_programado (HO05)
    etiquetas: frozenset[str]
    ausencia: bool
    provisional: bool = False
    alertas: tuple[str, ...] = ()
    motivos: tuple[str, ...] = ()


def clasificar_dia(
    fecha: date,
    calendarios,
    *,
    programado: bool,
    descanso_semanal: bool,
    trabajado_s: int,
    justificacion: str | None = None,
) -> ClasificacionDia:
    """HO05/P-29: diferencia descanso semanal, dia no programado, descanso obligatorio y ausencia.

    `justificacion` (permiso, vacaciones, incapacidad...) no es tiempo trabajado (RE06); solo
    evita contar la ausencia. Un descanso obligatorio no programado nunca es falta.
    """
    if trabajado_s < 0:
        raise ValueError("trabajado_s no puede ser negativo")
    ambiguo = False
    try:
        cal = calendario_del_anio(calendarios, fecha.year)
    except CalendarioAmbiguo:
        cal, ambiguo = None, True
    obligatorio = cal is not None and fecha in cal.descansos_obligatorios
    de_empresa = cal is not None and fecha in cal.dias_empresa
    base = PROGRAMADO if programado else DESCANSO_SEMANAL if descanso_semanal else NO_PROGRAMADO
    trabajo = trabajado_s > 0
    etiquetas = {base}
    for activa, etiqueta in (
        (fecha.weekday() == 6, DOMINGO),
        (obligatorio, DESCANSO_OBLIGATORIO),
        (de_empresa, DIA_EMPRESA),
    ):
        if activa:
            etiquetas.add(etiqueta)
            if trabajo:
                etiquetas.add(f"{etiqueta}_trabajado")
    if base == DESCANSO_SEMANAL and trabajo:
        etiquetas.add("descanso_semanal_trabajado")
    if trabajo:
        etiquetas.add(TRABAJADO)
    if justificacion:
        etiquetas.add(f"justificado:{justificacion}")
    motivos = ()
    if ambiguo:
        motivos = ("calendario_ambiguo",)
    elif cal is None:
        motivos = ("calendario_faltante",)
    elif not cal.confirmado:
        motivos = ("calendario_sin_confirmar",)
    ausencia = programado and not trabajo and not justificacion and not obligatorio and not de_empresa
    return ClasificacionDia(
        fecha, base, frozenset(etiquetas), ausencia, bool(motivos), (AL12,) if motivos else (), motivos
    )


# ---------------------------------------------------------------------------
# Jornada logica y fecha real (plan 5.1-5, P-26)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ParteFecha:
    fecha_real: date
    intervalo: Intervalo


@dataclass(frozen=True)
class IntervaloAsignado:
    emparejado: object  # IntervaloEmparejado
    dia_logico: date
    partes: tuple[ParteFecha, ...]


def dividir_por_fecha_real(intervalo: Intervalo, zona: tzinfo) -> tuple[ParteFecha, ...]:
    """Divide en cada medianoche local para vigencias y festivos; ningun segundo se duplica."""
    fecha = fecha_local(intervalo.inicio, zona)
    partes, inicio = [], intervalo.inicio
    while True:
        corte = instante_local(fecha + timedelta(days=1), 0, zona)
        if corte >= intervalo.fin:
            partes.append(ParteFecha(fecha, Intervalo(inicio, intervalo.fin)))
            return tuple(partes)
        partes.append(ParteFecha(fecha, Intervalo(inicio, corte)))
        inicio, fecha = corte, fecha + timedelta(days=1)


def asignar_dia_logico(intervalo: Intervalo, zona: tzinfo, fin_de_jornada_previa=None) -> date:
    """Dia logico: el de inicio del turno.

    `fin_de_jornada_previa(fecha)` entrega el instante en que termina el turno programado de
    `fecha` cuando cruza la medianoche (o None). Si el intervalo empieza antes de ese instante,
    continua el turno del dia anterior (p. ej. regreso de la comida de un turno nocturno).
    """
    fecha = fecha_local(intervalo.inicio, zona)
    if fin_de_jornada_previa is not None:
        previo = fecha - timedelta(days=1)
        fin = fin_de_jornada_previa(previo)
        if fin is not None and intervalo.inicio < fin:
            return previo
    return fecha


def asignar_jornada_logica(emparejados, zona: tzinfo, fin_de_jornada_previa=None) -> tuple[IntervaloAsignado, ...]:
    """Cada intervalo emparejado con su dia logico y sus partes por fecha real (orden determinista)."""
    ordenados = sorted(
        emparejados,
        key=lambda e: (e.intervalo.inicio, e.intervalo.fin, clave_orden(e.desde), clave_orden(e.hasta)),
    )
    return tuple(
        IntervaloAsignado(
            e,
            asignar_dia_logico(e.intervalo, zona, fin_de_jornada_previa),
            dividir_por_fecha_real(e.intervalo, zona),
        )
        for e in ordenados
    )
