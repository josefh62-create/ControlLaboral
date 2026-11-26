"""Semilla de politica patronal para checadas: traslado entre empresas y duplicados."""
from datetime import date

import pytest

from Dominio import normatividad as n
from Dominio.modelos import ORIGEN_LEGAL, ORIGEN_PATRONAL
from Dominio.normatividad import FaltaParametro, resolver_vigente, validar_versiones
from Dominio.tiempo import minutos_a_segundos

P = n.SEMILLA_PATRONAL


def test_traslado_maximo_inicial_60_min_patronal():
    v = resolver_vigente(P, n.TRASLADO_MAX_S, date(2027, 1, 4), ORIGEN_PATRONAL)
    assert v.valor == minutos_a_segundos(60)
    assert v.origen == ORIGEN_PATRONAL
    assert "art. 58" in v.fuente


def test_ventana_duplicados_inicial_30_min_valor_de_v1():
    v = resolver_vigente(P, n.VENTANA_DUPLICADOS_S, date(2027, 1, 4), ORIGEN_PATRONAL)
    assert v.valor == minutos_a_segundos(30)
    assert "V1" in v.fuente


def test_politica_no_se_confunde_con_limite_legal():
    with pytest.raises(FaltaParametro):
        resolver_vigente(P, n.TRASLADO_MAX_S, date(2027, 1, 4), ORIGEN_LEGAL)


def test_semilla_patronal_sin_traslapes_ni_huecos():
    assert validar_versiones(P) == ()
