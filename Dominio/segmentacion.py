# -*- coding: utf-8 -*-
"""Segmentacion y clasificacion base (doc. 03 8.2 pasos 4 y 8; plan 5.1-5 y 5.2).

Parte de las piezas efectivas de T3 (`ResultadoEfectivo`) y las corta en cada frontera donde
cambia algo que el calculo posterior necesita saber:
- horario y descansos: ya vienen cortados por `construir_intervalos_efectivos`;
- medianoche local (fecha real: festivos y vigencias, P-26). La frontera de SEMANA laboral y todo
  cambio de vigencia de un parametro caen siempre en una medianoche local, porque la semana y la
  vigencia se resuelven por fecha trabajada: cortar por fecha real las garantiza;
- franja nocturna versionada (`NOCTURNO_INICIO_S`/`NOCTURNO_FIN_S`, art. 60), resuelta por la
  fecha real del segmento con `resolver_vigente`; nunca se fija en el codigo.

Cada segmento queda con: clase (dentro de horario / exceso diario / sin clasificar), banda
(diurna/nocturna), semana laboral, etiquetas de dia (domingo, descanso obligatorio, descanso
semanal trabajado: solo etiquetas, jamas tiempo extra, P-29) y su estado de T3 sin tocar
(`pendiente` sigue pendiente). La jornada diurna/nocturna/mixta se clasifica por dia logico con
`regimenes.clasificar_jornada` (P-26, P-27).

Principios: ningun segundo se pierde ni se repite (la suma de segmentos es la de las piezas);
parametro faltante, ambiguo o invalido => el segmento se conserva, el resultado queda provisional
con AL12 y el criterio no se inventa; sin excepciones que aborten el calculo. T5 asigna extras.
"""

from dataclasses import dataclass
from datetime import date, tzinfo

from Dominio import normatividad as n
from Dominio.calendario import (
    AL12,
    ClasificacionDia,
    clasificar_dia,
    dia_inicio_semana,
    dividir_por_fecha_real,
    semana_laboral,
)
from Dominio.horarios import (
    _ERRORES_DE_CONFIGURACION,
    CONFIRMADO,
    DENTRO_HORARIO,
    DIA_NO_PROGRAMADO,
    FUERA_HORARIO,
    HorarioAmbiguo,
    ResultadoEfectivo,
    SIN_HORARIO,
    _motivo_de,
    resolver_horario,
)
from Dominio.modelos import ORIGEN_PATRONAL, Vigencia
from Dominio.normatividad import resolver_vigente
from Dominio.regimenes import clasificar_jornada
from Dominio.tiempo import Intervalo, instante_local

# Clase del segmento respecto del horario del dia logico (doc. 03 8.2 paso 8).
CLASE_DENTRO = "dentro_de_horario"
CLASE_EXCESO = "exceso_diario"
CLASE_SIN_CLASIFICAR = "sin_clasificar"  # no hay horario vigente (HO06): provisional

BANDA_DIURNA = "diurna"
BANDA_NOCTURNA = "nocturna"

_CLASE_POR_UBICACION = {
    DENTRO_HORARIO: CLASE_DENTRO,
    FUERA_HORARIO: CLASE_EXCESO,
    DIA_NO_PROGRAMADO: CLASE_EXCESO,  # hay horario pero ese dia no se programa: todo es exceso
    SIN_HORARIO: CLASE_SIN_CLASIFICAR,
}

_SEGUNDOS_DIA = 86_400


@dataclass(frozen=True)
class Segmento:
    intervalo: Intervalo
    dia_logico: date
    fecha_real: date
    semana: Vigencia | None
    clase: str
    banda: str | None  # None: la franja nocturna no se pudo resolver
    etiquetas: frozenset[str]
    origen: str
    estado: str
    ubicacion: str
    descanso: str | None = None
    empresa: str | None = None
    reloj: str | None = None
    referencia: str | None = None
    motivos: tuple[str, ...] = ()


@dataclass(frozen=True)
class JornadaClasificada:
    """Clasificacion de la jornada de un dia logico con el tiempo confirmado dentro de horario."""

    dia_logico: date
    nocturnos_s: int
    diurnos_s: int
    clasificacion: str | None  # diurna | nocturna | mixta; None si falta un dato (provisional)
    regimen_declarado: str | None = None


@dataclass(frozen=True)
class ResultadoSegmentacion:
    segmentos: tuple[Segmento, ...] = ()
    jornadas: tuple[JornadaClasificada, ...] = ()
    provisional: bool = False
    alertas: tuple[str, ...] = ()
    motivos: tuple[str, ...] = ()

    def total_s(self, **filtros) -> int:
        return sum(
            s.intervalo.duracion for s in self.segmentos if all(getattr(s, k) == v for k, v in filtros.items())
        )


def _franja_de(versiones, fecha: date):
    """((inicio_s, fin_s), None) vigente en la fecha, o (None, motivo) si falta, es ambigua o invalida."""
    try:
        inicio = resolver_vigente(versiones, n.NOCTURNO_INICIO_S, fecha).valor
        fin = resolver_vigente(versiones, n.NOCTURNO_FIN_S, fecha).valor
    except _ERRORES_DE_CONFIGURACION as error:
        return None, _motivo_de(error)
    valida = all(0 <= v <= _SEGUNDOS_DIA for v in (inicio, fin)) and inicio != fin
    return ((inicio, fin), None) if valida else (None, "franja_nocturna_invalida")


def _tramos_nocturnos(franja, fecha: date, zona: tzinfo) -> tuple[Intervalo, ...]:
    """Tramos nocturnos de la fecha real, en hora de pared local (la franja cruza la medianoche)."""
    inicio, fin = franja
    pares = [(0, fin), (inicio, _SEGUNDOS_DIA)] if inicio > fin else [(inicio, fin)]
    return tuple(
        Intervalo(instante_local(fecha, a, zona), instante_local(fecha, b, zona)) for a, b in pares if a < b
    )


class _Contexto:
    """Resuelve y memoriza por fecha lo versionado; cada dato faltante se vuelve un motivo."""

    def __init__(self, zona, horarios, calendarios, versiones, empresa):
        self.zona, self.horarios, self.calendarios = zona, horarios, calendarios
        self.versiones, self.empresa = versiones, empresa
        self._franjas, self._horarios, self._semanas = {}, {}, {}

    def franja(self, fecha: date):
        if fecha not in self._franjas:
            self._franjas[fecha] = _franja_de(self.versiones, fecha)
        return self._franjas[fecha]

    def horario(self, dia: date):
        if dia not in self._horarios:
            try:
                self._horarios[dia] = resolver_horario(self.horarios, dia)
            except HorarioAmbiguo:  # ya lo reporta T3; aqui se trata como horario faltante
                self._horarios[dia] = None
        return self._horarios[dia]

    def semana(self, fecha: date, dia_logico: date):
        empresa = self.empresa or getattr(self.horario(dia_logico), "empresa", None)
        if (fecha, empresa) not in self._semanas:
            try:
                resultado = (semana_laboral(fecha, dia_inicio_semana(self.versiones, fecha, empresa)), None)
            except _ERRORES_DE_CONFIGURACION as error:
                resultado = (None, _motivo_de(error))
            except ValueError:  # dia de inicio fuera de 0..6
                resultado = (None, f"semana_inicio_invalido:{n.SEMANA_INICIO_DIA}")
            self._semanas[(fecha, empresa)] = resultado
        return self._semanas[(fecha, empresa)]

    def dia(self, pieza, fecha: date, trabajado_s: int) -> ClasificacionDia:
        """Etiquetas: la base (programado/descanso semanal) es del dia logico; el calendario, de la fecha real."""
        horario = self.horario(pieza.dia_logico)
        programado = horario is not None and horario.programado(pieza.dia_logico.weekday())
        descanso = horario is not None and horario.es_descanso_semanal(pieza.dia_logico.weekday())
        return clasificar_dia(
            fecha, self.calendarios, programado=programado, descanso_semanal=descanso, trabajado_s=trabajado_s
        )


def _clave_pieza(p):
    return (
        p.intervalo.inicio, p.intervalo.fin, p.origen, p.estado, p.ubicacion, p.dia_logico,
        p.descanso or "", p.empresa or "", p.reloj or "", p.referencia or "",
    )


def _segmentos_de(pieza, ctx: _Contexto) -> list[Segmento]:
    segmentos = []
    for parte in dividir_por_fecha_real(pieza.intervalo, ctx.zona):
        franja, motivo_franja = ctx.franja(parte.fecha_real)
        tramos = _tramos_nocturnos(franja, parte.fecha_real, ctx.zona) if franja else ()
        cortes = sorted(
            {parte.intervalo.inicio, parte.intervalo.fin}
            | {x for t in tramos for x in (t.inicio, t.fin) if parte.intervalo.inicio < x < parte.intervalo.fin}
        )
        semana, motivo_semana = ctx.semana(parte.fecha_real, pieza.dia_logico)
        for a, b in zip(cortes, cortes[1:]):
            sub = Intervalo(a, b)
            banda = None if franja is None else (
                BANDA_NOCTURNA if any(t.contiene(a) for t in tramos) else BANDA_DIURNA
            )
            dia = ctx.dia(pieza, parte.fecha_real, sub.duracion if pieza.estado == CONFIRMADO else 0)
            motivos = {m for m in (motivo_franja, motivo_semana, *dia.motivos) if m}
            segmentos.append(Segmento(
                sub, pieza.dia_logico, parte.fecha_real, semana,
                _CLASE_POR_UBICACION.get(pieza.ubicacion, CLASE_SIN_CLASIFICAR), banda, dia.etiquetas,
                pieza.origen, pieza.estado, pieza.ubicacion, pieza.descanso, pieza.empresa, pieza.reloj,
                pieza.referencia, tuple(sorted(motivos)),
            ))
    return segmentos


def _clasificar_jornadas(segmentos, ctx: _Contexto, motivos: set[str]) -> tuple[JornadaClasificada, ...]:
    por_dia: dict[date, list[Segmento]] = {}
    for s in segmentos:
        if s.clase == CLASE_DENTRO and s.estado == CONFIRMADO:
            por_dia.setdefault(s.dia_logico, []).append(s)
    jornadas = []
    for dia in sorted(por_dia):
        propios = por_dia[dia]
        noct = sum(s.intervalo.duracion for s in propios if s.banda == BANDA_NOCTURNA)
        diurno = sum(s.intervalo.duracion for s in propios if s.banda == BANDA_DIURNA)
        clasificacion = None
        if all(s.banda is not None for s in propios):  # sin franja resuelta no se adivina la jornada
            try:
                clasificacion = clasificar_jornada(noct, diurno, ctx.versiones, dia)
            except _ERRORES_DE_CONFIGURACION as error:
                motivos.add(_motivo_de(error))
        horario = ctx.horario(dia)
        jornadas.append(JornadaClasificada(dia, noct, diurno, clasificacion, horario.regimen if horario else None))
    return tuple(jornadas)


def segmentar(
    efectivo: ResultadoEfectivo, zona: tzinfo, horarios, calendarios, versiones, empresa: str | None = None
) -> ResultadoSegmentacion:
    """Segmenta y clasifica las piezas efectivas; determinista y sin perder ni duplicar segundos.

    `empresa` da el alcance de la politica patronal (dia de inicio de semana); si es None se usa
    la del horario del dia logico. `versiones` mezcla norma legal y politica patronal.
    """
    ctx = _Contexto(zona, horarios, calendarios, versiones, empresa)
    segmentos = [s for p in sorted(efectivo.piezas, key=_clave_pieza) for s in _segmentos_de(p, ctx)]
    segmentos.sort(key=lambda s: (s.intervalo.inicio, s.intervalo.fin, s.origen, s.estado, s.reloj or "", s.referencia or ""))
    motivos = {m for s in segmentos for m in s.motivos}
    jornadas = _clasificar_jornadas(segmentos, ctx, motivos)
    todos = set(efectivo.motivos) | motivos
    return ResultadoSegmentacion(
        tuple(segmentos),
        jornadas,
        efectivo.provisional or bool(motivos),
        tuple(sorted(set(efectivo.alertas) | ({AL12} if motivos else set()))),
        tuple(sorted(todos)),
    )
