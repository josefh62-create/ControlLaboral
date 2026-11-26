# -*- coding: utf-8 -*-
"""Checadas: orden por instante y marcado SIN descartar (plan 5.1 pasos 2-3, RE05).

Decision doc. 03 8.2 pasos 1-2: V1 descartaba la segunda checada cercana (R006);
V2 conserva todas y solo las MARCA. Nada de lo que entra deja de salir.

Convenciones:
- El instante lleva zona (`datetime` consciente); internamente son segundos enteros
  de epoch UTC (doc. 03 8.4). Las fracciones de segundo se truncan.
- Un duplicado se evalua solo dentro del MISMO reloj y con el mismo sentido declarado:
  salida en un reloj y entrada en otro a pocos minutos es un traslado, no un duplicado.
- La ventana (por empresa de la checada) se mide contra la ultima checada CONSERVADA
  (sin arrastre en cadena).
- Sin sentido declarado, una checada cercana solo se marca duplicada si quitarla deja
  consistente la paridad entrada/salida del dia (si no, puede ser la salida y regreso
  de una comida y marcarla romperia el emparejamiento); la repeticion exacta del mismo
  instante en el mismo reloj siempre es duplicado (lote importado dos veces, P-31).
- `futura` y `desfase` solo se marcan si quien llama aporta lo necesario: el dominio
  no tiene reloj propio ni umbral documentado de desfase.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from Dominio.modelos import ORIGEN_PATRONAL
from Dominio.normatividad import VENTANA_DUPLICADOS_S, resolver_vigente

POSIBLE_DUPLICADO = "posible_duplicado"
FUTURA = "futura"
DESFASE = "desfase"

ENTRADA = "entrada"
SALIDA = "salida"
_SENTIDOS = (None, ENTRADA, SALIDA)

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_UN_SEGUNDO = timedelta(seconds=1)


def _segundos(instante: datetime) -> int:
    return (instante - _EPOCH) // _UN_SEGUNDO


def _exigir_zona(instante, nombre: str) -> None:
    if not isinstance(instante, datetime) or instante.utcoffset() is None:
        raise ValueError(f"{nombre} debe ser un datetime con zona horaria")


@dataclass(frozen=True)
class Checada:
    """Evento original del reloj, con su reloj y empresa de origen.

    `sentido` es la semantica del dispositivo cuando la declara (None si no).
    `desfase_s` es el desfase del reloj medido por quien llama contra una referencia
    confiable (positivo = el reloj adelanta); el dominio no lo estima.
    """

    id: str
    instante: datetime
    reloj: str
    empresa: str
    sentido: str | None = None
    desfase_s: int | None = None

    def __post_init__(self):
        _exigir_zona(self.instante, "instante")
        if self.sentido not in _SENTIDOS:
            raise ValueError(f"sentido desconocido: {self.sentido!r}")

    @property
    def instante_s(self) -> int:
        return _segundos(self.instante)

    @property
    def fecha_local(self) -> date:
        """Fecha calendario en la zona propia de la checada (fecha trabajada candidata)."""
        return self.instante.date()


@dataclass(frozen=True)
class ChecadaMarcada:
    checada: Checada
    marcas: frozenset[str] = field(default_factory=frozenset)


def clave_orden(c: Checada):
    # Orden total y determinista: el instante manda; el resto solo desempata para que
    # cualquier permutacion de la entrada produzca exactamente la misma salida (P-32).
    return (
        c.instante_s, c.instante.microsecond, c.reloj, c.empresa, c.id,
        c.sentido or "", str(c.instante.tzinfo), c.desfase_s if c.desfase_s is not None else 0,
    )


def ordenar_checadas(checadas) -> tuple[Checada, ...]:
    """Tupla ordenada por instante real (no por importacion); no descarta ninguna (P-32)."""
    return tuple(sorted(checadas, key=clave_orden))


def marcar_checadas(
    checadas,
    versiones,
    *,
    instante_referencia: datetime | None = None,
    umbral_desfase_s: int | None = None,
) -> tuple[ChecadaMarcada, ...]:
    """Todas las checadas, ordenadas, cada una con sus marcas; ninguna se elimina.

    `versiones`: politica patronal (ventana de duplicados, via `resolver_vigente`).
    `instante_referencia`: si se entrega, lo posterior a el se marca `futura`.
    `umbral_desfase_s`: si se entrega, |desfase_s| mayor se marca `desfase`.
    """
    if instante_referencia is not None:
        _exigir_zona(instante_referencia, "instante_referencia")
        referencia_s = _segundos(instante_referencia)
    ordenadas = ordenar_checadas(checadas)
    ultima_conservada: dict[tuple[str, str | None], int] = {}
    definitivos: set[int] = set()  # posiciones en `ordenadas`
    tentativos: list[int] = []
    for pos, c in enumerate(ordenadas):
        clave = (c.reloj, c.sentido)
        ventana = resolver_vigente(
            versiones, VENTANA_DUPLICADOS_S, c.fecha_local, ORIGEN_PATRONAL, c.empresa
        ).valor
        previa = ultima_conservada.get(clave)
        if previa is None or c.instante_s - previa > ventana:
            ultima_conservada[clave] = c.instante_s
        elif c.sentido is not None or c.instante_s == previa:
            definitivos.add(pos)  # mismo rol declarado, o repeticion exacta
        else:
            tentativos.append(pos)
    # Sin sentido declarado, solo es duplicado si quitarlo deja consistente la paridad
    # entrada/salida del dia (si no, podria ser la salida/regreso de una comida). Los
    # candidatos de cada fecha se aceptan juntos o ninguno (conservador).
    for fecha in {ordenadas[pos].fecha_local for pos in tentativos}:
        del_dia = [p for p, c in enumerate(ordenadas) if c.fecha_local == fecha and p not in definitivos]
        candidatos = [p for p in tentativos if ordenadas[p].fecha_local == fecha]
        if (len(del_dia) - len(candidatos)) % 2 == 0:
            definitivos.update(candidatos)
    resultado = []
    for pos, c in enumerate(ordenadas):
        marcas = set()
        if pos in definitivos:
            marcas.add(POSIBLE_DUPLICADO)
        if instante_referencia is not None and c.instante_s > referencia_s:
            marcas.add(FUTURA)
        if (
            umbral_desfase_s is not None
            and c.desfase_s is not None
            and abs(c.desfase_s) > umbral_desfase_s
        ):
            marcas.add(DESFASE)
        resultado.append(ChecadaMarcada(c, frozenset(marcas)))
    return tuple(resultado)
