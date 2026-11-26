# -*- coding: utf-8 -*-
"""Emparejamiento de entradas y salidas sobre la secuencia UNIFICADA de todos los relojes.

Plan 5.1 paso 4 y doc. 03 8.2 paso 3. Reglas (decisiones del propietario 26/11/2026
y principio P-30: jamas se fabrica una hora de salida):

- Se empareja sobre la secuencia ordenada por instante de TODOS los relojes del
  trabajador; cada extremo conserva su reloj y empresa de origen.
- No se asume alternancia perfecta. Sin `sentido` declarado, el rol sale de la
  alternancia (la siguiente checada cierra lo abierto). Con `sentido`, este manda.
- `impar`: checada sin contraparte (entrada sin salida o salida sin entrada).
- `ambigua`: la secuencia contradice el sentido declarado. Lo dudoso no se cuenta.
- `intervalo_excedido`: un par supera el maximo versionado `INTERVALO_MAX_S` (inicial
  16 h, decision del propietario 26/11/2026, configurable por empresa; se usa la de la
  checada de ENTRADA). No se cuenta y conserva ambos extremos. Recuperacion: sin
  sentido declarado, la checada de cierre se reinterpreta como nueva entrada, de modo
  que una salida faltante no desplaza el emparejamiento del resto de la semana.
- `traslape`: dos intervalos (de relojes distintos) se encimian; ambos se conservan y
  `tiempo_sin_traslape` da la union para no contar el mismo segundo dos veces.
- Traslado entre empresas: hueco entre una salida y una entrada de empresas distintas
  el mismo dia (fecha local de cada extremo; Q-F abierta para turnos que cruzan
  medianoche). Hasta el maximo versionado (`TRASLADO_MAX_S`, origen patronal) es un
  intervalo `traslado`; por encima, incidencia `traslado_excedido` y no se computa. El
  maximo es el de la empresa DESTINO. Si el hueco entre empresas cruza la medianoche
  local y no excede el maximo, no se adivina: incidencia `traslado_pendiente_q_f`
  (pregunta abierta Q-F, doc. 03 15.2) sin computar; un hueco mayor al maximo no puede
  ser traslado y no genera incidencia.
- Las checadas marcadas `posible_duplicado` o `futura` no participan; siguen existiendo
  en las marcas (nada se elimina).
"""

from dataclasses import dataclass

from Dominio.checadas import (
    ENTRADA,
    FUTURA,
    POSIBLE_DUPLICADO,
    SALIDA,
    Checada,
    clave_orden,
    ordenar_checadas,
)
from Dominio.modelos import ORIGEN_PATRONAL
from Dominio.normatividad import INTERVALO_MAX_S, TRASLADO_MAX_S, resolver_vigente
from Dominio.tiempo import Intervalo

NORMAL = "normal"
TRASLADO = "traslado"

IMPAR = "impar"
AMBIGUA = "ambigua"
TRASLAPE = "traslape"
TRASLADO_EXCEDIDO = "traslado_excedido"
INTERVALO_EXCEDIDO = "intervalo_excedido"
TRASLADO_PENDIENTE_Q_F = "traslado_pendiente_q_f"

_EXCLUIDAS = frozenset({POSIBLE_DUPLICADO, FUTURA})


@dataclass(frozen=True)
class IntervaloEmparejado:
    """Intervalo con la checada de origen de cada extremo y su etiqueta."""

    intervalo: Intervalo
    desde: Checada
    hasta: Checada
    etiqueta: str = NORMAL


@dataclass(frozen=True)
class Incidencia:
    tipo: str
    checadas: tuple[Checada, ...]
    detalle: str = ""


@dataclass(frozen=True)
class ResultadoEmparejamiento:
    intervalos: tuple[IntervaloEmparejado, ...] = ()
    incidencias: tuple[Incidencia, ...] = ()


def _incidencia(tipo: str, checadas, detalle: str = "") -> Incidencia:
    return Incidencia(tipo, ordenar_checadas(checadas), detalle)


def _clave_intervalo(i: IntervaloEmparejado):
    return (i.intervalo.inicio, i.intervalo.fin, clave_orden(i.desde), clave_orden(i.hasta))


def _clave_incidencia(i: Incidencia):
    return (
        min(c.instante_s for c in i.checadas),
        i.tipo,
        tuple(clave_orden(c) for c in i.checadas),
    )


def _par(entrada: Checada, salida: Checada) -> IntervaloEmparejado:
    return IntervaloEmparejado(Intervalo(entrada.instante_s, salida.instante_s), entrada, salida)


def _emparejar_secuencia(usables, versiones):
    """Recorre la secuencia ordenada; devuelve (intervalos normales, incidencias)."""
    abiertas: list[Checada] = []
    intervalos, incidencias = [], []
    for c in usables:
        rol = c.sentido or (SALIDA if abiertas else ENTRADA)
        if rol == SALIDA:
            mismo_reloj = [a for a in abiertas if a.reloj == c.reloj]
            if mismo_reloj:
                abierta = mismo_reloj[0]
            elif len(abiertas) == 1:
                abierta = abiertas[0]
            elif not abiertas:
                incidencias.append(_incidencia(IMPAR, [c], "salida sin entrada"))
                continue
            else:
                incidencias.append(
                    _incidencia(AMBIGUA, [c, *abiertas], "salida con varias entradas abiertas")
                )
                continue
            abiertas.remove(abierta)
            maximo = resolver_vigente(
                versiones, INTERVALO_MAX_S, abierta.fecha_local, ORIGEN_PATRONAL, abierta.empresa
            ).valor
            if c.instante_s - abierta.instante_s > maximo:
                incidencias.append(
                    _incidencia(INTERVALO_EXCEDIDO, [abierta, c], "intervalo mayor al maximo")
                )
                if c.sentido is None:  # sin sentido declarado, c puede ser una nueva entrada
                    abiertas.append(c)
                continue
            intervalos.append(_par(abierta, c))
        else:
            previa = next((a for a in abiertas if a.reloj == c.reloj), None)
            if previa is not None:
                abiertas.remove(previa)
                incidencias.append(
                    _incidencia(AMBIGUA, [previa, c], "dos entradas seguidas en el mismo reloj")
                )
            abiertas.append(c)
    incidencias += [_incidencia(IMPAR, [a], "entrada sin salida") for a in abiertas]
    return intervalos, incidencias


def _traslapes(intervalos) -> list[Incidencia]:
    incidencias = []
    for k, b in enumerate(intervalos):
        for a in intervalos[:k]:
            if a.intervalo.se_traslapa(b.intervalo):
                incidencias.append(
                    _incidencia(TRASLAPE, {a.desde, a.hasta, b.desde, b.hasta}, "intervalos encimados")
                )
    return incidencias


def _traslados(intervalos, versiones):
    """Huecos entre empresas el mismo dia: (intervalos de traslado, incidencias excedidas)."""
    traslados, excedidos = [], []
    ultimo = None  # el intervalo con el fin mas tardio hasta ahora
    for sig in intervalos:
        if (
            ultimo is not None
            and sig.intervalo.inicio > ultimo.intervalo.fin
            and ultimo.hasta.empresa != sig.desde.empresa
        ):
            hueco = sig.intervalo.inicio - ultimo.intervalo.fin
            maximo = resolver_vigente(
                versiones,
                TRASLADO_MAX_S,
                ultimo.hasta.fecha_local,
                ORIGEN_PATRONAL,
                sig.desde.empresa,  # empresa destino
            ).valor
            if ultimo.hasta.fecha_local != sig.desde.fecha_local:
                if hueco <= maximo:
                    excedidos.append(
                        _incidencia(
                            TRASLADO_PENDIENTE_Q_F,
                            [ultimo.hasta, sig.desde],
                            "hueco entre empresas que cruza la medianoche (Q-F)",
                        )
                    )
            elif hueco <= maximo:
                traslados.append(
                    IntervaloEmparejado(
                        Intervalo(ultimo.intervalo.fin, sig.intervalo.inicio),
                        ultimo.hasta,
                        sig.desde,
                        TRASLADO,
                    )
                )
            else:
                excedidos.append(
                    _incidencia(
                        TRASLADO_EXCEDIDO,
                        [ultimo.hasta, sig.desde],
                        "traslado mayor al maximo; pendiente de revision",
                    )
                )
        if ultimo is None or sig.intervalo.fin > ultimo.intervalo.fin:
            ultimo = sig
    return traslados, excedidos


def emparejar(marcadas, versiones) -> ResultadoEmparejamiento:
    """Intervalos e incidencias a partir de las checadas marcadas de un trabajador.

    `versiones`: politica patronal (maximos de intervalo y traslado, via `resolver_vigente`); si falta
    una version se propaga `FaltaParametro` para que el llamador marque provisional.
    El maximo de intervalo y el de traslado son politica patronal por empresa.
    """
    usables = ordenar_checadas(cm.checada for cm in marcadas if not (cm.marcas & _EXCLUIDAS))
    intervalos, incidencias = _emparejar_secuencia(usables, versiones)
    intervalos.sort(key=_clave_intervalo)
    incidencias += _traslapes(intervalos)
    traslados, excedidos = _traslados(intervalos, versiones)
    todos = sorted(intervalos + traslados, key=_clave_intervalo)
    return ResultadoEmparejamiento(
        tuple(todos), tuple(sorted(incidencias + excedidos, key=_clave_incidencia))
    )


def tiempo_sin_traslape(intervalos) -> tuple[Intervalo, ...]:
    """Union de intervalos: ningun segundo se cuenta dos veces (plan 5.1 paso 4)."""
    unidos: list[Intervalo] = []
    for i in sorted(intervalos, key=lambda x: (x.inicio, x.fin)):
        if unidos and i.inicio <= unidos[-1].fin:
            if i.fin > unidos[-1].fin:
                unidos[-1] = Intervalo(unidos[-1].inicio, i.fin)
        else:
            unidos.append(i)
    return tuple(unidos)
