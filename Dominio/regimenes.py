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

# Toda prohibicion de menores dispara AL13 "Prohibicion para menores" (critico;
# decision del propietario 26/11/2026, plan 4.4). El tiempo extra de un menor es
# AL13 (prohibicion), no AL02.
_ALERTA = {
    EXTRA_PROHIBIDA: "AL13",
    DOMINGO_PROHIBIDO: "AL13",
    DESCANSO_OBLIGATORIO_PROHIBIDO: "AL13",
    NOCTURNO_MENOR_PROHIBIDO: "AL13",
}
_FUNDAMENTO = {
    EXTRA_PROHIBIDA: "LFT art. 178",
    DOMINGO_PROHIBIDO: "LFT art. 178",
    DESCANSO_OBLIGATORIO_PROHIBIDO: "LFT art. 178",
    NOCTURNO_MENOR_PROHIBIDO: "LFT arts. 175 I y 176",
}


MAX_FIN_DEL_DIA_S = 2 * 86_400  # cota para detectar valores no interpretables


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
    supuesto: str | None = None  # valor que la LFT no fija y se adopta por supuesto


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
        Regimen(
            "menor_16_18",
            "Mayor de 16 y menor de 18 (arts. 175, 178)",
            n.JORNADA_DIURNA_S,
            supuesto=(
                "Supuesto: la LFT no fija un tope diario especifico para 16-18; "
                "se aplica el tope general de 8 h (validar con el asesor laboral)"
            ),
            **_MENOR,
        ),
    )
}


def obtener_regimen(codigo: str) -> Regimen:
    return REGIMENES[codigo]


def regimen_por_edad(edad: int, versiones, fecha: date) -> Regimen | None:
    """Regimen de menores segun anos cumplidos; None para mayores de edad.

    Los umbrales (15/16/18) salen de la semilla versionada. Menor del minimo:
    trabajo prohibido (art. 22 Bis). El art. 22 dice «mayores de quince»; se
    toman 15 anos cumplidos (a validar con el asesor).
    """
    minima = resolver_vigente(versiones, n.EDAD_MINIMA_TRABAJO, fecha).valor
    fin_15_16 = resolver_vigente(versiones, n.EDAD_FIN_REGIMEN_15_16, fecha).valor
    mayoria = resolver_vigente(versiones, n.EDAD_MAYORIA, fecha).valor
    if edad < minima:
        raise TrabajoMenorProhibido(f"menor de {minima} anos ({edad}): trabajo prohibido (art. 22 Bis)")
    if edad < fin_15_16:
        return REGIMENES["menor_15_16"]
    if edad < mayoria:
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
    """Prohibiciones del regimen que el dia evaluado viola (vacio si ninguna).

    `fin_del_dia_s` son segundos desde el INICIO DEL DIA LOGICO: un turno que
    termina a las 00:30 del dia siguiente se expresa como 86400 + 1800. Se
    admite terminar exactamente en la hora limite. Un valor que no sea entero o
    quede fuera de 0..172800 (48 h) no es interpretable y levanta ValueError.
    """
    if fin_del_dia_s is not None and (
        isinstance(fin_del_dia_s, bool)
        or not isinstance(fin_del_dia_s, int)
        or not 0 <= fin_del_dia_s <= MAX_FIN_DEL_DIA_S
    ):
        raise ValueError(f"fin_del_dia_s no interpretable: {fin_del_dia_s!r}")
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

    Todo en periodo nocturno es nocturna; todo diurno es diurna. Cantidades
    negativas o una jornada sin tiempo (0 y 0) levantan ValueError.
    """
    if segundos_nocturnos < 0 or segundos_diurnos < 0:
        raise ValueError("los segundos no pueden ser negativos")
    if segundos_nocturnos == 0 and segundos_diurnos == 0:
        raise ValueError("jornada sin tiempo: no hay nada que clasificar")
    if segundos_nocturnos == 0:
        return "diurna"
    if segundos_diurnos == 0:
        return "nocturna"
    umbral = resolver_vigente(versiones, n.UMBRAL_NOCTURNA_S, fecha).valor
    return "nocturna" if segundos_nocturnos >= umbral else "mixta"
