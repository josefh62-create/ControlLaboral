# -*- coding: utf-8 -*-
"""Tolerancias de entrada/salida (plan 4.3, TO01-TO07; doc. 03 8.2 paso 12).

Principios:
- TO01: enteros de 0 a 15 minutos inclusive. El 15 es una decision FUNCIONAL del
  propietario (plan 4.3), no un limite legal; por eso vive aqui y no en la semilla legal.
- TO02: por empresa y, si el horario las trae, por horario. Precedencia explicita:
  horario > empresa > general (cada una con su vigencia). No se siembra ningun valor.
- TO03: el limite exacto queda DENTRO (07:10:00 con 10 min); un segundo despues, fuera.
- TO04/TO06: la tolerancia nunca altera el tiempo fisico ni suprime trabajo efectivo:
  aqui solo se CLASIFICA la marca. Magnitudes en segundos enteros, sin redondeo.
- TO05: se conservan por separado la diferencia real y el excedente sobre la tolerancia;
  la politica de retardo (desde el inicio o solo excedente) se elige al reportar.
"""

from dataclasses import dataclass
from datetime import date

from Dominio import normatividad as n
from Dominio.modelos import ORIGEN_PATRONAL, VersionParametro, Vigencia
from Dominio.normatividad import resolver_vigente
from Dominio.tiempo import SEGUNDOS_POR_MINUTO, minutos_a_segundos

TOLERANCIA_MAX_MIN = 15  # decision funcional del propietario (plan 4.3), no legal

ANTICIPADA = "anticipada"
TARDIA = "tardia"
POSTERIOR = "posterior"
_DIRECCIONES = (ANTICIPADA, TARDIA, POSTERIOR)

CLAVES_TOLERANCIA = (
    n.TOL_ENTRADA_ANTICIPADA_S,
    n.TOL_ENTRADA_TARDIA_S,
    n.TOL_SALIDA_ANTICIPADA_S,
    n.TOL_SALIDA_POSTERIOR_S,
    n.TOL_REGRESO_COMIDA_S,
)


class ToleranciaInvalida(ValueError):
    """Valor fuera de TO01 (entero de 0 a 15 minutos); `clave` nombra el parametro si se conoce."""

    def __init__(self, mensaje: str, clave: str | None = None):
        super().__init__(mensaje)
        self.clave = clave


def validar_tolerancia_minutos(valor) -> int:
    """TO01: acepta enteros de 0 a 15; rechaza bool, decimales, texto, negativos y >15."""
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ToleranciaInvalida(f"la tolerancia debe ser entera, no {valor!r}")
    if not 0 <= valor <= TOLERANCIA_MAX_MIN:
        raise ToleranciaInvalida(f"la tolerancia debe estar entre 0 y {TOLERANCIA_MAX_MIN} min: {valor}")
    return valor


def _validar_segundos(segundos) -> int:
    if isinstance(segundos, bool) or not isinstance(segundos, int) or segundos % SEGUNDOS_POR_MINUTO:
        raise ToleranciaInvalida(f"la tolerancia debe ser un numero entero de minutos: {segundos!r}")
    validar_tolerancia_minutos(segundos // SEGUNDOS_POR_MINUTO)
    return segundos


@dataclass(frozen=True)
class Tolerancias:
    """Las cinco tolerancias del plan 4.3, en segundos (multiplos de 60, de 0 a 900)."""

    entrada_anticipada_s: int
    entrada_tardia_s: int
    salida_anticipada_s: int
    salida_posterior_s: int
    regreso_comida_s: int

    def __post_init__(self):
        for valor in (
            self.entrada_anticipada_s, self.entrada_tardia_s, self.salida_anticipada_s,
            self.salida_posterior_s, self.regreso_comida_s,
        ):
            _validar_segundos(valor)

    @classmethod
    def desde_minutos(cls, entrada_anticipada, entrada_tardia, salida_anticipada, salida_posterior, regreso_comida):
        return cls(*(minutos_a_segundos(validar_tolerancia_minutos(v)) for v in (
            entrada_anticipada, entrada_tardia, salida_anticipada, salida_posterior, regreso_comida)))


def version_de_tolerancia(clave: str, minutos, vigencia: Vigencia, fuente: str, empresa: str | None = None):
    """Version patronal de una tolerancia, validada por TO01 antes de existir."""
    if clave not in CLAVES_TOLERANCIA:
        raise ValueError(f"no es una clave de tolerancia: {clave!r}")
    valor = minutos_a_segundos(validar_tolerancia_minutos(minutos))
    return VersionParametro(clave, valor, vigencia, fuente, ORIGEN_PATRONAL, empresa)


def resolver_tolerancias(versiones, fecha: date, empresa: str | None = None, horario: Tolerancias | None = None) -> Tolerancias:
    """Tolerancias vigentes en la fecha trabajada (TO02, P-50).

    Precedencia: las del horario (si trae) > version de la empresa > version general.
    Falta de configuracion -> `FaltaParametro` (el llamador marca provisional, AL12).
    Un valor almacenado fuera de TO01 levanta `ToleranciaInvalida`.
    """
    if horario is not None:
        return horario
    valores = []
    for clave in CLAVES_TOLERANCIA:
        valor = resolver_vigente(versiones, clave, fecha, ORIGEN_PATRONAL, empresa).valor
        try:
            _validar_segundos(valor)
        except ToleranciaInvalida as error:
            raise ToleranciaInvalida(f"{clave}: {error}", clave) from error
        valores.append(valor)
    return Tolerancias(*valores)


@dataclass(frozen=True)
class EvaluacionMarca:
    """TO05: diferencia real y excedente por separado; `precision` es la de la fuente."""

    direccion: str
    diferencia_real_s: int
    excedente_s: int
    dentro_tolerancia: bool
    tolerancia_s: int
    precision: str


def evaluar_marca(direccion: str, esperado_s: int, real_s: int, tolerancia_s: int, precision: str = "segundos") -> EvaluacionMarca:
    """Compara una marca real con el instante esperado del horario, a segundos exactos.

    `ANTICIPADA`: real antes de lo esperado; `TARDIA` y `POSTERIOR`: real despues. Una marca
    del otro lado no es diferencia en ese sentido (0). El limite exacto esta dentro (TO03).
    """
    if direccion not in _DIRECCIONES:
        raise ValueError(f"direccion desconocida: {direccion!r}")
    _validar_segundos(tolerancia_s)
    diferencia = max(0, esperado_s - real_s if direccion == ANTICIPADA else real_s - esperado_s)
    return EvaluacionMarca(
        direccion, diferencia, max(0, diferencia - tolerancia_s), diferencia <= tolerancia_s,
        tolerancia_s, precision,
    )
