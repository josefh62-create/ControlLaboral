# -*- coding: utf-8 -*-
"""Criterio de inicio de extra (doc. 03 8.2 pasos 9 y 10; plan 5.2; decision del propietario Q05).

`CriterioExtra` es un Protocol; cada criterio se registra por codigo en `CRITERIOS`. Si el
reglamento STPS o el asesor laboral cambian el criterio, se agrega otra implementacion y una version
de parametro, sin tocar el resto (plan 5.2-4). Hoy existe `semanal_con_acuerdo`:

1. Cuanto: extra semanal = max(0, tiempo efectivo CONFIRMADO de la semana - tope ordinario semanal
   vigente). Los dias cortos compensan a los largos dentro de la misma semana.
2. Donde: solo en segmentos de exceso diario (trabajo confirmado fuera del horario del dia, incluido el
   de dias sin horario), los MAS RECIENTES primero: el exceso mas antiguo compensa faltantes. Un segmento
   se divide exactamente: la extra son sus ultimos segundos. Si la extra supera todo el exceso (solo ocurre
   cuando el horario acordado rebasa el tope), el remanente se asigna a los ultimos minutos programados de
   la semana, en orden cronologico inverso, con la alerta HO03. El tiempo nunca se pierde ni se bloquea.
3. Lo que el criterio no puede decidir (tope semanal faltante, ambiguo o distinto dentro de la semana de
   transicion, semana sin resolver) NO se inventa: queda `pendiente` de clasificacion, la semana
   `provisional` con AL12 y la evidencia intacta (plan 8; doc. 03 8.2).

El tope sale siempre de `resolver_vigente` (nunca de una constante). Aqui no se reparten tramos
doble/triple: eso es de `tramos_extra`.
"""

from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Protocol, runtime_checkable

from Dominio import normatividad as n
from Dominio.calendario import AL12
from Dominio.horarios import _ERRORES_DE_CONFIGURACION, CONFIRMADO, HO03, _motivo_de
from Dominio.modelos import Vigencia
from Dominio.normatividad import resolver_vigente
from Dominio.segmentacion import CLASE_DENTRO, JornadaClasificada, ResultadoSegmentacion, Segmento
from Dominio.tiempo import Intervalo

CODIGO_SEMANAL_CON_ACUERDO = "semanal_con_acuerdo"

# Tipo de cada pieza confirmada tras aplicar el criterio.
ORDINARIO = "ordinario"
EXTRA = "extra"  # extra asignada: `tramos_extra` la reparte en doble/triple
PENDIENTE = "pendiente_clasificacion"  # el criterio no pudo decidirla: se conserva y se alerta

# De donde sale una pieza de extra.
ORIGEN_EXCESO = "exceso_diario"
ORIGEN_REMANENTE = "remanente_programado"

MOTIVO_SEMANA_SIN_RESOLVER = "semana_sin_resolver"
MOTIVO_TRANSICION = f"semana_transicion:{n.ORDINARIA_SEMANAL_S}"


class CriterioDesconocido(LookupError):
    """Codigo de criterio no registrado: no se sustituye por otro en silencio."""


@dataclass(frozen=True)
class PiezaAsignada:
    segmento: Segmento  # el segmento original, o la parte exacta de el que corresponde al tipo
    tipo: str
    origen: str | None = None  # solo para EXTRA
    motivo: str | None = None  # solo para PENDIENTE


@dataclass(frozen=True)
class AsignacionSemana:
    semana: Vigencia | None
    criterio: str
    piezas: tuple[PiezaAsignada, ...]  # solo tiempo confirmado, en orden cronologico
    no_confirmados: tuple[Segmento, ...]  # pendiente / no laborado / descanso no computable: intactos
    jornadas: tuple[JornadaClasificada, ...] = ()
    tope_semanal_s: int | None = None  # None si falta, es ambiguo o cambia dentro de la semana
    provisional: bool = False
    alertas: tuple[str, ...] = ()
    motivos: tuple[str, ...] = ()

    def total_s(self, tipo: str) -> int:
        return sum(p.segmento.intervalo.duracion for p in self.piezas if p.tipo == tipo)

    @property
    def confirmado_s(self) -> int:
        return sum(p.segmento.intervalo.duracion for p in self.piezas)

    @property
    def ordinario_s(self) -> int:
        return self.total_s(ORDINARIO)

    @property
    def extra_s(self) -> int:
        return self.total_s(EXTRA)

    @property
    def pendiente_s(self) -> int:
        return self.total_s(PENDIENTE)


@runtime_checkable
class CriterioExtra(Protocol):
    codigo: str

    def asignar(
        self, segmentos: tuple[Segmento, ...], jornadas: tuple[JornadaClasificada, ...], versiones, semana: Vigencia | None
    ) -> AsignacionSemana:
        """Reparte el tiempo confirmado de UNA semana en ordinario / extra / pendiente."""


CRITERIOS: dict[str, CriterioExtra] = {}


def registrar_criterio(criterio: CriterioExtra) -> CriterioExtra:
    CRITERIOS[criterio.codigo] = criterio
    return criterio


def obtener_criterio(codigo: str) -> CriterioExtra:
    try:
        return CRITERIOS[codigo]
    except KeyError:
        raise CriterioDesconocido(f"criterio de extra no registrado: {codigo!r}") from None


def _clave_segmento(s: Segmento):
    return (s.intervalo.inicio, s.intervalo.fin, s.origen, s.estado, s.reloj or "", s.referencia or "")


def _topes_semanales(versiones, semana: Vigencia | None):
    """((menor, mayor), None) del tope ordinario semanal en los dias de la semana, o (None, motivo).

    Distintos valores dentro de la misma semana = semana de transicion (28/12/2026-03/01/2027): no se
    prorratea ni se elige uno; el criterio trabaja con ambos extremos.
    """
    if semana is None:
        return None, MOTIVO_SEMANA_SIN_RESOLVER
    fin = semana.hasta or semana.desde + timedelta(days=7)
    valores = set()
    dia: date = semana.desde
    while dia < fin:
        try:
            valores.add(resolver_vigente(versiones, n.ORDINARIA_SEMANAL_S, dia).valor)
        except _ERRORES_DE_CONFIGURACION as error:
            return None, _motivo_de(error)
        dia += timedelta(days=1)
    return (min(valores), max(valores)), None


def _asignar_de_atras(confirmados, indices, restante, tomado, origen) -> int:
    """Toma `restante` segundos de los segmentos `indices` empezando por el mas reciente; devuelve lo que sobra."""
    for i in reversed(indices):
        if restante <= 0:
            break
        tomo = min(restante, confirmados[i].intervalo.duracion)
        tomado[i] = (tomo, origen)
        restante -= tomo
    return restante


def _repartir(confirmados: list[Segmento], extra_s: int):
    """Piezas cronologicas con la extra en el exceso mas reciente y, si sobra, en lo programado mas tardio."""
    excesos = [i for i, s in enumerate(confirmados) if s.clase != CLASE_DENTRO]
    programados = [i for i, s in enumerate(confirmados) if s.clase == CLASE_DENTRO]
    tomado: dict[int, tuple[int, str]] = {}
    sobrante = _asignar_de_atras(confirmados, excesos, extra_s, tomado, ORIGEN_EXCESO)
    _asignar_de_atras(confirmados, programados, sobrante, tomado, ORIGEN_REMANENTE)
    piezas = []
    for i, s in enumerate(confirmados):
        if i not in tomado:
            piezas.append(PiezaAsignada(s, ORDINARIO))
            continue
        tomo, origen = tomado[i]
        corte = s.intervalo.fin - tomo
        if corte > s.intervalo.inicio:
            piezas.append(PiezaAsignada(replace(s, intervalo=Intervalo(s.intervalo.inicio, corte)), ORDINARIO))
        piezas.append(PiezaAsignada(replace(s, intervalo=Intervalo(corte, s.intervalo.fin)), EXTRA, origen))
    return piezas, sobrante > 0


def _pendiente_los_primeros(piezas: list[PiezaAsignada], segundos: int, motivo: str) -> list[PiezaAsignada]:
    """Las `segundos` mas antiguas de la extra pasan a pendiente (division exacta)."""
    resultado = []
    for p in piezas:
        if p.tipo != EXTRA or segundos <= 0:
            resultado.append(p)
            continue
        duracion = p.segmento.intervalo.duracion
        toma = min(segundos, duracion)
        segundos -= toma
        corte = p.segmento.intervalo.inicio + toma
        s = p.segmento
        resultado.append(PiezaAsignada(replace(s, intervalo=Intervalo(s.intervalo.inicio, corte)), PENDIENTE, None, motivo))
        if toma < duracion:
            resultado.append(replace(p, segmento=replace(s, intervalo=Intervalo(corte, s.intervalo.fin))))
    return resultado


class SemanalConAcuerdo:
    """Criterio por defecto desde 2027 (decision del propietario 24/11/2026; plan 5.2)."""

    codigo = CODIGO_SEMANAL_CON_ACUERDO

    def asignar(self, segmentos, jornadas, versiones, semana) -> AsignacionSemana:
        ordenados = sorted(segmentos, key=_clave_segmento)
        confirmados = [s for s in ordenados if s.estado == CONFIRMADO]
        no_confirmados = tuple(s for s in ordenados if s.estado != CONFIRMADO)
        motivos = {m for s in ordenados for m in s.motivos}
        topes, motivo = _topes_semanales(versiones, semana)
        alertas: set[str] = set()
        if topes is None:
            motivos.add(motivo)
            piezas = [PiezaAsignada(s, PENDIENTE, None, motivo) for s in confirmados]
            tope = None
        else:
            menor, mayor = topes
            total = sum(s.intervalo.duracion for s in confirmados)
            piezas, uso_remanente = _repartir(confirmados, max(0, total - menor))
            if uso_remanente:
                alertas.add(HO03)
            if menor != mayor:  # transicion: la extra segura es la mas reciente; el resto espera criterio
                motivos.add(MOTIVO_TRANSICION)
                banda = max(0, total - menor) - max(0, total - mayor)
                piezas = _pendiente_los_primeros(piezas, banda, MOTIVO_TRANSICION)
            tope = mayor if menor == mayor else None
        if motivos:
            alertas.add(AL12)
        return AsignacionSemana(
            semana, self.codigo, tuple(piezas), no_confirmados, tuple(jornadas), tope, bool(motivos),
            tuple(sorted(alertas)), tuple(sorted(motivos)),
        )


registrar_criterio(SemanalConAcuerdo())


def asignar_extra(
    segmentacion: ResultadoSegmentacion, versiones, criterio: str = CODIGO_SEMANAL_CON_ACUERDO
) -> tuple[AsignacionSemana, ...]:
    """Aplica el criterio registrado a cada semana laboral de la segmentacion (una asignacion por semana).

    Los segmentos sin semana resuelta forman su propio grupo: el criterio los deja pendientes.
    """
    aplicar = obtener_criterio(criterio)
    grupos: dict[Vigencia | None, list[Segmento]] = {}
    for s in segmentacion.segmentos:
        grupos.setdefault(s.semana, []).append(s)
    resultados = []
    for semana in sorted(grupos, key=lambda w: (w is None, w.desde if w else date.min)):
        propios = tuple(grupos[semana])  # el criterio ordena por su cuenta
        dias = {s.dia_logico for s in propios}
        jornadas = tuple(j for j in segmentacion.jornadas if j.dia_logico in dias)
        resultados.append(aplicar.asignar(propios, jornadas, versiones, semana))
    return tuple(resultados)
