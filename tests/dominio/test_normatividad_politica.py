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


def test_anticipacion_preventiva_inicial_60_min_patronal_general():
    v = resolver_vigente(P, n.ANTICIPACION_PREVENTIVA_S, date(2027, 1, 4), ORIGEN_PATRONAL)
    assert v.valor == minutos_a_segundos(60) and v.origen == ORIGEN_PATRONAL and v.empresa is None
    assert "28/11/2026" in v.fuente
    with pytest.raises(FaltaParametro):
        resolver_vigente(P, n.ANTICIPACION_PREVENTIVA_S, date(2027, 1, 4), ORIGEN_LEGAL)


def test_politica_no_se_confunde_con_limite_legal():
    with pytest.raises(FaltaParametro):
        resolver_vigente(P, n.TRASLADO_MAX_S, date(2027, 1, 4), ORIGEN_LEGAL)


def test_semilla_patronal_sin_traslapes_ni_huecos():
    assert validar_versiones(P) == ()


# --- Alcance por empresa (decision del propietario 26/11/2026) -------------------

from Dominio.modelos import VersionParametro, Vigencia  # noqa: E402
from Dominio.normatividad import ParametroAmbiguo  # noqa: E402


def _pol(valor, empresa=None, clave="k", desde=date(2026, 1, 1), hasta=None, origen=ORIGEN_PATRONAL):
    return VersionParametro(clave, valor, Vigencia(desde, hasta), "prueba", origen, empresa)


def test_intervalo_maximo_inicial_16_h_patronal():
    v = resolver_vigente(P, n.INTERVALO_MAX_S, date(2027, 1, 4), ORIGEN_PATRONAL)
    assert v.valor == 16 * 3600 and v.empresa is None
    assert "26/11/2026" in v.fuente


def test_version_de_la_empresa_gana_a_la_general():
    vs = [_pol(10), _pol(20, "CATAB")]
    assert resolver_vigente(vs, "k", date(2027, 1, 4), ORIGEN_PATRONAL, "CATAB").valor == 20
    assert resolver_vigente(vs, "k", date(2027, 1, 4), ORIGEN_PATRONAL, "AEI").valor == 10
    assert resolver_vigente(vs, "k", date(2027, 1, 4), ORIGEN_PATRONAL).valor == 10


def test_version_de_empresa_fuera_de_vigencia_cae_a_la_general():
    vs = [_pol(10), _pol(20, "CATAB", desde=date(2028, 1, 1))]
    assert resolver_vigente(vs, "k", date(2027, 1, 4), ORIGEN_PATRONAL, "CATAB").valor == 10


def test_ambiguedad_se_evalua_dentro_de_cada_alcance():
    vs = [_pol(10), _pol(20, "CATAB"), _pol(30, "CATAB")]
    with pytest.raises(ParametroAmbiguo):
        resolver_vigente(vs, "k", date(2027, 1, 4), ORIGEN_PATRONAL, "CATAB")
    # AEI no tiene version propia: la ambiguedad de CATAB no le afecta
    assert resolver_vigente(vs, "k", date(2027, 1, 4), ORIGEN_PATRONAL, "AEI").valor == 10


def test_falta_si_no_hay_ni_de_empresa_ni_general():
    with pytest.raises(FaltaParametro):
        resolver_vigente([_pol(20, "CATAB")], "k", date(2027, 1, 4), ORIGEN_PATRONAL, "AEI")


def test_parametro_legal_es_global_una_version_legal_por_empresa_se_ignora():
    vs = [_pol(48, origen=ORIGEN_LEGAL), _pol(40, "CATAB", origen=ORIGEN_LEGAL)]
    assert resolver_vigente(vs, "k", date(2027, 1, 4), ORIGEN_LEGAL, "CATAB").valor == 48
    # y no puede ser la unica: una version legal solo de empresa no existe como global
    with pytest.raises(FaltaParametro):
        resolver_vigente([_pol(40, "CATAB", origen=ORIGEN_LEGAL)], "k", date(2027, 1, 4), ORIGEN_LEGAL)


def test_validador_trabaja_por_clave_origen_y_empresa():
    ok = [_pol(10), _pol(20, "CATAB"), _pol(30, "AEI")]  # vigencias abiertas, alcances distintos
    assert validar_versiones(ok) == ()
    mal = ok + [_pol(40, "CATAB")]
    (p,) = validar_versiones(mal)
    assert (p.tipo, p.clave, p.empresa) == ("traslape", "k", "CATAB")


def test_validador_hueco_dentro_de_una_empresa():
    vs = [_pol(1, "CATAB", hasta=date(2027, 1, 1)), _pol(2, "CATAB", desde=date(2027, 2, 1))]
    (p,) = validar_versiones(vs)
    assert (p.tipo, p.empresa) == ("hueco", "CATAB")
