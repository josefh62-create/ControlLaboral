"""Emparejamiento sobre la secuencia unificada multi-reloj.

P-30 (falta de salida), P-31 y P-32 (parte pura), P-45 (dos relojes), AL10,
plan 5.1 paso 4 (traslado entre empresas, decision del propietario 26/11/2026).
"""
import random
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from Dominio import normatividad as n
from Dominio.checadas import Checada, marcar_checadas
from Dominio.emparejamiento import (
    AMBIGUA,
    IMPAR,
    NORMAL,
    TRASLADO,
    INTERVALO_EXCEDIDO,
    TRASLADO_EXCEDIDO,
    TRASLADO_PENDIENTE_Q_F,
    TRASLAPE,
    emparejar,
    tiempo_sin_traslape,
)
from Dominio.modelos import ORIGEN_PATRONAL, VersionParametro, Vigencia
from Dominio.tiempo import Intervalo, minutos_a_segundos

CDMX = ZoneInfo("America/Mexico_City")
VERS = n.SEMILLA_PATRONAL
CATAB = dict(reloj="R-CATAB", empresa="CATAB")
AEI = dict(reloj="R-AEI", empresa="AEI")


def ck(id_, h, m=0, s=0, dia=4, sentido=None, **origen):
    origen = origen or AEI
    return Checada(id_, datetime(2027, 1, dia, h, m, s, tzinfo=CDMX), sentido=sentido, **origen)


def emp(checadas, versiones=VERS, **kw):
    return emparejar(marcar_checadas(checadas, versiones), versiones, **kw)


def duraciones(res, etiqueta=None):
    return [
        i.intervalo.duracion for i in res.intervalos if etiqueta in (None, i.etiqueta)
    ]


def tipos(res):
    return sorted(i.tipo for i in res.incidencias)


# --- Caso base ----------------------------------------------------------------

def test_entrada_y_salida_forman_un_intervalo_con_su_origen():
    res = emp([ck("e", 8), ck("s", 17)])
    (i,) = res.intervalos
    assert i.etiqueta == NORMAL
    assert (i.desde.id, i.hasta.id) == ("e", "s")
    assert i.intervalo.duracion == 9 * 3600
    assert i.intervalo == Intervalo(i.desde.instante_s, i.hasta.instante_s)
    assert res.incidencias == ()


def test_sin_checadas_no_hay_nada():
    res = emp([])
    assert res.intervalos == () and res.incidencias == ()


def test_dos_jornadas_el_mismo_dia_son_dos_intervalos_de_la_misma_empresa():
    res = emp([ck("a", 8), ck("b", 12), ck("c", 13), ck("d", 17)])
    assert duraciones(res) == [4 * 3600, 4 * 3600]
    assert all(i.etiqueta == NORMAL for i in res.intervalos)  # misma empresa: descanso, no traslado


# --- P-30: falta de salida ----------------------------------------------------

def test_p30_entrada_sin_salida_es_impar_y_no_fabrica_hora():
    res = emp([ck("e", 8)])
    assert res.intervalos == ()
    (inc,) = res.incidencias
    assert inc.tipo == IMPAR
    assert [c.id for c in inc.checadas] == ["e"]


def test_p30_tres_checadas_cierran_las_dos_primeras_y_la_ultima_queda_impar():
    res = emp([ck("a", 8), ck("b", 12), ck("c", 13)])
    assert duraciones(res) == [4 * 3600]
    assert tipos(res) == [IMPAR]
    assert res.incidencias[0].checadas[0].id == "c"


def test_p30_salida_declarada_sin_entrada_es_impar():
    res = emp([ck("s", 17, sentido="salida")])
    assert res.intervalos == ()
    assert tipos(res) == [IMPAR]


# --- Semantica del dispositivo (ambigua) ---------------------------------------

def test_dos_entradas_declaradas_seguidas_en_el_mismo_reloj_son_ambiguas():
    res = emp([ck("a", 8, sentido="entrada"), ck("b", 9, sentido="entrada"),
               ck("c", 17, sentido="salida")])
    assert tipos(res) == [AMBIGUA]
    assert {c.id for c in res.incidencias[0].checadas} == {"a", "b"}
    # lo dudoso no se cuenta como definitivo: solo b-c es un intervalo
    assert [(i.desde.id, i.hasta.id) for i in res.intervalos] == [("b", "c")]


def test_sentido_declarado_manda_sobre_la_alternancia():
    res = emp([ck("a", 8, sentido="entrada"), ck("b", 12, sentido="salida"),
               ck("c", 13, sentido="entrada"), ck("d", 17, sentido="salida")])
    assert duraciones(res) == [4 * 3600, 4 * 3600]
    assert res.incidencias == ()


def test_intervalo_mas_largo_que_el_maximo_se_marca_y_no_se_cuenta():
    # falta de salida a media secuencia desplazaria todo el emparejamiento
    res = emp([ck("a", 8), ck("b", 8, dia=5), ck("c", 17, dia=5)])
    assert duraciones(res) == [9 * 3600]
    assert tipos(res) == [INTERVALO_EXCEDIDO]
    assert {c.id for c in res.incidencias[0].checadas} == {"a", "b"}


def test_b1_falta_de_salida_el_dia_1_no_desplaza_el_resto_de_la_semana():
    # sin sentido: d1 entrada sin salida; d2 y d3 completos
    res = emp([ck("a", 8), ck("b", 8, dia=5), ck("c", 17, dia=5),
               ck("d", 8, dia=6), ck("e", 17, dia=6)])
    assert [(i.desde.id, i.hasta.id) for i in res.intervalos] == [("b", "c"), ("d", "e")]
    assert duraciones(res) == [9 * 3600, 9 * 3600]
    assert tipos(res) == [INTERVALO_EXCEDIDO]
    assert {c.id for c in res.incidencias[0].checadas} == {"a", "b"}


def test_b1_con_sentido_declarado_tambien_se_marca_y_no_se_cuenta():
    res = emp([ck("a", 8, sentido="entrada"), ck("b", 8, dia=5, sentido="salida")])
    assert res.intervalos == ()
    assert tipos(res) == [INTERVALO_EXCEDIDO]


def test_b1_exactamente_16_h_se_cuenta():
    res = emp([ck("a", 6), ck("b", 22)])
    assert duraciones(res) == [16 * 3600] and res.incidencias == ()


def _pol(clave, valor, empresa):
    return VersionParametro(clave, valor, Vigencia(date(2026, 1, 1)), "prueba",
                            ORIGEN_PATRONAL, empresa)


def test_b1_el_maximo_de_intervalo_es_por_empresa_de_la_entrada():
    vs = (*VERS, _pol(n.INTERVALO_MAX_S, 10 * 3600, "CATAB"))
    ok_aei = emp([ck("a", 6, **AEI), ck("b", 20, **AEI)], vs)  # 14 h, AEI usa 16 h
    assert duraciones(ok_aei) == [14 * 3600]
    en_catab = emp([ck("a", 6, **CATAB), ck("b", 20, **CATAB)], vs)  # 14 h > 10 h
    # la salida reinterpretada como nueva entrada queda impar (recuperacion)
    assert en_catab.intervalos == () and tipos(en_catab) == [IMPAR, INTERVALO_EXCEDIDO]
    # cruzado: manda la empresa de la ENTRADA
    cruzado = emp([ck("a", 6, **AEI), ck("b", 20, **CATAB)], vs)
    assert duraciones(cruzado) == [14 * 3600]


def test_b1_sin_politica_de_intervalo_se_propaga_falta_parametro():
    sin = tuple(v for v in VERS if v.clave != n.INTERVALO_MAX_S)
    with pytest.raises(n.FaltaParametro):
        emp([ck("a", 8), ck("b", 17)], sin)


def test_b1_el_traslado_usa_el_maximo_de_la_empresa_destino():
    vs = (*VERS, _pol(n.TRASLADO_MAX_S, 30 * 60, "AEI"))
    # CATAB -> AEI (destino AEI, 30 min): 45 min excede
    a = emp([ck("a", 8, **CATAB), ck("b", 12, **CATAB), ck("c", 12, 45, **AEI), ck("d", 17, **AEI)], vs)
    assert tipos(a) == [TRASLADO_EXCEDIDO]
    # AEI -> CATAB (destino CATAB, usa el general de 60 min): 45 min cuenta
    b = emp([ck("a", 8, **AEI), ck("b", 12, **AEI), ck("c", 12, 45, **CATAB), ck("d", 17, **CATAB)], vs)
    assert duraciones(b, TRASLADO) == [45 * 60] and tipos(b) == []


def test_n1_hueco_entre_empresas_que_cruza_medianoche_dentro_del_maximo_queda_pendiente():
    res = emp([ck("a", 20, **CATAB), ck("b", 23, 30, **CATAB),
               ck("c", 0, 10, dia=5, **AEI), ck("d", 4, dia=5, **AEI)])
    assert duraciones(res, TRASLADO) == []
    assert tipos(res) == [TRASLADO_PENDIENTE_Q_F]
    assert [c.id for c in res.incidencias[0].checadas] == ["b", "c"]


# --- Duplicados y futuras no entran al emparejamiento (P-31 parte pura) ---------

def test_duplicado_se_conserva_marcado_pero_no_se_usa_para_emparejar():
    res = emp([ck("e", 8), ck("e2", 8, 10), ck("s", 17)])
    (i,) = res.intervalos
    assert (i.desde.id, i.hasta.id) == ("e", "s")
    assert res.incidencias == ()


def test_p31_lote_duplicado_da_los_mismos_intervalos_y_totales():
    lote = [ck("a", 8), ck("b", 12), ck("c", 13), ck("d", 17)]
    uno = emp(lote)
    dos = emp(lote + lote)
    assert dos.intervalos == uno.intervalos
    assert dos.incidencias == uno.incidencias
    assert sum(duraciones(dos)) == 8 * 3600


def test_checada_futura_no_se_empareja_pero_no_se_pierde_en_las_marcas():
    ref = datetime(2027, 1, 4, 12, 0, tzinfo=CDMX)
    marcadas = marcar_checadas([ck("e", 8), ck("s", 17)], VERS, instante_referencia=ref)
    res = emparejar(marcadas, VERS)
    assert res.intervalos == ()
    assert tipos(res) == [IMPAR]
    assert len(marcadas) == 2


# --- P-32: orden -----------------------------------------------------------------

def test_p32_permutaciones_del_mismo_conjunto_dan_resultado_identico():
    base = [
        ck("1", 8, **CATAB), ck("2", 12, **CATAB), ck("3", 12, 40, **AEI),
        ck("4", 17, **AEI), ck("5", 8, dia=5, **AEI), ck("5", 8, dia=5, **AEI),
        ck("6", 9, 30, dia=5, **CATAB),
    ]
    esperado = emp(base)
    rnd = random.Random(26112026)
    for _ in range(100):
        barajada = base[:]
        rnd.shuffle(barajada)
        assert emp(barajada) == esperado


def test_p32_propiedad_sin_minutos_duplicados_ni_negativos():
    rnd = random.Random(7)
    for _ in range(200):
        n_ev = rnd.randint(0, 12)
        evs = [
            ck(
                str(k), rnd.randint(6, 20), rnd.randint(0, 59), rnd.randint(0, 59),
                dia=rnd.randint(4, 6),
                sentido=rnd.choice([None, None, "entrada", "salida"]),
                **rnd.choice([AEI, CATAB]),
            )
            for k in range(n_ev)
        ]
        res = emp(evs)
        union = tiempo_sin_traslape(i.intervalo for i in res.intervalos)
        assert all(x.duracion >= 0 for x in union)
        assert all(a.fin <= b.inicio for a, b in zip(union, union[1:]))
        assert sum(x.duracion for x in union) <= sum(duraciones(res))
        # sin traslape detectado => lo contado es exactamente la suma de los intervalos
        if TRASLAPE not in tipos(res):
            assert sum(x.duracion for x in union) == sum(duraciones(res))


# --- P-45: dos relojes, mismo trabajador ---------------------------------------------

def test_p45_entrada_en_catab_y_salida_en_aei_es_un_solo_intervalo():
    res = emp([ck("e", 8, **CATAB), ck("s", 17, **AEI)])
    (i,) = res.intervalos
    assert (i.desde.empresa, i.hasta.empresa) == ("CATAB", "AEI")
    assert (i.desde.reloj, i.hasta.reloj) == ("R-CATAB", "R-AEI")
    assert i.etiqueta == NORMAL and res.incidencias == ()


def test_p45_traslado_dentro_del_maximo_cuenta_como_tiempo_etiquetado():
    res = emp([ck("a", 8, **CATAB), ck("b", 12, **CATAB),
               ck("c", 12, 45, **AEI), ck("d", 17, **AEI)])
    assert duraciones(res, NORMAL) == [4 * 3600, 4 * 3600 + 15 * 60]
    (t,) = [i for i in res.intervalos if i.etiqueta == TRASLADO]
    assert t.intervalo.duracion == 45 * 60
    assert (t.desde.id, t.hasta.id) == ("b", "c")
    assert (t.desde.empresa, t.hasta.empresa) == ("CATAB", "AEI")
    assert res.incidencias == ()


def test_p45_traslado_exactamente_en_el_maximo_se_cuenta():
    res = emp([ck("a", 8, **CATAB), ck("b", 12, **CATAB),
               ck("c", 13, **AEI), ck("d", 17, **AEI)])
    assert duraciones(res, TRASLADO) == [3600]


def test_p45_traslado_que_excede_el_maximo_queda_pendiente_y_no_se_cuenta():
    res = emp([ck("a", 8, **CATAB), ck("b", 12, **CATAB),
               ck("c", 13, 1, **AEI), ck("d", 17, **AEI)])
    assert duraciones(res, TRASLADO) == []
    assert tipos(res) == [TRASLADO_EXCEDIDO]
    assert [c.id for c in res.incidencias[0].checadas] == ["b", "c"]
    assert len(res.intervalos) == 2


def test_p45_salida_de_una_empresa_y_entrada_de_otra_al_dia_siguiente_no_es_traslado():
    res = emp([ck("a", 8, **CATAB), ck("b", 17, **CATAB),
               ck("c", 8, dia=5, **AEI), ck("d", 17, dia=5, **AEI)])
    assert duraciones(res, TRASLADO) == []
    assert tipos(res) == []  # hueco de 15 h: ni traslado ni pendiente


def test_p45_el_maximo_viene_de_la_politica_versionada():
    v30 = (
        VersionParametro(n.TRASLADO_MAX_S, minutos_a_segundos(30), Vigencia(date(2026, 1, 1)),
                         "prueba", ORIGEN_PATRONAL),
        *n.SEMILLA_PATRONAL[1:],
    )
    cks = [ck("a", 8, **CATAB), ck("b", 12, **CATAB), ck("c", 12, 45, **AEI), ck("d", 17, **AEI)]
    res = emp(cks, v30)
    assert tipos(res) == [TRASLADO_EXCEDIDO]


def test_p45_sin_politica_de_traslado_se_propaga_falta_parametro():
    cks = [ck("a", 8, **CATAB), ck("b", 12, **CATAB), ck("c", 12, 45, **AEI), ck("d", 17, **AEI)]
    marcadas = marcar_checadas(cks, VERS)
    with pytest.raises(n.FaltaParametro):
        emparejar(marcadas, ())


def test_p45_traslape_entre_relojes_se_alerta_y_no_se_cuenta_dos_veces():
    # entrada declarada en CATAB 08:00 y en AEI 09:00; salidas 11:00 (CATAB) y 12:00 (AEI)
    res = emp([
        ck("a", 8, sentido="entrada", **CATAB), ck("b", 9, sentido="entrada", **AEI),
        ck("c", 11, sentido="salida", **CATAB), ck("d", 12, sentido="salida", **AEI),
    ])
    assert len(res.intervalos) == 2
    assert tipos(res) == [TRASLAPE]
    assert {c.id for c in res.incidencias[0].checadas} == {"a", "b", "c", "d"}
    union = tiempo_sin_traslape(i.intervalo for i in res.intervalos)
    assert sum(x.duracion for x in union) == 4 * 3600  # 08:00-12:00, no 6 h


def test_tiempo_sin_traslape_une_intervalos_que_se_tocan_o_se_encimian():
    union = tiempo_sin_traslape([Intervalo(10, 20), Intervalo(0, 5), Intervalo(5, 12), Intervalo(30, 40)])
    assert union == (Intervalo(0, 20), Intervalo(30, 40))


def test_incidencias_e_intervalos_salen_ordenados_por_instante():
    res = emp([ck("z", 9, dia=6, sentido="entrada"), ck("y", 9, dia=5, sentido="salida"),
               ck("a", 8), ck("b", 17)])
    assert [i.desde.id for i in res.intervalos] == ["a"]
    assert [inc.checadas[0].id for inc in res.incidencias] == ["y", "z"]
