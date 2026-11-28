"""Catalogo AL01-AL14, tipo comun `Alerta` y clave de deduplicacion (P-48, parte pura).

El catalogo es la unica fuente de codigo, nombre, nivel y bloqueo de cada alerta (plan 4.4); los
modulos de T1-T5 solo conservan el codigo, y aqui se comprueba que coinciden con el catalogo.
La clave no depende del orden de entrada ni de la severidad/detalle: una misma alerta reimportada no
genera otro aviso (P-48)."""
import random
from dataclasses import replace
from datetime import date

import pytest

from Dominio import alertas as al
from Dominio import calendario, horarios, normatividad as n, tramos_extra
from Dominio.alertas import (
    CATALOGO,
    Alerta,
    clave_deduplicacion,
    consolidar,
    definicion,
)
from Dominio.modelos import Vigencia

SEMANA = Vigencia(date(2027, 1, 4), date(2027, 1, 11))
CODIGOS = tuple(f"AL{i:02d}" for i in range(1, 15))


def alerta(**kw):
    base = dict(
        codigo="AL02", trabajador="T-1", empresa="AEI", severidad="informativo",
        periodo=SEMANA, dia_logico=date(2027, 1, 5), sujeto="", version="n1",
    )
    base.update(kw)
    return Alerta(**base)


# --- Catalogo ---------------------------------------------------------------------------------

def test_el_catalogo_tiene_exactamente_al01_a_al14_en_orden():
    assert tuple(c for c in CATALOGO if c.startswith("AL")) == CODIGOS


@pytest.mark.parametrize("codigo", CODIGOS)
def test_cada_alerta_del_catalogo_tiene_nombre_nivel_y_severidades(codigo):
    d = definicion(codigo)
    assert d.codigo == codigo and d.nombre.strip() and d.nivel.strip()
    assert d.severidades and all(s in al.SEVERIDADES for s in d.severidades)


def test_niveles_del_plan_4_4_se_conservan_literalmente():
    assert definicion("AL01").nivel == "Preventivo"
    assert definicion("AL02").nivel == "Informativo/revisión"
    assert definicion("AL04").nivel == "Advertencia diferenciada"
    assert definicion("AL06").nivel == "Preventivo/crítico"
    assert definicion("AL12").nivel == "Cálculo pendiente"
    assert definicion("AL13").nivel == "Crítico"
    assert definicion("AL14").nivel == "Configuración"


def test_solo_al12_bloquea_el_cierre_y_al14_expresamente_no_bloquea():
    # NL04/RE02: lo no resuelto bloquea solo el calculo definitivo; AL14 "no bloquea" (decision 27/11/2026).
    assert [c for c in CODIGOS if definicion(c).bloquea_cierre] == ["AL12"]
    assert definicion("AL14").bloquea_cierre is False


def test_codigo_desconocido_se_rechaza():
    with pytest.raises(KeyError):
        definicion("AL99")
    with pytest.raises(ValueError):
        alerta(codigo="AL99")


def test_severidad_fuera_de_las_del_catalogo_se_rechaza():
    with pytest.raises(ValueError):
        alerta(codigo="AL01", severidad="critico")  # AL01 es solo preventiva
    assert alerta(codigo="AL06", severidad="critico").severidad == "critico"


def test_los_codigos_producidos_por_t1_a_t5_coinciden_con_el_catalogo():
    assert calendario.AL12 == "AL12" and horarios.AL09 == "AL09" and horarios.AL14 == "AL14"
    assert tramos_extra.AL02 == "AL02" and tramos_extra.AL03 == "AL03"
    assert {n.ALERTA_POR_LIMITE[k] for k in n.ALERTA_POR_LIMITE} <= set(CATALOGO)
    assert horarios.HO03 in CATALOGO  # alerta del plan 5.2 fuera de AL01-AL14, producida por T3/T5
    assert tuple(al.ALERTAS) == CODIGOS


# --- Clave de deduplicacion (P-48, parte pura) ----------------------------------------------------

def test_la_misma_alerta_tiene_la_misma_clave():
    assert clave_deduplicacion(alerta()) == clave_deduplicacion(alerta())


@pytest.mark.parametrize("cambio", [
    dict(codigo="AL12", severidad="calculo_pendiente"),
    dict(trabajador="T-2"),
    dict(empresa="CATAB"),
    dict(dia_logico=date(2027, 1, 6)),
    dict(dia_logico=None),
    dict(periodo=Vigencia(date(2027, 1, 11), date(2027, 1, 18))),
    dict(periodo=None),
    dict(sujeto="art66_alcanzado"),
    dict(version="n2"),
])
def test_cualquier_campo_de_identidad_distinto_da_otra_clave(cambio):
    assert clave_deduplicacion(alerta(**cambio)) != clave_deduplicacion(alerta())


def test_severidad_y_detalle_no_forman_parte_de_la_clave():
    base = alerta(codigo="AL06", severidad="preventivo", detalle="a")
    otra = alerta(codigo="AL06", severidad="critico", detalle="b")
    assert clave_deduplicacion(base) == clave_deduplicacion(otra)


def test_la_clave_no_confunde_campos_con_separadores():
    uno = alerta(trabajador="a|b", empresa="c")
    dos = alerta(trabajador="a", empresa="b|c")
    assert clave_deduplicacion(uno) != clave_deduplicacion(dos)


def test_p48_reimportar_la_misma_alerta_no_genera_avisos_duplicados():
    primera = [alerta(), alerta(codigo="AL12", severidad="calculo_pendiente", sujeto="falta:x")]
    reimportada = [replace(a) for a in primera]
    assert consolidar(primera + reimportada) == consolidar(primera)
    assert len(consolidar(primera + reimportada)) == 2


def test_consolidar_es_independiente_del_orden_de_entrada():
    rng = random.Random(48)
    alertas = [
        alerta(trabajador=f"T-{i % 3}", dia_logico=date(2027, 1, 4 + i % 4), sujeto=str(i % 2),
               severidad="informativo" if i % 2 else "revision", detalle=f"d{i}")
        for i in range(40)
    ]
    esperado = consolidar(alertas)
    for _ in range(25):
        rng.shuffle(alertas)
        assert consolidar(alertas) == esperado


def test_entre_duplicadas_conserva_la_de_mayor_severidad_sin_depender_del_orden():
    leve = alerta(codigo="AL06", severidad="preventivo", sujeto="x", detalle="z")
    grave = alerta(codigo="AL06", severidad="critico", sujeto="x", detalle="a")
    assert consolidar([leve, grave]) == consolidar([grave, leve]) == (grave,)


def test_consolidar_devuelve_tupla_ordenada_por_clave():
    alertas = [alerta(trabajador="T-9"), alerta(trabajador="T-1"), alerta(trabajador="T-5")]
    claves = [clave_deduplicacion(a) for a in consolidar(alertas)]
    assert claves == sorted(claves)


def test_alerta_expone_si_bloquea_el_cierre_segun_el_catalogo():
    assert alerta(codigo="AL12", severidad="calculo_pendiente").bloquea_cierre is True
    assert alerta().bloquea_cierre is False
