"""Tabla de regimenes (NL07, doc. 03 8.5): topes, prohibiciones y alertas."""
from datetime import date

import pytest

from Dominio import normatividad as n
from Dominio import regimenes as r
from Dominio.normatividad import FaltaParametro
from Dominio.tiempo import horas_a_segundos, minutos_a_segundos

S = n.SEMILLA_LEGAL
F = date(2027, 3, 3)


def test_estan_modelados_todos_los_regimenes_nl07():
    assert set(r.REGIMENES) == {
        "diurna", "nocturna", "mixta", "parcial", "menor_15_16", "menor_16_18",
    }
    for codigo, reg in r.REGIMENES.items():
        assert reg.codigo == codigo
        assert r.obtener_regimen(codigo) is reg


def test_regimen_desconocido():
    with pytest.raises(KeyError):
        r.obtener_regimen("inexistente")


@pytest.mark.parametrize(
    "codigo, minutos",
    [("diurna", 480), ("nocturna", 420), ("mixta", 450), ("menor_15_16", 360), ("menor_16_18", 480)],
)
def test_tope_diario_viene_de_la_normatividad(codigo, minutos):
    assert r.tope_diario_s(r.obtener_regimen(codigo), S, F) == minutos_a_segundos(minutos)


def test_parcial_no_tiene_tope_legal_propio():
    assert r.tope_diario_s(r.obtener_regimen("parcial"), S, F) is None


def test_tope_sin_version_vigente_levanta_falta_parametro():
    with pytest.raises(FaltaParametro):
        r.tope_diario_s(r.obtener_regimen("diurna"), (), F)


def test_adultos_admiten_extra_domingo_y_descanso():
    for codigo in ("diurna", "nocturna", "mixta", "parcial"):
        reg = r.obtener_regimen(codigo)
        assert reg.permite_extra and reg.permite_domingo and reg.permite_descanso_obligatorio
        assert reg.clave_hora_limite is None
        assert r.evaluar_prohibiciones(
            reg, S, F, tiempo_extra_s=3600, es_domingo=True,
            es_descanso_obligatorio=True, fin_del_dia_s=horas_a_segundos(23),
        ) == ()


@pytest.mark.parametrize("codigo", ["menor_15_16", "menor_16_18"])
def test_menores_art_178_prohibiciones(codigo):
    reg = r.obtener_regimen(codigo)
    assert not reg.permite_extra
    assert not reg.permite_domingo
    assert not reg.permite_descanso_obligatorio
    codigos = lambda **kw: {i.codigo for i in r.evaluar_prohibiciones(reg, S, F, **kw)}
    assert codigos(tiempo_extra_s=1) == {r.EXTRA_PROHIBIDA}
    assert codigos(es_domingo=True) == {r.DOMINGO_PROHIBIDO}
    assert codigos(es_descanso_obligatorio=True) == {r.DESCANSO_OBLIGATORIO_PROHIBIDO}
    assert codigos() == set()


@pytest.mark.parametrize("codigo", ["menor_15_16", "menor_16_18"])
def test_menores_no_despues_de_las_22(codigo):
    reg = r.obtener_regimen(codigo)
    assert r.hora_limite_s(reg, S, F) == horas_a_segundos(22)
    en = lambda h: r.evaluar_prohibiciones(reg, S, F, fin_del_dia_s=horas_a_segundos(h))
    assert en(22) == ()  # terminar exactamente a las 22:00 es admisible
    assert [i.codigo for i in en(22) + en(23)] == [r.NOCTURNO_MENOR_PROHIBIDO]


def test_adultos_sin_hora_limite():
    assert r.hora_limite_s(r.obtener_regimen("diurna"), S, F) is None


def test_menor_15_16_periodos_de_3h_y_reposo_de_1h():
    assert r.limites_periodo(r.obtener_regimen("menor_15_16"), S, F) == (
        horas_a_segundos(3), horas_a_segundos(1),
    )
    assert r.limites_periodo(r.obtener_regimen("menor_16_18"), S, F) is None
    assert r.limites_periodo(r.obtener_regimen("diurna"), S, F) is None


def test_infracciones_citan_fundamento_y_alerta_diferenciada():
    reg = r.obtener_regimen("menor_16_18")
    (inf,) = r.evaluar_prohibiciones(reg, S, F, tiempo_extra_s=60)
    assert "178" in inf.fundamento
    assert inf.alerta == "AL02"


@pytest.mark.parametrize(
    "edad, codigo", [(15, "menor_15_16"), (16, "menor_16_18"), (17, "menor_16_18"), (18, None), (40, None)]
)
def test_regimen_por_edad(edad, codigo):
    reg = r.regimen_por_edad(edad)
    assert (reg.codigo if reg else None) == codigo


def test_menor_de_15_trabajo_prohibido_art_22_bis():
    with pytest.raises(r.TrabajoMenorProhibido):
        r.regimen_por_edad(14)


@pytest.mark.parametrize(
    "nocturnos_min, diurnos_min, esperado",
    [(0, 480, "diurna"), (209, 271, "mixta"), (210, 270, "nocturna"), (420, 0, "nocturna"), (60, 0, "nocturna")],
)
def test_art_60_mixta_con_menos_de_3h30_nocturnas(nocturnos_min, diurnos_min, esperado):
    # P-27 (3 h 29 / 3 h 30) se cubrira completo en T4; aqui solo el umbral versionado.
    clasificada = r.clasificar_jornada(
        minutos_a_segundos(nocturnos_min), minutos_a_segundos(diurnos_min), S, F
    )
    assert clasificada == esperado


def test_p27_umbral_3h29_mixta_3h30_nocturna():
    umbral = minutos_a_segundos(210)
    assert r.clasificar_jornada(umbral - 60, 3600, S, F) == "mixta"
    assert r.clasificar_jornada(umbral, 3600, S, F) == "nocturna"
