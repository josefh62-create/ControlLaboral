# -*- coding: utf-8 -*-
"""Resolucion de parametros versionados por fecha trabajada (doc. 03 8.3, NL02)."""

from dataclasses import dataclass
from datetime import date

from Dominio.modelos import ORIGEN_LEGAL, VersionParametro, Vigencia
from Dominio.tiempo import horas_a_segundos, minutos_a_segundos


class FaltaParametro(LookupError):
    """Ninguna version vigente para la fecha: el calculo queda provisional (NL04, AL12)."""

    def __init__(self, clave: str, fecha: date):
        super().__init__(f"sin version vigente de {clave!r} el {fecha}")
        self.clave = clave
        self.fecha = fecha


class ParametroAmbiguo(ValueError):
    """Mas de una version vigente para la fecha: error de configuracion (NL02)."""

    def __init__(self, clave: str, fecha: date, cantidad: int):
        super().__init__(f"{cantidad} versiones vigentes de {clave!r} el {fecha}")
        self.clave = clave
        self.fecha = fecha
        self.cantidad = cantidad


def resolver_vigente(
    versiones, clave: str, fecha_trabajada: date, origen: str = ORIGEN_LEGAL
) -> VersionParametro:
    """Exactamente una version de `clave`/`origen` cuya vigencia contiene la fecha.

    La fecha es la fecha TRABAJADA del segmento, no la de consulta (P-36, P-40, P-50).
    """
    candidatas = [
        v
        for v in versiones
        if v.clave == clave and v.origen == origen and v.vigencia.contiene(fecha_trabajada)
    ]
    if not candidatas:
        raise FaltaParametro(clave, fecha_trabajada)
    if len(candidatas) > 1:
        raise ParametroAmbiguo(clave, fecha_trabajada, len(candidatas))
    return candidatas[0]


@dataclass(frozen=True)
class ProblemaVigencia:
    """Traslape o hueco entre versiones consecutivas de una misma clave/origen."""

    tipo: str  # "traslape" | "hueco"
    clave: str
    origen: str
    desde: date
    hasta: date


def _problemas_de_un_grupo(grupo: list[VersionParametro]) -> list[ProblemaVigencia]:
    clave, origen = grupo[0].clave, grupo[0].origen
    grupo = sorted(grupo, key=lambda v: v.vigencia.desde)
    problemas = []
    for i, a in enumerate(grupo):
        for b in grupo[i + 1 :]:
            fin = a.vigencia.hasta
            if fin is None or b.vigencia.desde < fin:
                finales = [x for x in (fin, b.vigencia.hasta) if x is not None]
                termina = min(finales) if finales else date.max  # ambas abiertas: sin fin
                problemas.append(
                    ProblemaVigencia("traslape", clave, origen, b.vigencia.desde, termina)
                )
    alcance = grupo[0].vigencia.hasta
    for v in grupo[1:]:
        if alcance is not None and alcance < v.vigencia.desde:
            problemas.append(ProblemaVigencia("hueco", clave, origen, alcance, v.vigencia.desde))
        fin = v.vigencia.hasta
        alcance = None if (alcance is None or fin is None) else max(alcance, fin)
    return problemas


def validar_versiones(versiones) -> tuple[ProblemaVigencia, ...]:
    """Detecta traslapes y huecos por (clave, origen); no altera la lista (NL02)."""
    grupos: dict[tuple[str, str], list[VersionParametro]] = {}
    for v in versiones:
        grupos.setdefault((v.clave, v.origen), []).append(v)
    problemas = []
    for clave_origen in sorted(grupos):
        problemas += _problemas_de_un_grupo(grupos[clave_origen])
    return tuple(problemas)


# ---------------------------------------------------------------------------
# Semilla legal (DATOS, no logica). Cada version cita su fundamento (doc. 00).
# Valores en segundos, salvo ART66_DIAS_SEMANA (cantidad de dias).
# NL05: son limites LEGALES (origen "legal"); los internos patronales viven
# aparte con origen "patronal". NL06: art. 66 y art. 68 son claves distintas.
# ---------------------------------------------------------------------------

ORDINARIA_SEMANAL_S = "ordinaria_semanal_s"
ART66_SEMANAL_S = "art66_semanal_s"
ART66_DIARIO_S = "art66_diario_s"
ART66_DIAS_SEMANA = "art66_dias_semana"
ART68_SEMANAL_S = "art68_semanal_s"
TOTAL_DIARIO_MAX_S = "total_diario_max_s"
JORNADA_DIURNA_S = "jornada_diurna_s"
JORNADA_NOCTURNA_S = "jornada_nocturna_s"
JORNADA_MIXTA_S = "jornada_mixta_s"
NOCTURNO_INICIO_S = "nocturno_inicio_s"
NOCTURNO_FIN_S = "nocturno_fin_s"
UMBRAL_NOCTURNA_S = "umbral_nocturna_s"
DESCANSO_CONTINUA_MIN_S = "descanso_continua_min_s"
MENOR16_JORNADA_S = "menor16_jornada_s"
MENOR16_PERIODO_MAX_S = "menor16_periodo_max_s"
MENOR16_REPOSO_MIN_S = "menor16_reposo_min_s"
MENOR_HORA_LIMITE_S = "menor_hora_limite_s"

# Alerta que dispara rebasar cada limite (plan 4.4); art. 66 y 68 distintos (NL06).
ALERTA_POR_LIMITE = {
    ORDINARIA_SEMANAL_S: "AL01",
    ART66_SEMANAL_S: "AL04",
    ART66_DIARIO_S: "AL05",
    ART66_DIAS_SEMANA: "AL05",
    ART68_SEMANAL_S: "AL06",
    TOTAL_DIARIO_MAX_S: "AL07",
}

_DEC = "Decreto DOF 01/05/2026"
_INICIO_DECRETO = date(2026, 5, 1)  # transitorio primero: entra en vigor el 01/05/2026
_D2026 = date(2026, 1, 1)
_H = horas_a_segundos
_M = minutos_a_segundos


def _anual(clave, valores_por_anio, fuente):
    """Versiones por anio calendario; el ultimo anio queda abierto (hasta nueva reforma)."""
    anios = sorted(valores_por_anio)
    return tuple(
        VersionParametro(
            clave,
            valores_por_anio[a],
            Vigencia(date(a, 1, 1), date(a + 1, 1, 1) if a != anios[-1] else None),
            fuente,
        )
        for a in anios
    )


def _v(clave, valor, desde, hasta, fuente):
    return VersionParametro(clave, valor, Vigencia(desde, hasta), fuente)


SEMILLA_LEGAL: tuple[VersionParametro, ...] = (
    # Art. 59 + transitorio segundo: 48, 46, 44, 42, 40 "a partir del 1 de enero".
    *_anual(
        ORDINARIA_SEMANAL_S,
        {2026: _H(48), 2027: _H(46), 2028: _H(44), 2029: _H(42), 2030: _H(40)},
        f"{_DEC}, art. 59 y transitorio segundo",
    ),
    # Transitorio cuarto: 9, 9, 10, 11, 12 h (tope semanal art. 66).
    *_anual(
        ART66_SEMANAL_S,
        {2026: _H(9), 2027: _H(9), 2028: _H(10), 2029: _H(11), 2030: _H(12)},
        f"{_DEC}, art. 66 y transitorio cuarto",
    ),
    # Distribucion art. 66: ene-abr 2026 norma anterior (3 h diarias, 3 veces por semana;
    # plan 2.1 "Vigencias"); desde el 01/05/2026, 4 h diarias en maximo 4 dias.
    _v(ART66_DIARIO_S, _H(3), _D2026, _INICIO_DECRETO, "LFT art. 66 anterior al decreto (plan 2.1)"),
    _v(ART66_DIARIO_S, _H(4), _INICIO_DECRETO, None, f"{_DEC}, art. 66 y transitorio primero"),
    _v(ART66_DIAS_SEMANA, 3, _D2026, _INICIO_DECRETO, "LFT art. 66 anterior al decreto (plan 2.1)"),
    _v(ART66_DIAS_SEMANA, 4, _INICIO_DECRETO, None, f"{_DEC}, art. 66 y transitorio primero"),
    # Art. 68 reformado: 4 h semanales adicionales (no gradual) y 12 h diarias en total.
    # No hay valor documentado para el art. 68 anterior: antes del 01/05/2026 no hay version.
    _v(ART68_SEMANAL_S, _H(4), _INICIO_DECRETO, None, f"{_DEC}, art. 68"),
    _v(TOTAL_DIARIO_MAX_S, _H(12), _INICIO_DECRETO, None, f"{_DEC}, art. 68"),
    # Art. 61: 8 h diurna, 7 nocturna, 7:30 mixta (plan 2.1: 480/420/450 min).
    _v(JORNADA_DIURNA_S, _M(480), _D2026, None, f"{_DEC}, art. 61"),
    _v(JORNADA_NOCTURNA_S, _M(420), _D2026, None, f"{_DEC}, art. 61"),
    _v(JORNADA_MIXTA_S, _M(450), _D2026, None, f"{_DEC}, art. 61"),
    # Art. 60: diurna 06:00-20:00, nocturna 20:00-06:00; mixta es nocturna con >= 3 h 30.
    _v(NOCTURNO_INICIO_S, _H(20), _D2026, None, "LFT art. 60"),
    _v(NOCTURNO_FIN_S, _H(6), _D2026, None, "LFT art. 60"),
    _v(UMBRAL_NOCTURNA_S, _M(210), _D2026, None, "LFT art. 60 (tres horas y media)"),
    # Art. 63: descanso de media hora, por lo menos, en jornada continua.
    _v(DESCANSO_CONTINUA_MIN_S, _M(30), _D2026, None, "LFT art. 63"),
    # Menores: art. 177 (6 h, periodos de 3 h, reposo de 1 h); arts. 175 I y 176 (22:00).
    _v(MENOR16_JORNADA_S, _H(6), _D2026, None, "LFT art. 177"),
    _v(MENOR16_PERIODO_MAX_S, _H(3), _D2026, None, "LFT art. 177"),
    _v(MENOR16_REPOSO_MIN_S, _H(1), _D2026, None, "LFT art. 177"),
    _v(MENOR_HORA_LIMITE_S, _H(22), _D2026, None, "LFT arts. 175 I y 176"),
)
