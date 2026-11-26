"""Tolerancias TO01-TO07: P-18, P-19, P-20, P-50 (version por fecha) y precedencia TO02."""
from datetime import date

import pytest

from Dominio import normatividad as n
from Dominio.modelos import ORIGEN_PATRONAL, VersionParametro, Vigencia
from Dominio.tiempo import minutos_a_segundos as m
from Dominio.tolerancias import (
    ANTICIPADA,
    POSTERIOR,
    TARDIA,
    Tolerancias,
    ToleranciaInvalida,
    evaluar_marca,
    resolver_tolerancias,
    validar_tolerancia_minutos,
    version_de_tolerancia,
)

HORA = 3600
S0700 = 7 * HORA  # instante base: 07:00:00


# --- TO01 / P-20 ---------------------------------------------------------------

@pytest.mark.parametrize("valor", [0, 15, 10])
def test_p20_acepta_enteros_de_0_a_15(valor):
    assert validar_tolerancia_minutos(valor) == valor


@pytest.mark.parametrize("valor", [-1, 16, 1.5, True, False, "10", None, 15.0])
def test_p20_rechaza_negativos_decimales_mayores_de_15_y_no_enteros(valor):
    with pytest.raises(ToleranciaInvalida):
        validar_tolerancia_minutos(valor)


def test_to01_tolerancias_valida_cada_campo_en_segundos():
    t = Tolerancias.desde_minutos(10, 5, 0, 15, 3)
    assert (t.entrada_anticipada_s, t.entrada_tardia_s) == (m(10), m(5))
    assert (t.salida_anticipada_s, t.salida_posterior_s, t.regreso_comida_s) == (0, m(15), m(3))
    with pytest.raises(ToleranciaInvalida):
        Tolerancias.desde_minutos(10, 16, 0, 0, 0)
    with pytest.raises(ToleranciaInvalida):
        Tolerancias(m(10) + 30, 0, 0, 0, 0)  # no es minuto entero
    with pytest.raises(ToleranciaInvalida):
        Tolerancias(m(16), 0, 0, 0, 0)


def test_to01_version_de_tolerancia_rechaza_valores_invalidos():
    v = version_de_tolerancia(n.TOL_ENTRADA_TARDIA_S, 10, Vigencia(date(2027, 1, 1)), "reglamento", "AEI")
    assert (v.valor, v.origen, v.empresa) == (m(10), ORIGEN_PATRONAL, "AEI")
    with pytest.raises(ToleranciaInvalida):
        version_de_tolerancia(n.TOL_ENTRADA_TARDIA_S, 16, Vigencia(date(2027, 1, 1)), "x")
    with pytest.raises(ValueError):
        version_de_tolerancia("clave_inexistente", 5, Vigencia(date(2027, 1, 1)), "x")


# --- TO03 / P-18 / P-19: borde exacto ------------------------------------------

def test_p18_entrada_0710_con_tolerancia_10_esta_dentro_y_conserva_diferencia_real():
    ev = evaluar_marca(TARDIA, S0700, S0700 + m(10), m(10))
    assert ev.dentro_tolerancia is True
    assert ev.diferencia_real_s == m(10)
    assert ev.excedente_s == 0


def test_p19_entrada_0711_con_tolerancia_10_esta_fuera_y_conserva_11_min():
    ev = evaluar_marca(TARDIA, S0700, S0700 + m(11), m(10))
    assert ev.dentro_tolerancia is False
    assert ev.diferencia_real_s == m(11)
    assert ev.excedente_s == m(1)


def test_to03_un_segundo_despues_del_limite_queda_fuera():
    dentro = evaluar_marca(TARDIA, S0700, S0700 + m(10), m(10))
    fuera = evaluar_marca(TARDIA, S0700, S0700 + m(10) + 1, m(10))
    assert dentro.dentro_tolerancia and not fuera.dentro_tolerancia
    assert fuera.diferencia_real_s == m(10) + 1
    assert fuera.excedente_s == 1
    assert fuera.precision == "segundos"


def test_to03_muestra_la_precision_usada():
    assert evaluar_marca(TARDIA, S0700, S0700 + 60, m(10), precision="minutos").precision == "minutos"


def test_to04_tolerancia_cero_no_da_margen():
    assert evaluar_marca(TARDIA, S0700, S0700 + 1, 0).dentro_tolerancia is False
    assert evaluar_marca(TARDIA, S0700, S0700, 0).dentro_tolerancia is True


def test_to05_diferencia_real_y_excedente_se_conservan_por_separado():
    ev = evaluar_marca(TARDIA, S0700, S0700 + m(12), m(10))  # ejemplo del plan: 12 min / 2 min
    assert (ev.diferencia_real_s, ev.excedente_s) == (m(12), m(2))


def test_evaluar_marca_distingue_anticipada_tardia_y_posterior():
    ant = evaluar_marca(ANTICIPADA, S0700, S0700 - m(10), m(10))
    assert ant.dentro_tolerancia and ant.diferencia_real_s == m(10)
    pos = evaluar_marca(POSTERIOR, S0700, S0700 + m(10), m(10))
    assert pos.dentro_tolerancia and pos.diferencia_real_s == m(10)
    # una marca del otro lado del horario no es diferencia en ese sentido
    assert evaluar_marca(TARDIA, S0700, S0700 - m(5), m(10)).diferencia_real_s == 0
    with pytest.raises(ValueError):
        evaluar_marca("otra", S0700, S0700, 0)


# --- TO02 / P-50: resolucion por empresa, horario y vigencia --------------------

def _ver(clave, minutos, desde, hasta=None, empresa=None):
    return VersionParametro(clave, m(minutos), Vigencia(desde, hasta), "prueba", ORIGEN_PATRONAL, empresa)


def _todas(minutos, desde, hasta=None, empresa=None):
    claves = (n.TOL_ENTRADA_ANTICIPADA_S, n.TOL_ENTRADA_TARDIA_S, n.TOL_SALIDA_ANTICIPADA_S,
              n.TOL_SALIDA_POSTERIOR_S, n.TOL_REGRESO_COMIDA_S)
    return [_ver(c, minutos, desde, hasta, empresa) for c in claves]


def test_to02_empresa_prevalece_sobre_general():
    vers = _todas(5, date(2027, 1, 1)) + _todas(10, date(2027, 1, 1), empresa="CATAB")
    assert resolver_tolerancias(vers, date(2027, 3, 1), "CATAB").entrada_tardia_s == m(10)
    assert resolver_tolerancias(vers, date(2027, 3, 1), "AEI").entrada_tardia_s == m(5)


def test_to02_horario_prevalece_sobre_empresa():
    vers = _todas(5, date(2027, 1, 1), empresa="AEI")
    propias = Tolerancias.desde_minutos(0, 3, 0, 0, 0)
    assert resolver_tolerancias(vers, date(2027, 3, 1), "AEI", propias).entrada_tardia_s == m(3)


def test_p50_cada_fecha_usa_su_version_aunque_cambie_a_mitad_de_mes():
    vers = (_todas(10, date(2027, 1, 1), date(2027, 3, 16))
            + _todas(5, date(2027, 3, 16)))
    assert resolver_tolerancias(vers, date(2027, 3, 15), "AEI").entrada_tardia_s == m(10)
    assert resolver_tolerancias(vers, date(2027, 3, 16), "AEI").entrada_tardia_s == m(5)


def test_resolver_tolerancias_sin_configuracion_levanta_falta_parametro():
    with pytest.raises(n.FaltaParametro):
        resolver_tolerancias([], date(2027, 3, 1), "AEI")


def test_resolver_tolerancias_rechaza_una_version_almacenada_invalida():
    malas = _todas(5, date(2027, 1, 1))
    malas[1] = VersionParametro(n.TOL_ENTRADA_TARDIA_S, m(16), Vigencia(date(2027, 1, 1)), "x", ORIGEN_PATRONAL)
    with pytest.raises(ToleranciaInvalida):
        resolver_tolerancias(malas, date(2027, 3, 1), "AEI")
