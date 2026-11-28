# -*- coding: utf-8 -*-
"""Derecho a alimentos por tiempo extra (plan 4.5 «Alimentos por tiempo extra», Q11; doc. 03 8.2 paso 13).

Por dia logico se marca a que comidas (desayuno, almuerzo, cena) tiene derecho el trabajador, SOLO si ese
dia genero tiempo extra confirmado (doble, triple o pendiente de clasificacion art. 66; el tiempo neutro
`tiempo_pendiente_de_clasificar` no cuenta: no se sabe si es extra). Las reglas son politica patronal
(`ORIGEN_PATRONAL`), por empresa y con vigencia, resueltas con `resolver_vigente` por el dia logico
(precedencia empresa > general). Tres condiciones opcionales por comida, todas en segundos:

- `alimento_<comida>_extra_min_s`: extra del dia >= valor;
- `alimento_<comida>_extra_inicio_desde_s`: la extra del dia empieza a esa hora o despues;
- `alimento_<comida>_extra_fin_desde_s`: la extra del dia termina a esa hora o despues.

Las horas son segundos desde la medianoche local del dia logico (un fin a las 02:00 del dia siguiente
es 26 h). Si hay varias condiciones configuradas deben cumplirse todas; sin ninguna, la comida no se marca.
No hay semilla: ninguna empresa ha entregado reglas (Q-L por confirmar). V2 solo registra el derecho; no
calcula importes (plan 7.4). El derecho es de la empresa donde se trabajo la extra (RE03).
"""

from dataclasses import dataclass
from datetime import date, tzinfo

from Dominio.horarios import _ERRORES_DE_CONFIGURACION, _motivo_de
from Dominio.modelos import ORIGEN_PATRONAL
from Dominio.normatividad import FaltaParametro, resolver_vigente
from Dominio.tiempo import instante_local
from Dominio.tramos_extra import CAT_DOBLE, CAT_PENDIENTE, CAT_TRIPLE

COMIDAS = ("desayuno", "almuerzo", "cena")
_EXTRA = frozenset({CAT_DOBLE, CAT_TRIPLE, CAT_PENDIENTE})


def clave_extra_min(comida: str) -> str:
    return f"alimento_{comida}_extra_min_s"


def clave_inicio_desde(comida: str) -> str:
    return f"alimento_{comida}_extra_inicio_desde_s"


def clave_fin_desde(comida: str) -> str:
    return f"alimento_{comida}_extra_fin_desde_s"


@dataclass(frozen=True)
class DerechoAlimento:
    dia_logico: date
    empresa: str | None
    comida: str
    extra_s: int  # extra confirmada del dia (informativo; sin importes)


@dataclass(frozen=True)
class ResultadoAlimentos:
    derechos: tuple[DerechoAlimento, ...] = ()
    motivos: tuple[str, ...] = ()  # reglas ambiguas/invalidas: esa comida no se marca


def _regla(versiones, clave, dia, empresa, motivos: set[str]):
    """(valor | None, valido): `None` valido = condicion no configurada; invalido = no evaluable."""
    try:
        return resolver_vigente(versiones, clave, dia, ORIGEN_PATRONAL, empresa).valor, True
    except FaltaParametro:
        return None, True
    except _ERRORES_DE_CONFIGURACION as error:
        motivos.add(_motivo_de(error))
        return None, False


def derivar_alimentos(resultado, versiones, zona: tzinfo, *, empresa: str | None = None) -> ResultadoAlimentos:
    """Derechos a alimentos de una semana ya clasificada (`ResultadoExtra`). No modifica el resultado.

    `empresa` es la de respaldo para segmentos sin empresa de origen. `zona` fija la medianoche local.
    """
    por_grupo: dict[tuple, list] = {}
    for c in resultado.segmentos:
        if c.categoria in _EXTRA and c.segmento.intervalo.duracion > 0:
            clave = (c.segmento.dia_logico, c.segmento.empresa or empresa)
            por_grupo.setdefault(clave, []).append(c.segmento.intervalo)
    motivos: set[str] = set()
    derechos = []
    for dia, emp in sorted(por_grupo, key=lambda k: (k[0], k[1] or "")):
        tramos = por_grupo[(dia, emp)]
        extra_s = sum(i.duracion for i in tramos)
        base = instante_local(dia, 0, zona)
        inicio_s, fin_s = min(i.inicio for i in tramos) - base, max(i.fin for i in tramos) - base
        for comida in COMIDAS:
            condiciones = [
                (_regla(versiones, clave_extra_min(comida), dia, emp, motivos), lambda v: extra_s >= v),
                (_regla(versiones, clave_inicio_desde(comida), dia, emp, motivos), lambda v: inicio_s >= v),
                (_regla(versiones, clave_fin_desde(comida), dia, emp, motivos), lambda v: fin_s >= v),
            ]
            configuradas = [(valor, prueba) for (valor, valida), prueba in condiciones if valida and valor is not None]
            todas_validas = all(valida for (_, valida), _ in condiciones)
            if todas_validas and configuradas and all(prueba(valor) for valor, prueba in configuradas):
                derechos.append(DerechoAlimento(dia, emp, comida, extra_s))
    return ResultadoAlimentos(tuple(derechos), tuple(sorted(motivos)))
