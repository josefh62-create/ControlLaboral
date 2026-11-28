# -*- coding: utf-8 -*-
"""Alertas del motor (plan 4.4, doc. 03 8.2 paso 12): catalogo unico AL01-AL14, tipo comun y
clave de deduplicacion (P-48, parte pura).

- El catalogo es la unica fuente de codigo, nombre, nivel (texto literal del plan), severidades
  posibles y bloqueo de cierre. Los modulos de T1-T5 solo conservan el codigo (`"AL12"`...).
- `Alerta` es el valor comun. Su identidad (clave de deduplicacion) es trabajador + empresa + periodo
  + dia logico + regla + sujeto + version: reimportar o recalcular los mismos datos con las mismas
  versiones da la misma clave y no genera otro aviso. Severidad y detalle NO forman parte de la
  identidad (una alerta que escala conserva su clave; el `sujeto` distingue alcanzado vs superado).
- Nada aqui calcula minutos: solo describe, normaliza y deduplica lo que ya produjeron T2-T5.
- Persistencia, reconocimiento y destinatarios son de E3/E4; aqui no hay E/S.
"""

import json
from dataclasses import dataclass
from datetime import date

from Dominio.modelos import Vigencia

# Severidades normalizadas a partir de los niveles del plan 4.4 (ordenadas de menor a mayor para
# desempatar duplicadas; el orden no cambia el calculo, solo cual duplicada se conserva).
SEVERIDADES = (
    "informativo", "configuracion", "preventivo", "revision", "calculo_pendiente", "advertencia", "critico",
)
_RANGO = {s: i for i, s in enumerate(SEVERIDADES)}


@dataclass(frozen=True)
class DefinicionAlerta:
    codigo: str
    nombre: str
    nivel: str  # texto literal de la columna "Nivel" del plan 4.4
    severidades: tuple[str, ...]  # severidades que una instancia puede llevar
    bloquea_cierre: bool = False  # solo lo no resuelto bloquea el calculo DEFINITIVO (NL04, RE02)
    nota: str = ""


def _d(codigo, nombre, nivel, severidades, bloquea_cierre=False, nota=""):
    return DefinicionAlerta(codigo, nombre, nivel, tuple(severidades), bloquea_cierre, nota)


_DEFINICIONES = (
    _d("AL01", "Próximo a límite ordinario diario/semanal", "Preventivo", ("preventivo",)),
    _d("AL02", "Tiempo extraordinario detectado", "Informativo/revisión", ("informativo", "revision")),
    _d("AL03", "Próximo a tope art. 66 semanal", "Preventivo", ("preventivo",)),
    _d("AL04", "Tope art. 66 alcanzado / superado", "Advertencia diferenciada", ("advertencia",)),
    _d("AL05", "Distribución art. 66 superior a 4 h/día o 4 días/semana", "Crítico/revisión legal",
       ("critico", "revision")),
    _d("AL06", "Tramo adicional art. 68 próximo a / superior a 4 h semanales", "Preventivo/crítico",
       ("preventivo", "critico")),
    _d("AL07", "Tiempo total diario próximo a / superior a 12 h", "Preventivo/crítico",
       ("preventivo", "critico")),
    _d("AL08", "Descanso semanal no acreditado", "Crítico/revisión", ("critico", "revision")),
    _d("AL09", "Horario futuro incompatible con reforma", "Preventivo", ("preventivo",)),
    _d("AL10", "Checada incompleta, duplicada o inconsistente", "Revisión", ("revision",)),
    _d("AL11", "Exceso de umbral interno patronal", "Advertencia administrativa", ("advertencia",),
       nota="el umbral y la magnitud que compara son configuracion patronal (pregunta abierta Q-K)"),
    _d("AL12", "Horario/norma ausente o transición no resuelta", "Cálculo pendiente", ("calculo_pendiente",),
       bloquea_cierre=True),
    _d("AL13", "Prohibición para menores de 18", "Crítico", ("critico",)),
    _d("AL14", "Tipo de jornada declarado no coincide con el art. 60", "Configuración", ("configuracion",),
       nota="no bloquea (decisión del propietario, 27/11/2026)"),
    # Fuera de AL01-AL14: alerta del plan 5.2 que ya producen T3/T5 y que el plan no clasifica.
    _d("HO03", "Horario incompatible con el tope legal", "Sin nivel en el plan (5.2)", ("revision",),
       nota="plan 5.2: remanente asignado a los ultimos minutos programados; RH debe corregir el horario"),
)

CATALOGO: dict[str, DefinicionAlerta] = {d.codigo: d for d in _DEFINICIONES}
ALERTAS = tuple(c for c in CATALOGO if c.startswith("AL"))

AL01, AL02, AL03, AL04, AL05, AL06, AL07, AL08, AL09, AL10, AL11, AL12, AL13, AL14 = ALERTAS
HO03 = "HO03"


def definicion(codigo: str) -> DefinicionAlerta:
    """Definicion del catalogo; `KeyError` si el codigo no existe (no se inventan alertas)."""
    return CATALOGO[codigo]


@dataclass(frozen=True)
class Alerta:
    """Una alerta concreta. Identidad = `clave_deduplicacion`; `severidad` y `detalle` son informativos."""

    codigo: str
    trabajador: str
    empresa: str
    severidad: str
    periodo: Vigencia | None = None  # semana laboral (o periodo) evaluado
    dia_logico: date | None = None  # None: alerta de la semana completa
    sujeto: str = ""  # a que se refiere dentro de la regla (aviso, tipo de incidencia, comida...)
    version: str = ""  # version de norma/politica con la que se evaluo (plan 4.4: "regla y version")
    detalle: str = ""

    def __post_init__(self):
        try:
            definido = CATALOGO[self.codigo]
        except KeyError:
            raise ValueError(f"alerta fuera del catalogo: {self.codigo!r}") from None
        if self.severidad not in definido.severidades:
            raise ValueError(f"{self.codigo} no admite severidad {self.severidad!r}: {definido.severidades}")

    @property
    def bloquea_cierre(self) -> bool:
        return CATALOGO[self.codigo].bloquea_cierre


def _iso(valor: date | None) -> str | None:
    return None if valor is None else valor.isoformat()


def clave_deduplicacion(alerta: Alerta) -> str:
    """Clave determinista: JSON canonico de (regla, trabajador, empresa, periodo, dia, sujeto, version).

    Sin separadores ambiguos y sin depender de orden de llegada, severidad ni detalle (P-48).
    """
    periodo = None if alerta.periodo is None else [_iso(alerta.periodo.desde), _iso(alerta.periodo.hasta)]
    return json.dumps(
        [alerta.codigo, alerta.trabajador, alerta.empresa, periodo, _iso(alerta.dia_logico), alerta.sujeto,
         alerta.version],
        ensure_ascii=True, separators=(",", ":"),
    )


def _preferida(a: Alerta):
    return (_RANGO[a.severidad], a.detalle, a.severidad)


def consolidar(alertas) -> tuple[Alerta, ...]:
    """Una alerta por clave (la de mayor severidad; empate por detalle), ordenadas por clave. Nunca oculta una clave."""
    elegidas: dict[str, Alerta] = {}
    for a in alertas:
        k = clave_deduplicacion(a)
        if k not in elegidas or _preferida(a) > _preferida(elegidas[k]):
            elegidas[k] = a
    return tuple(elegidas[k] for k in sorted(elegidas))
