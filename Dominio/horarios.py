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

from dataclasses import dataclass, replace
from datetime import date, tzinfo
from types import MappingProxyType
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from Dominio import normatividad as n
from Dominio.calendario import (
    AL12,
    CalendarioAnual,
    asignar_dia_logico,
    calendario_del_anio,
    dividir_por_fecha_real,
)
from Dominio.checadas import clave_orden
from Dominio.emparejamiento import TRASLADO, tiempo_sin_traslape
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


# ---------------------------------------------------------------------------
# Paso 6: intervalos efectivos (plan 5.2)
# ---------------------------------------------------------------------------

# Origen de cada pieza.
CHECADA = "checada"
ORIGEN_TRASLADO = "traslado"
COMPLEMENTO = "complemento"
DESCANSO_COMPUTABLE = "descanso_computable"
# Estado: solo `confirmado` es tiempo efectivo; `pendiente` y `no_laborado` se conservan visibles.
CONFIRMADO = "confirmado"
PENDIENTE = "pendiente"
NO_LABORADO = "no_laborado"
DESCANSO_NO_COMPUTABLE = "descanso_no_computable"
# Ubicacion respecto del horario del dia logico (para que T4/T5 segmenten y hallen el exceso).
DENTRO_HORARIO = "dentro_de_horario"
FUERA_HORARIO = "fuera_de_horario"
DIA_NO_PROGRAMADO = "dia_no_programado"  # hay horario pero ese dia no tiene programacion: todo es exceso
SIN_HORARIO = "sin_horario"  # no hay horario vigente (HO06): sin clasificar, resultado provisional
# Descanso en el que cae la pieza.
COMPUTABLE = "computable"
NO_COMPUTABLE = "no_computable"


@dataclass(frozen=True)
class Complemento:
    """Movimiento administrativo (p. ej. contingencia, plan 17) con su procedencia explicita.

    Solo el `aprobado` cuenta como tiempo; uno no aprobado se conserva como pendiente.
    """

    id: str
    intervalo: Intervalo  # segundos de epoch
    empresa: str | None = None
    aprobado: bool = False
    origen: str = "ADMINISTRATIVO_CONTINGENCIA"


@dataclass(frozen=True)
class Confirmacion:
    """Resolucion de RH sobre tiempo fuera de horario: `trabajado` False = solo presencia (TO06)."""

    intervalo: Intervalo  # segundos de epoch
    trabajado: bool
    motivo: str = ""


@dataclass(frozen=True)
class PiezaEfectiva:
    intervalo: Intervalo
    dia_logico: date
    fecha_real: date
    origen: str
    estado: str
    ubicacion: str
    descanso: str | None = None
    empresa: str | None = None
    reloj: str | None = None
    referencia: str | None = None  # id del complemento, si lo hay


@dataclass(frozen=True)
class ResultadoEfectivo:
    piezas: tuple[PiezaEfectiva, ...] = ()
    provisional: bool = False
    alertas: tuple[str, ...] = ()
    motivos: tuple[str, ...] = ()

    def total_s(self, estado: str) -> int:
        return sum(p.intervalo.duracion for p in self.piezas if p.estado == estado)

    @property
    def confirmado_s(self) -> int:
        return self.total_s(CONFIRMADO)

    @property
    def pendiente_s(self) -> int:
        return self.total_s(PENDIENTE)


@dataclass(frozen=True)
class _Fuente:
    intervalo: Intervalo
    origen: str
    aprobada: bool
    empresa: str | None
    reloj: str | None
    referencia: str | None
    orden: tuple


def _fuentes(emparejados, complementos) -> list[_Fuente]:
    fuentes = []
    for e in emparejados:
        traslado = e.etiqueta == TRASLADO
        origen_ck = e.hasta if traslado else e.desde  # el traslado se atribuye a la empresa destino
        fuentes.append(_Fuente(
            e.intervalo, ORIGEN_TRASLADO if traslado else CHECADA, True, origen_ck.empresa, origen_ck.reloj,
            None, (0, e.intervalo.inicio, e.intervalo.fin, clave_orden(e.desde), clave_orden(e.hasta)),
        ))
    for c in complementos:
        fuentes.append(_Fuente(
            c.intervalo, COMPLEMENTO, c.aprobado, c.empresa, None, c.id,
            (1 if c.aprobado else 2, c.intervalo.inicio, c.intervalo.fin, c.id),
        ))
    return sorted(fuentes, key=lambda f: f.orden)


def _restar(partes: list[Intervalo], cubierto: Intervalo) -> list[Intervalo]:
    resto = []
    for p in partes:
        comun = p.interseccion(cubierto)
        if comun is None:
            resto.append(p)
            continue
        if p.inicio < comun.inicio:
            resto.append(Intervalo(p.inicio, comun.inicio))
        if comun.fin < p.fin:
            resto.append(Intervalo(comun.fin, p.fin))
    return resto


def _contiene(intervalos, instante: int) -> bool:
    return any(i.contiene(instante) for i in intervalos)


def _resolver_confirmacion(confirmaciones, instante: int) -> str | None:
    aplicables = [c.trabajado for c in confirmaciones if c.intervalo.contiene(instante)]
    if not aplicables:
        return None
    if all(aplicables):
        return CONFIRMADO
    return NO_LABORADO if not any(aplicables) else PENDIENTE  # resoluciones contradictorias: pendiente


def _piezas_del_dia(dia: date, items, horarios, versiones, confirmaciones, motivos: set[str]) -> list[PiezaEfectiva]:
    """Piezas de un dia logico. `items`: (subintervalo, fuente) ya sin segundos repetidos."""
    horario = resolver_horario(horarios, dia)
    programadas, descansos = instantes_del_dia(horario, dia) if horario else ((), ())
    if horario is None:
        motivos.add("horario_faltante")
    tolerancias = None
    if horario is not None and programadas:
        try:
            tolerancias = resolver_tolerancias(versiones, dia, horario.empresa, horario.tolerancias)
        except FaltaParametro as falta:
            motivos.add(f"falta:{falta.clave}")
    ventanas = []
    if tolerancias is not None:  # TO06: solo marca lo dudoso de los bordes del dia; no suprime ni suma
        primero, ultimo = min(p.inicio for p in programadas), max(p.fin for p in programadas)
        ventanas = [
            Intervalo(primero - tolerancias.entrada_anticipada_s, primero),
            Intervalo(ultimo, ultimo + tolerancias.salida_posterior_s),
        ]
    ubicacion_fija = SIN_HORARIO if horario is None else DIA_NO_PROGRAMADO if not programadas else None
    cortes_fijos = {
        x
        for i in (*programadas, *ventanas, *(d.intervalo for d in descansos), *(c.intervalo for c in confirmaciones))
        for x in (i.inicio, i.fin)
    }
    piezas = []
    for sub, fuente in items:
        cortes = sorted({sub.inicio, sub.fin} | {c for c in cortes_fijos if sub.inicio < c < sub.fin})
        for a, b in zip(cortes, cortes[1:]):
            ubicacion = ubicacion_fija or (DENTRO_HORARIO if _contiene(programadas, a) else FUERA_HORARIO)
            descanso = next(
                (COMPUTABLE if d.computable else NO_COMPUTABLE for d in descansos if d.intervalo.contiene(a)), None
            )
            if descanso == NO_COMPUTABLE:
                estado = DESCANSO_NO_COMPUTABLE
            elif not fuente.aprobada:
                estado = PENDIENTE
            elif fuente.origen == COMPLEMENTO or ubicacion in (DENTRO_HORARIO, SIN_HORARIO):
                estado = CONFIRMADO
            else:  # fuera de horario: lo resuelve RH; sin resolucion, la ventana de tolerancia queda dudosa
                dudoso = fuente.origen == CHECADA and _contiene(ventanas, a)
                estado = _resolver_confirmacion(confirmaciones, a) or (PENDIENTE if dudoso else CONFIRMADO)
            piezas.append(PiezaEfectiva(
                Intervalo(a, b), dia, dia, fuente.origen, estado, ubicacion, descanso,
                fuente.empresa, fuente.reloj, fuente.referencia,
            ))
    # Descanso computable (art. 63/64): cuenta aunque el trabajador haya checado salida, si hay
    # trabajo confirmado a ambos lados del hueco.
    trabajado = tiempo_sin_traslape([sub for sub, f in items if f.aprobada])
    for antes, despues in zip(trabajado, trabajado[1:]):
        hueco = Intervalo(antes.fin, despues.inicio)
        for d in (x for x in descansos if x.computable):
            comun = hueco.interseccion(d.intervalo)
            if comun is not None:
                previa = next(f for sub, f in items if f.aprobada and sub.fin == antes.fin)
                piezas.append(PiezaEfectiva(
                    comun, dia, dia, DESCANSO_COMPUTABLE, CONFIRMADO, DENTRO_HORARIO, COMPUTABLE,
                    previa.empresa, previa.reloj, None,
                ))
    return piezas


def _fusionar(piezas: list[PiezaEfectiva]) -> list[PiezaEfectiva]:
    """Une piezas contiguas que solo difieren en el intervalo (menos fragmentos, mismo tiempo)."""
    fusion: list[PiezaEfectiva] = []
    for p in sorted(piezas, key=lambda x: (x.intervalo.inicio, x.intervalo.fin, x.origen, x.estado)):
        ultima = fusion[-1] if fusion else None
        if ultima is not None and ultima.intervalo.fin == p.intervalo.inicio and (
            replace(ultima, intervalo=p.intervalo) == p
        ):
            fusion[-1] = replace(ultima, intervalo=Intervalo(ultima.intervalo.inicio, p.intervalo.fin))
        else:
            fusion.append(p)
    return fusion


def construir_intervalos_efectivos(
    emparejados, horarios, zona: tzinfo, *, versiones=(), complementos=(), confirmaciones=()
) -> ResultadoEfectivo:
    """Paso 6: tiempo efectivo por pieza, con su dia logico, fecha real y ubicacion en el horario.

    - Descansos del horario (Q03, «descanso segun horario, sin checada»): el no computable se
      resta SOLO donde cae dentro de un intervalo trabajado (queda como pieza
      `descanso_no_computable`); el computable se conserva y, si el trabajador checo salida, se
      incorpora el tramo del hueco que cubre el descanso.
    - Complementos aprobados entran con su origen; los no aprobados quedan pendientes. Ningun
      segundo se cuenta dos veces (las checadas tienen prioridad).
    - La tolerancia NO cambia el tiempo fisico (TO04): solo marca `pendiente` el tiempo fuera de
      horario pegado al inicio/fin del dia, dentro de la tolerancia, mientras RH no confirme si fue
      trabajo (`Confirmacion`). Mas alla de la tolerancia se cuenta como exceso confirmado.
    - Falta de horario o de tolerancias: resultado provisional con AL12; los datos se conservan.
    Cada pieza es un segmento disjunto; T4 agrega fronteras de semana/vigencia y T5 asigna extras.
    """
    previa = fin_de_jornada_previa(horarios, zona)
    cubierto: list[Intervalo] = []
    por_dia: dict[date, list] = {}
    for fuente in _fuentes(emparejados, complementos):
        dia = asignar_dia_logico(fuente.intervalo, zona, previa)
        restos = [fuente.intervalo]
        for c in cubierto:
            restos = _restar(restos, c)
        cubierto.append(fuente.intervalo)
        por_dia.setdefault(dia, []).extend((r, fuente) for r in restos if r.duracion > 0)
    motivos: set[str] = set()
    piezas = []
    for dia in sorted(por_dia):
        piezas += _piezas_del_dia(dia, por_dia[dia], horarios, versiones, confirmaciones, motivos)
    por_fecha = [
        replace(p, intervalo=parte.intervalo, fecha_real=parte.fecha_real)
        for p in piezas
        for parte in dividir_por_fecha_real(p.intervalo, zona)
    ]
    return ResultadoEfectivo(
        tuple(_fusionar(por_fecha)), bool(motivos), (AL12,) if motivos else (), tuple(sorted(motivos))
    )
