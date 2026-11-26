# -*- coding: utf-8 -*-
"""Estrategias por regimen (NL07, doc. 03 8.5): topes, prohibiciones y alertas.

Tabla de DATOS mas funciones pequenas. Los valores legales (topes, hora limite,
periodos) no viven aqui: cada regimen solo nombra la CLAVE del parametro y el
valor se obtiene con `resolver_vigente` segun la fecha trabajada.
"""

from dataclasses import dataclass
from datetime import date

from Dominio import normatividad as n
from Dominio.normatividad import resolver_vigente

EXTRA_PROHIBIDA = "extra_prohibida"
DOMINGO_PROHIBIDO = "domingo_prohibido"
DESCANSO_OBLIGATORIO_PROHIBIDO = "descanso_obligatorio_prohibido"
NOCTURNO_MENOR_PROHIBIDO = "nocturno_menor_prohibido"

# Alerta por infraccion. Solo AL02 (tiempo extraordinario detectado) corresponde
# con claridad; el plan 4.4 no define un codigo AL para las demas prohibiciones
# de menores: quedan en None hasta que el propietario lo decida (no se inventa).
_ALERTA = {
    EXTRA_PROHIBIDA: "AL02",
    DOMINGO_PROHIBIDO: None,
    DESCANSO_OBLIGATORIO_PROHIBIDO: None,
    NOCTURNO_MENOR_PROHIBIDO: None,
}
_FUNDAMENTO = {
    EXTRA_PROHIBIDA: "LFT art. 178",
    DOMINGO_PROHIBIDO: "LFT art. 178",
    DESCANSO_OBLIGATORIO_PROHIBIDO: "LFT art. 178",
    NOCTURNO_MENOR_PROHIBIDO: "LFT arts. 175 I y 176",
}


class TrabajoMenorProhibido(ValueError):
    """Menor de 15 anos: trabajo prohibido (LFT art. 22 Bis)."""


@dataclass(frozen=True)
class Regimen:
    codigo: str
    descripcion: str
    clave_tope_diario: str | None  # None: sin tope legal propio en las fuentes
    permite_extra: bool = True
    permite_domingo: bool = True
    permite_descanso_obligatorio: bool = True
    clave_hora_limite: str | None = None
    clave_periodo_max: str | None = None
    clave_reposo_min: str | None = None


_MENOR = dict(
    permite_extra=False,
    permite_domingo=False,
    permite_descanso_obligatorio=False,
    clave_hora_limite=n.MENOR_HORA_LIMITE_S,
)

REGIMENES: dict[str, Regimen] = {
    reg.codigo: reg
    for reg in (
        Regimen("diurna", "General diurna (art. 61)", n.JORNADA_DIURNA_S),
        Regimen("nocturna", "General nocturna (art. 61)", n.JORNADA_NOCTURNA_S),
        Regimen("mixta", "General mixta (art. 61)", n.JORNADA_MIXTA_S),
        Regimen("parcial", "Parcial o reducida: el tope sale del contrato/horario", None),
        Regimen(
            "menor_15_16",
            "Mayor de 15 y menor de 16 (art. 177)",
            n.MENOR16_JORNADA_S,
            clave_periodo_max=n.MENOR16_PERIODO_MAX_S,
            clave_reposo_min=n.MENOR16_REPOSO_MIN_S,
            **_MENOR,
        ),
        Regimen("menor_16_18", "Mayor de 16 y menor de 18 (arts. 175, 178)", n.JORNADA_DIURNA_S, **_MENOR),
    )
}


def obtener_regimen(codigo: str) -> Regimen:
    return REGIMENES[codigo]


def regimen_por_edad(edad: int) -> Regimen | None:
    """Regimen de menores segun anos cumplidos; None para mayores de edad.

    Menor de 15: trabajo prohibido (art. 22 Bis). El texto del art. 22 dice
    «mayores de quince»; aqui se toman 15 anos cumplidos (a validar con el asesor).
    """
    if edad < 15:
        raise TrabajoMenorProhibido(f"menor de 15 anos ({edad}): trabajo prohibido (art. 22 Bis)")
    if edad < 16:
        return REGIMENES["menor_15_16"]
    if edad < 18:
        return REGIMENES["menor_16_18"]
    return None


def _valor(versiones, clave: str | None, fecha: date) -> int | None:
    return None if clave is None else resolver_vigente(versiones, clave, fecha).valor


def tope_diario_s(regimen: Regimen, versiones, fecha: date) -> int | None:
    return _valor(versiones, regimen.clave_tope_diario, fecha)


def hora_limite_s(regimen: Regimen, versiones, fecha: date) -> int | None:
    """Hora del dia (segundos desde 00:00) despues de la cual no se puede trabajar."""
    return _valor(versiones, regimen.clave_hora_limite, fecha)


def limites_periodo(regimen: Regimen, versiones, fecha: date) -> tuple[int, int] | None:
    """(duracion maxima de un periodo, reposo minimo entre periodos), si el regimen los fija."""
    if regimen.clave_periodo_max is None:
        return None
    return (
        _valor(versiones, regimen.clave_periodo_max, fecha),
        _valor(versiones, regimen.clave_reposo_min, fecha),
    )


@dataclass(frozen=True)
class Infraccion:
    codigo: str
    alerta: str | None
    fundamento: str


def _infraccion(codigo: str) -> Infraccion:
    return Infraccion(codigo, _ALERTA[codigo], _FUNDAMENTO[codigo])


def evaluar_prohibiciones(
    regimen: Regimen,
    versiones,
    fecha: date,
    *,
    tiempo_extra_s: int = 0,
    es_domingo: bool = False,
    es_descanso_obligatorio: bool = False,
    fin_del_dia_s: int | None = None,
) -> tuple[Infraccion, ...]:
    """Prohibiciones del regimen que el dia evaluado viola (vacio si ninguna)."""
    encontradas = []
    if tiempo_extra_s > 0 and not regimen.permite_extra:
        encontradas.append(EXTRA_PROHIBIDA)
    if es_domingo and not regimen.permite_domingo:
        encontradas.append(DOMINGO_PROHIBIDO)
    if es_descanso_obligatorio and not regimen.permite_descanso_obligatorio:
        encontradas.append(DESCANSO_OBLIGATORIO_PROHIBIDO)
    limite = hora_limite_s(regimen, versiones, fecha)
    if limite is not None and fin_del_dia_s is not None and fin_del_dia_s > limite:
        encontradas.append(NOCTURNO_MENOR_PROHIBIDO)
    return tuple(_infraccion(c) for c in encontradas)


def clasificar_jornada(segundos_nocturnos: int, segundos_diurnos: int, versiones, fecha: date) -> str:
    """Art. 60: con >= 3 h 30 nocturnas la jornada mixta se reputa nocturna.

    Todo en periodo nocturno es nocturna; todo diurno es diurna.
    """
    if segundos_nocturnos == 0:
        return "diurna"
    if segundos_diurnos == 0:
        return "nocturna"
    umbral = resolver_vigente(versiones, n.UMBRAL_NOCTURNA_S, fecha).valor
    return "nocturna" if segundos_nocturnos >= umbral else "mixta"
