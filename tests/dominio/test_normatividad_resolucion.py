"""resolver_vigente y validacion de versiones (NL02, NL05, P-36, P-49, P-50)."""
from datetime import date

import pytest

from Dominio.modelos import Vigencia, VersionParametro
from Dominio.normatividad import (
    FaltaParametro,
    ParametroAmbiguo,
    resolver_vigente,
    validar_versiones,
)

K = "tope_semanal_s"


def v(valor, desde, hasta=None, clave=K, origen="legal"):
    return VersionParametro(clave, valor, Vigencia(desde, hasta), "prueba", origen)


def test_vigencia_semiabierta():
    vig = Vigencia(date(2027, 1, 1), date(2028, 1, 1))
    assert vig.contiene(date(2027, 1, 1))
    assert vig.contiene(date(2027, 12, 31))
    assert not vig.contiene(date(2028, 1, 1))
    assert not vig.contiene(date(2026, 12, 31))


def test_vigencia_abierta_no_tiene_fin():
    assert Vigencia(date(2030, 1, 1), None).contiene(date(2099, 1, 1))


def test_vigencia_invalida():
    with pytest.raises(ValueError):
        Vigencia(date(2027, 1, 1), date(2027, 1, 1))


def test_resuelve_exactamente_una_version():
    vs = [v(48, date(2026, 1, 1), date(2027, 1, 1)), v(46, date(2027, 1, 1), date(2028, 1, 1))]
    assert resolver_vigente(vs, K, date(2026, 6, 1)).valor == 48
    assert resolver_vigente(vs, K, date(2027, 1, 1)).valor == 46


def test_p36_consulta_2026_usa_norma_2026_aunque_2027_este_activa():
    vs = [v(48, date(2026, 1, 1), date(2027, 1, 1)), v(46, date(2027, 1, 1), date(2028, 1, 1))]
    # la fecha que cuenta es la trabajada, no la de consulta
    assert resolver_vigente(vs, K, date(2026, 11, 30)).valor == 48


def test_p49_version_futura_no_afecta_la_fecha_actual():
    actual = [v(48, date(2026, 1, 1))]
    con_futura = [v(48, date(2026, 1, 1), date(2027, 1, 1)), v(46, date(2027, 1, 1))]
    hoy = date(2026, 11, 26)
    assert resolver_vigente(actual, K, hoy).valor == resolver_vigente(con_futura, K, hoy).valor == 48
    # la simulacion futura si la ve
    assert resolver_vigente(con_futura, K, date(2027, 3, 1)).valor == 46


def test_p50_parametro_cambia_a_mitad_de_mes():
    vs = [v(10, date(2026, 3, 1), date(2026, 3, 16)), v(5, date(2026, 3, 16))]
    assert resolver_vigente(vs, K, date(2026, 3, 15)).valor == 10
    assert resolver_vigente(vs, K, date(2026, 3, 16)).valor == 5
    assert resolver_vigente(vs, K, date(2026, 3, 31)).valor == 5


def test_cero_versiones_levanta_falta_parametro():
    vs = [v(46, date(2027, 1, 1))]
    with pytest.raises(FaltaParametro) as e:
        resolver_vigente(vs, K, date(2026, 6, 1))
    assert e.value.clave == K and e.value.fecha == date(2026, 6, 1)


def test_clave_inexistente_levanta_falta_parametro():
    with pytest.raises(FaltaParametro):
        resolver_vigente([v(1, date(2026, 1, 1))], "otra", date(2026, 6, 1))


def test_dos_versiones_vigentes_levanta_ambiguo():
    vs = [v(48, date(2026, 1, 1)), v(46, date(2026, 6, 1))]
    with pytest.raises(ParametroAmbiguo):
        resolver_vigente(vs, K, date(2026, 7, 1))


def test_resolver_ignora_otras_claves():
    vs = [v(48, date(2026, 1, 1)), v(99, date(2026, 1, 1), clave="otra")]
    assert resolver_vigente(vs, K, date(2026, 2, 1)).valor == 48


def test_nl05_limite_patronal_no_altera_el_legal():
    legal = v(2880, date(2026, 1, 1))
    patronal = v(2400, date(2026, 1, 1), origen="patronal")
    vs = [legal, patronal]
    assert resolver_vigente(vs, K, date(2026, 6, 1)).valor == 2880
    assert resolver_vigente(vs, K, date(2026, 6, 1), origen="patronal").valor == 2400


def test_nl02_detecta_traslape():
    vs = [v(1, date(2026, 1, 1), date(2026, 7, 1)), v(2, date(2026, 6, 1), date(2027, 1, 1))]
    problemas = validar_versiones(vs)
    assert [(p.tipo, p.clave) for p in problemas] == [("traslape", K)]
    assert problemas[0].desde == date(2026, 6, 1)
    assert problemas[0].hasta == date(2026, 7, 1)


def test_nl02_detecta_hueco():
    vs = [v(1, date(2026, 1, 1), date(2026, 6, 1)), v(2, date(2026, 7, 1))]
    problemas = validar_versiones(vs)
    assert [p.tipo for p in problemas] == ["hueco"]
    assert (problemas[0].desde, problemas[0].hasta) == (date(2026, 6, 1), date(2026, 7, 1))


def test_nl02_contiguas_sin_problemas_y_orden_de_entrada_irrelevante():
    vs = [v(2, date(2027, 1, 1)), v(1, date(2026, 1, 1), date(2027, 1, 1))]
    assert validar_versiones(vs) == ()


def test_nl02_traslape_con_version_abierta():
    vs = [v(1, date(2026, 1, 1)), v(2, date(2027, 1, 1))]
    assert [p.tipo for p in validar_versiones(vs)] == ["traslape"]


def test_nl02_validacion_es_por_clave_y_origen():
    vs = [
        v(1, date(2026, 1, 1)),
        v(2, date(2026, 1, 1), clave="otra"),
        v(3, date(2026, 1, 1), origen="patronal"),
    ]
    assert validar_versiones(vs) == ()
