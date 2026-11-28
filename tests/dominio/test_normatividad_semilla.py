"""Semilla legal 2026-2030 (doc. 00, plan 2/2.1): P-36, P-40, NL01, NL05, NL06."""
from datetime import date

import pytest

from Dominio import normatividad as n
from Dominio.modelos import ORIGEN_PATRONAL, VersionParametro, Vigencia
from Dominio.normatividad import FaltaParametro, resolver_vigente, validar_versiones
from Dominio.tiempo import horas_a_segundos, minutos_a_segundos

S = n.SEMILLA_LEGAL


def val(clave, fecha):
    return resolver_vigente(S, clave, fecha).valor


@pytest.mark.parametrize(
    "anio, horas",
    [(2026, 48), (2027, 46), (2028, 44), (2029, 42), (2030, 40), (2031, 40), (2040, 40)],
)
def test_ordinaria_semanal_por_anio(anio, horas):
    assert val(n.ORDINARIA_SEMANAL_S, date(anio, 6, 15)) == horas_a_segundos(horas)


def test_cambio_de_anio_es_el_1_de_enero():
    assert val(n.ORDINARIA_SEMANAL_S, date(2026, 12, 31)) == horas_a_segundos(48)
    assert val(n.ORDINARIA_SEMANAL_S, date(2027, 1, 1)) == horas_a_segundos(46)


@pytest.mark.parametrize(
    "anio, horas", [(2026, 9), (2027, 9), (2028, 10), (2029, 11), (2030, 12), (2035, 12)]
)
def test_art66_semanal_por_anio(anio, horas):
    assert val(n.ART66_SEMANAL_S, date(anio, 7, 1)) == horas_a_segundos(horas)


def test_art68_es_4h_semanales_y_no_gradual():
    for anio in (2026, 2027, 2028, 2029, 2030):
        assert val(n.ART68_SEMANAL_S, date(anio, 12, 1)) == horas_a_segundos(4)


def test_nl06_art66_y_art68_son_parametros_y_alertas_distintos():
    assert n.ART66_SEMANAL_S != n.ART68_SEMANAL_S
    assert n.ALERTA_POR_LIMITE[n.ART66_SEMANAL_S] == "AL04"
    assert n.ALERTA_POR_LIMITE[n.ART68_SEMANAL_S] == "AL06"
    assert n.ALERTA_POR_LIMITE[n.ART66_DIARIO_S] == "AL05"
    assert n.ALERTA_POR_LIMITE[n.ART66_DIAS_SEMANA] == "AL05"
    assert n.ALERTA_POR_LIMITE[n.TOTAL_DIARIO_MAX_S] == "AL07"
    # 2027: 9 h del art. 66 y 4 h adicionales del art. 68, sumadas 13 h (plan 2)
    f = date(2027, 5, 5)
    assert val(n.ART66_SEMANAL_S, f) + val(n.ART68_SEMANAL_S, f) == horas_a_segundos(13)


def test_distribucion_nueva_desde_decreto_4h_dia_4_dias():
    f = date(2026, 5, 1)
    assert val(n.ART66_DIARIO_S, f) == horas_a_segundos(4)
    assert val(n.ART66_DIAS_SEMANA, f) == 4
    assert val(n.TOTAL_DIARIO_MAX_S, f) == horas_a_segundos(12)


def test_p40_enero_abril_2026_usa_norma_anterior_sin_limites_nuevos():
    for f in (date(2026, 1, 1), date(2026, 4, 30)):
        assert val(n.ART66_DIARIO_S, f) == horas_a_segundos(3)
        assert val(n.ART66_DIAS_SEMANA, f) == 3
        # el limite nuevo de 12 h diarias y el tramo art. 68 no existen aun para el periodo
        with pytest.raises(FaltaParametro):
            val(n.TOTAL_DIARIO_MAX_S, f)
        with pytest.raises(FaltaParametro):
            val(n.ART68_SEMANAL_S, f)


def test_p40_corte_exacto_el_1_de_mayo():
    assert val(n.ART66_DIARIO_S, date(2026, 4, 30)) == horas_a_segundos(3)
    assert val(n.ART66_DIARIO_S, date(2026, 5, 1)) == horas_a_segundos(4)


def test_p36_fecha_2026_resuelve_2026_con_la_semilla_completa_activa():
    assert val(n.ORDINARIA_SEMANAL_S, date(2026, 10, 1)) == horas_a_segundos(48)
    assert val(n.ORDINARIA_SEMANAL_S, date(2027, 10, 1)) == horas_a_segundos(46)


def test_regimenes_diarios_y_franja_art_60_61():
    f = date(2027, 3, 3)
    assert val(n.JORNADA_DIURNA_S, f) == minutos_a_segundos(480)
    assert val(n.JORNADA_NOCTURNA_S, f) == minutos_a_segundos(420)
    assert val(n.JORNADA_MIXTA_S, f) == minutos_a_segundos(450)
    assert val(n.NOCTURNO_INICIO_S, f) == horas_a_segundos(20)
    assert val(n.NOCTURNO_FIN_S, f) == horas_a_segundos(6)
    assert val(n.UMBRAL_NOCTURNA_S, f) == minutos_a_segundos(210)


def test_menores_arts_177_175():
    f = date(2027, 3, 3)
    assert val(n.MENOR16_JORNADA_S, f) == horas_a_segundos(6)
    assert val(n.MENOR16_PERIODO_MAX_S, f) == horas_a_segundos(3)
    assert val(n.MENOR16_REPOSO_MIN_S, f) == horas_a_segundos(1)
    assert val(n.MENOR_HORA_LIMITE_S, f) == horas_a_segundos(22)


def test_descanso_jornada_continua_art_63():
    assert val(n.DESCANSO_CONTINUA_MIN_S, date(2027, 1, 1)) == minutos_a_segundos(30)


def test_toda_version_semilla_es_legal_y_cita_fuente():
    for v in S:
        assert v.origen == "legal"
        assert v.fuente.strip()
        assert isinstance(v.valor, int)


def test_nl02_semilla_sin_traslapes_ni_huecos_salvo_lo_no_documentado():
    # ART68 y TOTAL_DIARIO empiezan el 2026-05-01 (no hay norma anterior documentada);
    # eso es ausencia, no hueco entre versiones.
    assert validar_versiones(S) == ()


def test_nl05_limite_patronal_mas_estricto_no_cambia_el_legal():
    interno = VersionParametro(
        n.ORDINARIA_SEMANAL_S, horas_a_segundos(40), Vigencia(date(2026, 1, 1)), "politica", ORIGEN_PATRONAL
    )
    todas = S + (interno,)
    f = date(2026, 8, 1)
    assert resolver_vigente(todas, n.ORDINARIA_SEMANAL_S, f).valor == horas_a_segundos(48)
    assert resolver_vigente(todas, n.ORDINARIA_SEMANAL_S, f, ORIGEN_PATRONAL).valor == horas_a_segundos(40)
    assert validar_versiones(todas) == ()
