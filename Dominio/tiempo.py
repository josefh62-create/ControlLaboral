# -*- coding: utf-8 -*-
"""Tiempo en segundos enteros e intervalos semiabiertos [inicio, fin).

Decision doc. 03 8.4: el motor opera en SEGUNDOS ENTEROS; parametros y horarios
se guardan en minutos y se multiplican x60. Los instantes de un `Intervalo` son
segundos enteros respecto a una referencia comun elegida por quien los crea.

Formato (RE07, plan 4.5): el calculo nunca redondea. Solo la presentacion en
HH:mm reduce precision, y lo hace asi:
- `formatear_hhmm`: redondea HACIA ARRIBA al minuto, de modo que lo mostrado
  nunca sea menor que lo trabajado (07:10:01 se muestra 07:11). Es el formato
  para totales a favor del trabajador.
- `formatear_hhmm_abajo`: trunca; solo para topes y holguras (tiempo que aun
  queda disponible), donde mostrar de mas sobrestimaria el margen.
- `formatear_hhmmss`: exacto, cuando la fuente tiene segundos (TO03, Q02).
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone, tzinfo

SEGUNDOS_POR_MINUTO = 60
SEGUNDOS_POR_HORA = 3600


_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_UN_SEGUNDO = timedelta(seconds=1)


def _entero(valor, nombre: str) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise TypeError(f"{nombre} debe ser entero, no {type(valor).__name__}")
    return valor


def minutos_a_segundos(minutos: int) -> int:
    return _entero(minutos, "minutos") * SEGUNDOS_POR_MINUTO


def horas_a_segundos(horas: int) -> int:
    return _entero(horas, "horas") * SEGUNDOS_POR_HORA


def _no_negativo(segundos: int) -> int:
    _entero(segundos, "segundos")
    if segundos < 0:
        raise ValueError("el tiempo no puede ser negativo")
    return segundos


def formatear_hhmmss(segundos: int) -> str:
    s = _no_negativo(segundos)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def formatear_hhmm(segundos: int) -> str:
    """HH:mm redondeando hacia arriba (nunca en perjuicio del trabajador)."""
    s = _no_negativo(segundos)
    minutos = -(-s // SEGUNDOS_POR_MINUTO)
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def formatear_hhmm_abajo(segundos: int) -> str:
    """HH:mm truncando; solo para topes y holguras."""
    minutos = _no_negativo(segundos) // SEGUNDOS_POR_MINUTO
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


@dataclass(frozen=True)
class Intervalo:
    """Intervalo semiabierto [inicio, fin) en segundos enteros."""

    inicio: int
    fin: int

    def __post_init__(self):
        _entero(self.inicio, "inicio")
        _entero(self.fin, "fin")
        if self.fin < self.inicio:
            raise ValueError("fin no puede ser anterior a inicio")

    @property
    def duracion(self) -> int:
        return self.fin - self.inicio

    def contiene(self, instante: int) -> bool:
        return self.inicio <= instante < self.fin

    def interseccion(self, otro: "Intervalo") -> "Intervalo | None":
        """Parte comun, o None si no comparten ningun segundo."""
        inicio, fin = max(self.inicio, otro.inicio), min(self.fin, otro.fin)
        return Intervalo(inicio, fin) if inicio < fin else None

    def se_traslapa(self, otro: "Intervalo") -> bool:
        return self.interseccion(otro) is not None

    def dividir(self, instante: int) -> "tuple[Intervalo, ...]":
        """Divide exactamente en `instante`; fuera del interior devuelve el mismo intervalo."""
        if not self.inicio < instante < self.fin:
            return (self,)
        return (Intervalo(self.inicio, instante), Intervalo(instante, self.fin))


# --- Instante (epoch UTC en segundos) <-> fecha local de una zona ---------------------
# El dominio no tiene reloj: estas funciones solo convierten valores que entrega quien llama.

def a_segundos_epoch(instante: datetime) -> int:
    """Segundos enteros de epoch UTC de un datetime CON zona; trunca fracciones."""
    if not isinstance(instante, datetime) or instante.utcoffset() is None:
        raise ValueError("el instante debe ser un datetime con zona horaria")
    return (instante - _EPOCH) // _UN_SEGUNDO


def fecha_local(segundos: int, zona: tzinfo) -> date:
    """Fecha calendario, en `zona`, del instante dado en segundos de epoch."""
    return (_EPOCH + timedelta(seconds=_entero(segundos, "segundos"))).astimezone(zona).date()


def instante_local(fecha: date, segundos_del_dia: int, zona: tzinfo) -> int:
    """Epoch de la hora de pared `fecha` 00:00 + `segundos_del_dia` en `zona`.

    Aritmetica de hora de pared: 25 h desde el lunes 00:00 es el martes 01:00. Sirve para
    horarios (turnos nocturnos) y medianoches locales.
    """
    base = datetime(fecha.year, fecha.month, fecha.day, tzinfo=zona)
    return a_segundos_epoch(base + timedelta(seconds=_entero(segundos_del_dia, "segundos_del_dia")))
