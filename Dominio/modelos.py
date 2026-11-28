# -*- coding: utf-8 -*-
"""Dataclasses inmutables base del dominio (solo lo que T1 necesita)."""

from dataclasses import dataclass
from datetime import date

ORIGEN_LEGAL = "legal"
ORIGEN_PATRONAL = "patronal"


@dataclass(frozen=True)
class Vigencia:
    """Rango de fechas semiabierto [desde, hasta); `hasta=None` = sin fin."""

    desde: date
    hasta: date | None = None

    def __post_init__(self):
        if self.hasta is not None and self.hasta <= self.desde:
            raise ValueError("hasta debe ser posterior a desde")

    def contiene(self, fecha: date) -> bool:
        return self.desde <= fecha and (self.hasta is None or fecha < self.hasta)


@dataclass(frozen=True)
class VersionParametro:
    """Un valor de parametro con su vigencia y fundamento.

    `valor` es entero: segundos, cantidad (dias) u hora del dia en segundos.
    `origen` separa el limite legal del interno patronal (NL05).
    """

    clave: str
    valor: int
    vigencia: Vigencia
    fuente: str
    origen: str = ORIGEN_LEGAL
