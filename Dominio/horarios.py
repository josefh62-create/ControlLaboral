# -*- coding: utf-8 -*-
"""Horarios acordados (plan 4.2, HO01-HO07) y contexto del dia (doc. 03 8.2 paso 5).

Modelo:
- `DiaHorario`: intervalos del dia en segundos desde las 00:00 del dia de INICIO del turno
  (un turno nocturno 22:00-05:00 es 22 h a 29 h; maximo 48 h) y sus descansos.
- Un descanso debe quedar DENTRO de un intervalo del horario (comida con el trabajador
  presente). Un hueco entre intervalos (turno partido) no es descanso y no cuenta.
- Descanso computable (art. 63, art. 64: el trabajador no puede salir) suma; no computable resta.

Principios: HO02 minutos ordinarios = intervalos - descansos no computables; HO03 un horario
incompatible se ADVIERTE, nunca se aprueba en silencio ni se recorta; HO06 sin horario el
resultado es provisional (AL12) y NO se inventan 8 h ni 48 h (P-33).
"""

from dataclasses import dataclass
from datetime import date, tzinfo
from types import MappingProxyType
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from Dominio import normatividad as n
from Dominio.calendario import AL12, CalendarioAnual, calendario_del_anio
from Dominio.modelos import Vigencia
from Dominio.normatividad import FaltaParametro, resolver_vigente
from Dominio.regimenes import REGIMENES, Regimen, obtener_regimen, tope_diario_s
from Dominio.tiempo import Intervalo, instante_local
from Dominio.tolerancias import Tolerancias, resolver_tolerancias

HO03 = "HO03"  # alerta «horario incompatible con el tope legal» (plan 5.2)
AL09 = "AL09"  # horario futuro incompatible con la reforma (HO07)

MAX_SEGUNDOS_DIA_HORARIO = 2 * 86_400


class HorarioAmbiguo(ValueError):
    """Mas de un horario vigente para la fecha (HO04): error de configuracion."""


@dataclass(frozen=True)
class DescansoHorario:
    intervalo: Intervalo
    computable: bool
    fundamento: str | None = None  # p. ej. «art. 63» o «art. 64»


@dataclass(frozen=True)
class DiaHorario:
    intervalos: tuple[Intervalo, ...]
    descansos: tuple[DescansoHorario, ...] = ()

    def __post_init__(self):
        intervalos = tuple(sorted(self.intervalos, key=lambda i: (i.inicio, i.fin)))
        descansos = tuple(sorted(self.descansos, key=lambda d: (d.intervalo.inicio, d.intervalo.fin)))
        if not intervalos:
            raise ValueError("un dia de horario necesita al menos un intervalo")
        for i in intervalos:
            if i.duracion <= 0 or i.inicio < 0 or i.fin > MAX_SEGUNDOS_DIA_HORARIO:
                raise ValueError(f"intervalo de horario fuera de 0..48 h o vacio: {i}")
        for a, b in zip(intervalos, intervalos[1:]):
            if b.inicio < a.fin:
                raise ValueError("los intervalos del horario no pueden traslaparse")
        for d in descansos:
            if not any(i.inicio <= d.intervalo.inicio and d.intervalo.fin <= i.fin for i in intervalos):
                raise ValueError(f"el descanso debe quedar dentro de un intervalo del horario: {d.intervalo}")
        for a, b in zip(descansos, descansos[1:]):
            if b.intervalo.inicio < a.intervalo.fin:
                raise ValueError("los descansos no pueden traslaparse")
        object.__setattr__(self, "intervalos", intervalos)
        object.__setattr__(self, "descansos", descansos)

    @property
    def ordinarios_s(self) -> int:
        """HO02: intervalos menos SOLO los descansos no computables."""
        return sum(i.duracion for i in self.intervalos) - sum(
            d.intervalo.duracion for d in self.descansos if not d.computable
        )


@dataclass(frozen=True)
class Horario:
    """Horario acordado con vigencia (plan 4.2). `dias` va por dia de la semana (0 = lunes)."""

    codigo: str
    vigencia: Vigencia
    regimen: str
    zona: str
    dias: object  # Mapping[int, DiaHorario]; se congela en __post_init__
    descansos_semanales: frozenset[int] = frozenset()
    empresa: str | None = None
    referencia_acuerdo: str | None = None  # acuerdo art. 58 que respalda la distribucion
    tolerancias: Tolerancias | None = None  # TO02: las del horario prevalecen

    def __post_init__(self):
        dias = dict(self.dias)
        for d in (*dias, *self.descansos_semanales):
            if isinstance(d, bool) or not isinstance(d, int) or not 0 <= d <= 6:
                raise ValueError(f"dia de la semana invalido: {d!r}")
        if set(dias) & set(self.descansos_semanales):
            raise ValueError("un dia no puede ser programado y descanso semanal a la vez")
        if self.regimen not in REGIMENES:
            raise ValueError(f"regimen desconocido: {self.regimen!r}")
        try:
            ZoneInfo(self.zona)
        except (ZoneInfoNotFoundError, ValueError, TypeError) as error:
            raise ValueError(f"zona horaria desconocida: {self.zona!r}") from error
        object.__setattr__(self, "dias", MappingProxyType(dict(sorted(dias.items()))))

    @property
    def ordinarios_semana_s(self) -> int:
        return sum(d.ordinarios_s for d in self.dias.values())

    def programado(self, dia_semana: int) -> bool:
        return dia_semana in self.dias

    def es_descanso_semanal(self, dia_semana: int) -> bool:
        return dia_semana in self.descansos_semanales


def resolver_horario(horarios, fecha: date) -> Horario | None:
    """Horario vigente en la fecha trabajada, o None (HO06: el llamador marca provisional + AL12)."""
    vigentes = [h for h in horarios if h.vigencia.contiene(fecha)]
    if len(vigentes) > 1:
        raise HorarioAmbiguo(f"{len(vigentes)} horarios vigentes el {fecha}: {[h.codigo for h in vigentes]}")
    return vigentes[0] if vigentes else None


def instantes_del_dia(horario: Horario, fecha: date) -> tuple[tuple[Intervalo, ...], tuple[DescansoHorario, ...]]:
    """Intervalos programados y descansos del dia logico `fecha`, en segundos de epoch."""
    dia = horario.dias.get(fecha.weekday())
    if dia is None:
        return (), ()
    zona = ZoneInfo(horario.zona)

    def a_epoch(i: Intervalo) -> Intervalo:
        return Intervalo(instante_local(fecha, i.inicio, zona), instante_local(fecha, i.fin, zona))

    return (
        tuple(a_epoch(i) for i in dia.intervalos),
        tuple(DescansoHorario(a_epoch(d.intervalo), d.computable, d.fundamento) for d in dia.descansos),
    )


def fin_de_jornada_previa(horarios, zona: tzinfo):
    """Funcion para `asignar_dia_logico`: fin (epoch) del turno programado de `fecha` si cruza la medianoche."""

    def fin(fecha: date) -> int | None:
        horario = resolver_horario(horarios, fecha)
        dia = horario.dias.get(fecha.weekday()) if horario else None
        if dia is None:
            return None
        ultimo = max(i.fin for i in dia.intervalos)
        return instante_local(fecha, ultimo, zona) if ultimo > 86_400 else None

    return fin


# ---------------------------------------------------------------------------
# HO03 / HO07: compatibilidad con los topes aplicables
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Compatibilidad:
    fecha: date
    semanal_s: int
    tope_semanal_s: int | None
    dias_sin_acuerdo: tuple[int, ...] = ()  # dia sobre el tope diario del regimen, sin acuerdo art. 58
    dias_sobre_total_diario: tuple[int, ...] = ()  # dia sobre 12 h (art. 68): no es ordinario
    advertencias: tuple[str, ...] = ()
    alertas: tuple[str, ...] = ()
    provisional: bool = False
    faltantes: tuple[str, ...] = ()

    @property
    def compatible(self) -> bool:
        return not self.advertencias and not self.provisional


def _valor_o_falta(faltantes: list, funcion):
    try:
        return funcion()
    except FaltaParametro as falta:
        faltantes.append(falta.clave)
        return None


def evaluar_compatibilidad(horario: Horario, versiones, fecha: date, *, fecha_referencia: date | None = None) -> Compatibilidad:
    """HO03: compara el horario con el tope semanal y el diario del regimen vigentes en `fecha`.

    Nunca recorta ni normaliza: advierte. Si `fecha_referencia` es de un anio anterior a `fecha`
    es una revision de horario futuro (HO07) y la alerta es AL09; en otro caso, HO03. Falta de
    norma vigente -> provisional con AL12.
    """
    faltantes: list[str] = []
    regimen = obtener_regimen(horario.regimen)
    tope_semanal = _valor_o_falta(faltantes, lambda: resolver_vigente(versiones, n.ORDINARIA_SEMANAL_S, fecha).valor)
    tope_diario = _valor_o_falta(faltantes, lambda: tope_diario_s(regimen, versiones, fecha))
    total_diario = _valor_o_falta(faltantes, lambda: resolver_vigente(versiones, n.TOTAL_DIARIO_MAX_S, fecha).valor)
    semanal = horario.ordinarios_semana_s
    advertencias = []
    if tope_semanal is not None and semanal > tope_semanal:
        advertencias.append("semanal_excede_tope")
    sin_acuerdo = tuple(
        d for d, dia in horario.dias.items()
        if tope_diario is not None and dia.ordinarios_s > tope_diario and not horario.referencia_acuerdo
    )
    sobre_total = tuple(
        d for d, dia in horario.dias.items() if total_diario is not None and dia.ordinarios_s > total_diario
    )
    if sin_acuerdo:
        advertencias.append("diario_excede_tope_sin_acuerdo")
    if sobre_total:
        advertencias.append("diario_excede_total_12h")
    alertas = []
    if advertencias:
        futuro = fecha_referencia is not None and fecha.year > fecha_referencia.year
        alertas.append(AL09 if futuro else HO03)
    if faltantes:
        alertas.append(AL12)
    return Compatibilidad(
        fecha, semanal, tope_semanal, sin_acuerdo, sobre_total, tuple(advertencias), tuple(alertas),
        bool(faltantes), tuple(sorted(set(faltantes))),
    )


# ---------------------------------------------------------------------------
# Contexto del dia (paso 5): horario, norma, politica y calendario por fecha trabajada
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ContextoDia:
    fecha: date
    horario: Horario | None
    dia_horario: DiaHorario | None
    regimen: Regimen | None
    tolerancias: Tolerancias | None
    calendario: CalendarioAnual | None
    tope_semanal_s: int | None
    tope_diario_s: int | None
    provisional: bool
    alertas: tuple[str, ...]
    motivos: tuple[str, ...]


def resolver_contexto(fecha: date, horarios, calendarios, versiones, empresa: str | None = None) -> ContextoDia:
    """Todo lo vigente en la fecha trabajada; lo que falta se marca (provisional + AL12), no se lanza.

    `versiones` mezcla norma legal y politica patronal (`resolver_vigente` distingue el origen).
    La empresa del horario, si la tiene, prevalece sobre `empresa` para las tolerancias.
    """
    motivos: list[str] = []
    horario = resolver_horario(horarios, fecha)
    if horario is None:
        motivos.append("horario_faltante")
    regimen = obtener_regimen(horario.regimen) if horario else None
    dia = horario.dias.get(fecha.weekday()) if horario else None

    def calcular(funcion):
        try:
            return funcion()
        except FaltaParametro as falta:
            motivos.append(f"falta:{falta.clave}")
            return None

    semanal = calcular(lambda: resolver_vigente(versiones, n.ORDINARIA_SEMANAL_S, fecha).valor)
    diario = calcular(lambda: tope_diario_s(regimen, versiones, fecha)) if regimen else None
    emp = horario.empresa if horario and horario.empresa else empresa
    tolerancias = calcular(
        lambda: resolver_tolerancias(versiones, fecha, emp, horario.tolerancias if horario else None)
    )
    calendario = calendario_del_anio(calendarios, fecha.year)
    if calendario is None:
        motivos.append("calendario_faltante")
    elif not calendario.confirmado:
        motivos.append("calendario_sin_confirmar")
    return ContextoDia(
        fecha, horario, dia, regimen, tolerancias, calendario, semanal, diario,
        bool(motivos), (AL12,) if motivos else (), tuple(motivos),
    )
