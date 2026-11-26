"""Orden y marcado de checadas: P-31 (parte pura), P-32, RE05, plan 5.1 pasos 2-3."""
import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from Dominio import normatividad as n
from Dominio.checadas import (
    CERCANA_SIN_RESOLVER,
    DESFASE,
    FUTURA,
    POSIBLE_DUPLICADO,
    Checada,
    ordenar_checadas,
    marcar_checadas,
)
from Dominio.tiempo import minutos_a_segundos

CDMX = ZoneInfo("America/Mexico_City")
VERS = n.SEMILLA_PATRONAL


def ck(id_, h, m=0, s=0, reloj="R-AEI", empresa="AEI", dia=4, sentido=None, **kw):
    return Checada(
        id_, datetime(2027, 1, dia, h, m, s, tzinfo=CDMX), reloj, empresa, sentido, **kw
    )


def marcas_de(resultado):
    return {cm.checada.id: cm.marcas for cm in resultado}


# --- Modelo ---------------------------------------------------------------

def test_checada_exige_instante_con_zona():
    with pytest.raises(ValueError):
        Checada("a", datetime(2027, 1, 4, 8, 0), "R", "AEI")


def test_checada_rechaza_sentido_desconocido():
    with pytest.raises(ValueError):
        ck("a", 8, sentido="otro")


def test_instante_en_segundos_enteros_independiente_de_zona():
    utc = Checada("u", datetime(2027, 1, 4, 14, 0, 5, tzinfo=timezone.utc), "R", "AEI")
    local = ck("l", 8, 0, 5)  # 08:00:05 CDMX = 14:00:05 UTC (enero, UTC-6)
    assert utc.instante_s == local.instante_s
    assert isinstance(local.instante_s, int)


# --- Orden (P-32) -----------------------------------------------------------

def test_p32_ordena_por_instante_no_por_importacion():
    a, b, c = ck("a", 8), ck("b", 12), ck("c", 17)
    assert ordenar_checadas([c, a, b]) == (a, b, c)


def test_p32_orden_entre_zonas_distintas_por_instante_real():
    utc = Checada("u", datetime(2027, 1, 4, 15, 0, tzinfo=timezone.utc), "R", "AEI")  # 09:00 CDMX
    local = ck("l", 8, 30)
    assert ordenar_checadas([utc, local]) == (local, utc)


def test_p32_ordenar_no_descarta_nada():
    xs = [ck("a", 8), ck("a", 8), ck("b", 9)]
    assert len(ordenar_checadas(xs)) == 3


def test_p32_permutaciones_dan_el_mismo_orden_y_marcas():
    rnd = random.Random(20261126)
    base = [
        ck("1", 8, reloj="R-CATAB", empresa="CATAB", sentido="entrada"),
        ck("2", 8, 10, reloj="R-CATAB", empresa="CATAB", sentido="entrada"),
        ck("3", 12),
        ck("4", 12),
        ck("5", 13, reloj="R-CATAB", empresa="CATAB"),
        ck("6", 17, 30),
        ck("6", 17, 30),
    ]
    esperado = marcar_checadas(base, VERS)
    for _ in range(50):
        barajada = base[:]
        rnd.shuffle(barajada)
        assert marcar_checadas(barajada, VERS) == esperado


# --- Marcado (RE05, P-31) -----------------------------------------------------

def test_marcar_devuelve_todas_las_checadas_sin_descartar():
    xs = [ck("a", 8), ck("b", 8, 5), ck("c", 12)]
    res = marcar_checadas(xs, VERS)
    assert [cm.checada for cm in res] == list(ordenar_checadas(xs))


def test_sin_marcas_cuando_todo_es_normal():
    res = marcar_checadas([ck("a", 8), ck("b", 12)], VERS)
    assert all(cm.marcas == frozenset() for cm in res)


def test_duplicado_dentro_de_la_ventana_marca_la_segunda_y_conserva_ambas():
    res = marcar_checadas([ck("a", 8), ck("b", 8, 20), ck("c", 17)], VERS)
    assert marcas_de(res) == {
        "a": frozenset(), "b": frozenset({POSIBLE_DUPLICADO}), "c": frozenset()
    }


def test_duplicado_limite_exacto_de_30_min_es_duplicado_y_30_01_no():
    res = marcar_checadas([ck("a", 8), ck("b", 8, 30), ck("c", 8, 30, 1)], VERS)
    m = marcas_de(res)
    assert m["b"] == frozenset({POSIBLE_DUPLICADO})
    assert m["c"] == frozenset()  # 30 min 1 s despues de la ultima conservada (08:00)


def test_ventana_se_mide_contra_la_ultima_conservada_sin_arrastre_en_cadena():
    # a 08:00 (conservada), b 08:25 (dup), c 08:50: 50 min desde a -> no es dup
    res = marcar_checadas([ck("a", 8), ck("b", 8, 25), ck("c", 8, 50)], VERS)
    assert marcas_de(res) == {
        "a": frozenset(),
        "b": frozenset({POSIBLE_DUPLICADO}),
        "c": frozenset(),
    }


def test_p31_lote_identico_dos_veces_marca_la_repeticion():
    lote = [ck("a", 8), ck("b", 12), ck("c", 17)]
    res = marcar_checadas(lote + lote, VERS)
    assert sum(POSIBLE_DUPLICADO in cm.marcas for cm in res) == 3
    conservadas = [cm.checada for cm in res if POSIBLE_DUPLICADO not in cm.marcas]
    assert conservadas == list(ordenar_checadas(lote))


def test_relojes_distintos_no_son_duplicado_entre_si():
    # salida en un reloj y entrada en otro a minutos: es traslado, no duplicado
    res = marcar_checadas(
        [ck("a", 14, reloj="R-CATAB", empresa="CATAB"), ck("b", 14, 20)], VERS
    )
    assert all(cm.marcas == frozenset() for cm in res)


def test_sentidos_declarados_distintos_no_son_duplicado():
    res = marcar_checadas(
        [ck("a", 8, sentido="entrada"), ck("b", 8, 2, sentido="salida")], VERS
    )
    assert all(cm.marcas == frozenset() for cm in res)


def test_ventana_viene_de_la_politica_versionada():
    from Dominio.modelos import ORIGEN_PATRONAL, VersionParametro, Vigencia
    from datetime import date

    v10 = (
        VersionParametro(
            n.VENTANA_DUPLICADOS_S, minutos_a_segundos(10), Vigencia(date(2026, 1, 1)),
            "prueba", ORIGEN_PATRONAL,
        ),
    )
    res = marcar_checadas([ck("a", 8), ck("b", 8, 20), ck("c", 17)], v10)
    assert all(cm.marcas == frozenset() for cm in res)


def test_sin_politica_vigente_se_propaga_falta_parametro():
    with pytest.raises(n.FaltaParametro):
        marcar_checadas([ck("a", 8), ck("b", 8, 5)], ())


def test_futura_solo_si_se_entrega_instante_de_referencia():
    xs = [ck("a", 8), ck("b", 18)]
    ref = datetime(2027, 1, 4, 12, 0, tzinfo=CDMX)
    assert all(cm.marcas == frozenset() for cm in marcar_checadas(xs, VERS))
    m = marcas_de(marcar_checadas(xs, VERS, instante_referencia=ref))
    assert m == {"a": frozenset(), "b": frozenset({FUTURA})}


def test_futura_igual_a_la_referencia_no_es_futura():
    ref = datetime(2027, 1, 4, 8, 0, tzinfo=CDMX)
    res = marcar_checadas([ck("a", 8)], VERS, instante_referencia=ref)
    assert res[0].marcas == frozenset()


def test_referencia_sin_zona_se_rechaza():
    with pytest.raises(ValueError):
        marcar_checadas([ck("a", 8)], VERS, instante_referencia=datetime(2027, 1, 4, 12))


def test_desfase_solo_con_umbral_explicito_y_medido_por_quien_llama():
    xs = [ck("a", 8, desfase_s=minutos_a_segundos(7)), ck("b", 12, desfase_s=-30), ck("c", 17)]
    assert all(cm.marcas == frozenset() for cm in marcar_checadas(xs, VERS))
    m = marcas_de(marcar_checadas(xs, VERS, umbral_desfase_s=minutos_a_segundos(5)))
    assert m == {"a": frozenset({DESFASE}), "b": frozenset(), "c": frozenset()}


def test_desfase_negativo_grande_tambien_se_marca():
    m = marcas_de(
        marcar_checadas([ck("a", 8, desfase_s=-600)], VERS, umbral_desfase_s=300)
    )
    assert m["a"] == frozenset({DESFASE})


def test_una_checada_puede_tener_varias_marcas():
    ref = datetime(2027, 1, 4, 7, 0, tzinfo=CDMX)
    res = marcar_checadas(
        [ck("a", 8), ck("b", 8, 1, desfase_s=900), ck("c", 17)], VERS,
        instante_referencia=ref, umbral_desfase_s=60,
    )
    assert marcas_de(res)["b"] == frozenset({FUTURA, POSIBLE_DUPLICADO, DESFASE})


# --- B2: un duplicado no debe romper el emparejamiento ----------------------------------

def test_b2_salida_y_regreso_de_comida_en_el_mismo_reloj_no_son_duplicado():
    res = marcar_checadas([ck("a", 8), ck("b", 13), ck("c", 13, 30), ck("d", 18)], VERS)
    assert all(POSIBLE_DUPLICADO not in cm.marcas for cm in res)


def test_b2_duplicado_real_de_2_minutos_se_marca():
    res = marcar_checadas([ck("a", 8), ck("b", 8, 2), ck("c", 17)], VERS)
    assert marcas_de(res)["b"] == frozenset({POSIBLE_DUPLICADO})


def test_b2_dos_duplicados_reales_en_el_dia_se_marcan_juntos():
    res = marcar_checadas([ck("a", 8), ck("b", 8, 2), ck("c", 17), ck("d", 17, 1)], VERS)
    m = marcas_de(res)
    assert m["b"] == m["d"] == frozenset({POSIBLE_DUPLICADO})
    assert m["a"] == m["c"] == frozenset()


def test_b2_dos_checadas_solas_cercanas_no_se_marcan_porque_romperia_la_paridad():
    res = marcar_checadas([ck("a", 8), ck("b", 8, 20)], VERS)
    assert all(POSIBLE_DUPLICADO not in cm.marcas for cm in res)


def test_b2_misma_marca_de_tiempo_exacta_siempre_es_duplicado_aunque_cambie_la_paridad():
    # lote importado dos veces: la repeticion exacta no puede ser un par real de tiempo cero
    res = marcar_checadas([ck("a", 8), ck("a", 8), ck("b", 12)], VERS)
    assert sum(POSIBLE_DUPLICADO in cm.marcas for cm in res) == 1


def test_b2_la_paridad_cuenta_las_checadas_del_dia_de_todos_los_relojes():
    xs = [ck("a", 8, **dict(reloj="R-CATAB", empresa="CATAB")), ck("b", 13), ck("c", 13, 30), ck("d", 18)]
    assert all(POSIBLE_DUPLICADO not in cm.marcas for cm in marcar_checadas(xs, VERS))


def test_ventana_de_duplicados_por_empresa():
    from Dominio.modelos import ORIGEN_PATRONAL, VersionParametro, Vigencia
    from datetime import date

    vs = (
        *VERS,
        VersionParametro(n.VENTANA_DUPLICADOS_S, minutos_a_segundos(5), Vigencia(date(2026, 1, 1)),
                         "prueba", ORIGEN_PATRONAL, "CATAB"),
    )
    cks = [ck("a", 8, **dict(reloj="R-CATAB", empresa="CATAB")),
           ck("b", 8, 20, **dict(reloj="R-CATAB", empresa="CATAB")),
           ck("c", 17, **dict(reloj="R-CATAB", empresa="CATAB"))]
    assert all(cm.marcas == frozenset() for cm in marcar_checadas(cks, vs))  # 20 min > 5 min
    aei = [ck("a", 8), ck("b", 8, 20), ck("c", 17)]
    assert marcas_de(marcar_checadas(aei, vs))["b"] == frozenset({POSIBLE_DUPLICADO})


# --- Cercanas sin resolver: nunca en silencio (plan 5.1-4, RE05) ---------------------

def test_cercanas_no_duplicado_se_marcan_ambas_para_revision():
    # 08:00, 08:02, 12:00, 17:00: no se sabe cual es el duplicado
    m = marcas_de(marcar_checadas([ck("a", 8), ck("b", 8, 2), ck("c", 12), ck("d", 17)], VERS))
    assert m == {
        "a": frozenset({CERCANA_SIN_RESOLVER}),
        "b": frozenset({CERCANA_SIN_RESOLVER}),
        "c": frozenset(),
        "d": frozenset(),
    }


def test_cercanas_de_comida_tambien_se_marcan_para_revision_sin_ser_duplicado():
    m = marcas_de(marcar_checadas([ck("a", 8), ck("b", 13), ck("c", 13, 30), ck("d", 18)], VERS))
    assert m["b"] == m["c"] == frozenset({CERCANA_SIN_RESOLVER})
    assert m["a"] == m["d"] == frozenset()
