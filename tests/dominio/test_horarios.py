"""Horarios: HO01-HO07 (modelo, minutos ordinarios, compatibilidad, horario faltante) y
contexto del dia (doc. 03 8.2 paso 5). Casos P-33, P-39, P-41, P-49."""
from datetime import date
from zoneinfo import ZoneInfo

import pytest

from Dominio import normatividad as n
from Dominio.calendario import AL12, CalendarioAnual
from Dominio.horarios import (
    AL09,
    HO03,
    DescansoHorario,
    DiaHorario,
    Horario,
    HorarioAmbiguo,
    evaluar_compatibilidad,
    fin_de_jornada_previa,
    instantes_del_dia,
    resolver_contexto,
    resolver_horario,
)
from Dominio.modelos import Vigencia
from Dominio.tiempo import Intervalo, instante_local
from Dominio.tolerancias import CLAVES_TOLERANCIA, Tolerancias, version_de_tolerancia

CDMX = ZoneInfo("America/Mexico_City")
H, M = 3600, 60
VERS = (*n.SEMILLA_LEGAL, *n.SEMILLA_PATRONAL)
D2027 = Vigencia(date(2027, 1, 1), date(2028, 1, 1))


def hm(h, m=0):
    return h * H + m * M


def bloque(h1, h2, m1=0, m2=0):
    return Intervalo(hm(h1, m1), hm(h2, m2))


def dia(*intervalos, descansos=()):
    return DiaHorario(tuple(intervalos), tuple(descansos))


def horario(dias, vigencia=D2027, **kw):
    kw.setdefault("codigo", "H1")
    kw.setdefault("regimen", "diurna")
    kw.setdefault("zona", "America/Mexico_City")
    return Horario(vigencia=vigencia, dias=dias, **kw)


def comida(h1, m1, h2, m2, computable):
    return DescansoHorario(bloque(h1, h2, m1, m2), computable)


def cinco_por_ocho_mas_seis():
    """5 x 8 (07:00-16:00, comida no computable 12-13) + sabado 6 h continuas (46 h)."""
    laboral = dia(bloque(7, 16), descansos=[comida(12, 0, 13, 0, False)])
    return horario({d: laboral for d in range(5)} | {5: dia(bloque(7, 13))}, descansos_semanales=frozenset({6}))


# --- HO01 / HO02 -------------------------------------------------------------------------

def test_ho02_minutos_ordinarios_descuentan_solo_descansos_no_computables():
    assert dia(bloque(7, 16), descansos=[comida(12, 0, 13, 0, False)]).ordinarios_s == 8 * H
    assert dia(bloque(7, 16), descansos=[comida(12, 0, 12, 30, True)]).ordinarios_s == 9 * H
    assert dia(bloque(7, 12), bloque(13, 16)).ordinarios_s == 8 * H  # turno partido: el hueco no cuenta


def test_ho02_total_semanal_5x8_mas_6_es_46_horas():
    assert cinco_por_ocho_mas_seis().ordinarios_semana_s == 46 * H


def test_p39_seis_dias_de_7_h_40_min_son_46_h_exactas():
    sem = horario({d: dia(bloque(7, 14, 0, 40)) for d in range(6)})
    assert sem.ordinarios_semana_s == 46 * H


def test_ho01_distribucion_2028_5x7h36_mas_6h_son_44_h():
    sem = horario({d: dia(bloque(7, 14, 0, 36)) for d in range(5)} | {5: dia(bloque(7, 13))})
    assert sem.ordinarios_semana_s == 44 * H


def test_ho01_turno_nocturno_cruza_medianoche_y_suma_7_h():
    nocturno = dia(bloque(22, 29))  # 22:00 a 05:00 del dia siguiente
    assert nocturno.ordinarios_s == 7 * H


def test_horario_rechaza_estructuras_invalidas():
    with pytest.raises(ValueError):
        dia(bloque(7, 12), bloque(11, 16))  # traslape
    with pytest.raises(ValueError):
        dia(bloque(7, 16), descansos=[comida(16, 0, 17, 0, False)])  # descanso fuera del intervalo
    with pytest.raises(ValueError):
        dia()  # sin intervalos
    with pytest.raises(ValueError):
        dia(Intervalo(0, 49 * H))  # mas de 48 h desde el inicio del dia
    with pytest.raises(ValueError):
        horario({7: dia(bloque(7, 16))})  # dia de la semana fuera de 0..6
    with pytest.raises(ValueError):
        horario({0: dia(bloque(7, 16))}, descansos_semanales=frozenset({0}))  # programado y descanso
    with pytest.raises(ValueError):
        horario({0: dia(bloque(7, 16))}, regimen="inexistente")
    with pytest.raises(ValueError):
        horario({0: dia(bloque(7, 16))}, zona="Nunca/Jamas")


def test_ho05_el_horario_distingue_programado_descanso_semanal_y_no_programado():
    h = cinco_por_ocho_mas_seis()
    assert h.programado(0) and not h.programado(6)
    assert h.es_descanso_semanal(6) and not h.es_descanso_semanal(5)


# --- HO04 / HO06: horario vigente --------------------------------------------------------

def test_ho04_resuelve_el_horario_por_vigencia_y_rechaza_traslapes():
    h26 = horario({0: dia(bloque(7, 16))}, Vigencia(date(2026, 1, 1), date(2027, 1, 1)), codigo="H26")
    h27 = horario({0: dia(bloque(7, 15))}, codigo="H27")
    assert resolver_horario([h26, h27], date(2026, 12, 31)).codigo == "H26"
    assert resolver_horario([h26, h27], date(2027, 1, 1)).codigo == "H27"
    solapado = horario({0: dia(bloque(8, 16))}, Vigencia(date(2027, 6, 1), date(2027, 7, 1)), codigo="X")
    with pytest.raises(HorarioAmbiguo):
        resolver_horario([h27, solapado], date(2027, 6, 15))


def test_ho06_sin_horario_vigente_devuelve_none_sin_inventar_un_defecto():
    assert resolver_horario([], date(2027, 3, 1)) is None
    h = horario({0: dia(bloque(7, 16))})
    assert resolver_horario([h], date(2026, 12, 31)) is None  # aun no vigente


def test_p49_un_horario_futuro_no_afecta_el_calculo_actual():
    futuro = horario({0: dia(bloque(7, 15))}, Vigencia(date(2028, 1, 1)), codigo="F")
    assert resolver_horario([futuro], date(2027, 6, 1)) is None


# --- instantes del dia / jornada logica ------------------------------------------------------

def test_instantes_del_dia_convierte_horario_a_epoch_con_descansos():
    h = cinco_por_ocho_mas_seis()
    lunes = date(2027, 1, 4)
    programados, descansos = instantes_del_dia(h, lunes)
    assert programados == (Intervalo(instante_local(lunes, hm(7), CDMX), instante_local(lunes, hm(16), CDMX)),)
    assert [(d.intervalo.duracion, d.computable) for d in descansos] == [(H, False)]
    assert instantes_del_dia(h, date(2027, 1, 10)) == ((), ())  # domingo: sin programacion


def test_fin_de_jornada_previa_solo_para_turnos_que_cruzan_medianoche():
    nocturno = horario({0: dia(bloque(22, 29))})
    previa = fin_de_jornada_previa([nocturno], CDMX)
    assert previa(date(2027, 1, 4)) == instante_local(date(2027, 1, 5), hm(5), CDMX)
    assert previa(date(2027, 1, 5)) is None  # martes sin horario
    assert fin_de_jornada_previa([cinco_por_ocho_mas_seis()], CDMX)(date(2027, 1, 4)) is None


# --- HO03 / HO07 / P-41: compatibilidad ----------------------------------------------------------

def horario_48h(vigencia=D2027, **kw):
    return horario({d: dia(bloque(7, 15)) for d in range(6)}, vigencia, **kw)  # 6 x 8 = 48 h


def test_p41_horario_de_48_h_en_2027_advierte_incompatibilidad_con_ho03():
    c = evaluar_compatibilidad(horario_48h(), VERS, date(2027, 3, 1))
    assert c.semanal_s == 48 * H and c.tope_semanal_s == 46 * H
    assert c.compatible is False
    assert "semanal_excede_tope" in c.advertencias and HO03 in c.alertas


def test_p41_el_mismo_horario_en_2026_es_compatible():
    c = evaluar_compatibilidad(horario_48h(Vigencia(date(2026, 1, 1), date(2027, 1, 1))), VERS, date(2026, 6, 1))
    assert c.compatible is True and c.advertencias == () and c.alertas == ()


def test_ho07_horario_de_siguiente_anio_incompatible_emite_al09_no_ho03():
    c = evaluar_compatibilidad(horario_48h(), VERS, date(2027, 3, 1), fecha_referencia=date(2026, 11, 26))
    assert c.compatible is False
    assert AL09 in c.alertas and HO03 not in c.alertas


def test_ho03_el_horario_de_46_h_en_2027_es_compatible_y_en_2030_no():
    h = cinco_por_ocho_mas_seis()
    assert evaluar_compatibilidad(h, VERS, date(2027, 3, 1)).compatible is True
    c30 = evaluar_compatibilidad(h, VERS, date(2030, 3, 1))
    assert c30.tope_semanal_s == 40 * H and c30.compatible is False


def test_ho03_dia_sobre_el_tope_diario_exige_acuerdo_art_58():
    largo = horario({d: dia(bloque(7, 17)) for d in range(4)})  # 4 x 10 h = 40 h
    sin = evaluar_compatibilidad(largo, VERS, date(2027, 3, 1))
    assert "diario_excede_tope_sin_acuerdo" in sin.advertencias and sin.dias_sin_acuerdo == (0, 1, 2, 3)
    con = evaluar_compatibilidad(
        horario({d: dia(bloque(7, 17)) for d in range(4)}, referencia_acuerdo="Acuerdo art. 58 2027-01"),
        VERS, date(2027, 3, 1),
    )
    assert con.advertencias == () and con.compatible is True


def test_ho03_dia_sobre_12_horas_se_rechaza_como_ordinario_aun_con_acuerdo():
    extremo = horario({d: dia(bloque(6, 19)) for d in range(3)}, referencia_acuerdo="Acuerdo")  # 13 h
    c = evaluar_compatibilidad(extremo, VERS, date(2027, 3, 1))
    assert "diario_excede_total_12h" in c.advertencias and c.dias_sobre_total_diario == (0, 1, 2)


def test_ho03_regimen_sin_tope_diario_propio_no_lo_evalua():
    parcial = horario({d: dia(bloque(7, 11)) for d in range(5)}, regimen="parcial")
    c = evaluar_compatibilidad(parcial, VERS, date(2027, 3, 1))
    assert c.compatible is True and c.dias_sin_acuerdo == ()


def test_ho03_sin_norma_vigente_queda_provisional_con_al12():
    c = evaluar_compatibilidad(horario_48h(Vigencia(date(2025, 1, 1), date(2026, 1, 1))), VERS, date(2025, 6, 1))
    assert c.provisional is True and AL12 in c.alertas and c.compatible is False


# --- resolver_contexto (paso 5) / P-33 -------------------------------------------------------------

def _tol(minutos=10, empresa="AEI"):
    return [version_de_tolerancia(k, minutos, Vigencia(date(2027, 1, 1)), "prueba", empresa) for k in CLAVES_TOLERANCIA]


def _cal(confirmado=True):
    return CalendarioAnual(2027, frozenset({date(2027, 5, 1)}), confirmado=confirmado)


def test_contexto_completo_no_es_provisional():
    ctx = resolver_contexto(date(2027, 3, 3), [cinco_por_ocho_mas_seis()], [_cal()], (*VERS, *_tol()), "AEI")
    assert ctx.provisional is False and ctx.alertas == ()
    assert ctx.horario.codigo == "H1" and ctx.dia_horario.ordinarios_s == 8 * H
    assert ctx.tope_semanal_s == 46 * H and ctx.tope_diario_s == 8 * H
    assert ctx.tolerancias.entrada_tardia_s == 10 * M and ctx.calendario.anio == 2027


def test_p33_sin_horario_el_contexto_es_provisional_con_al12_y_sin_8h_ni_48h_por_defecto():
    ctx = resolver_contexto(date(2027, 3, 3), [], [_cal()], (*VERS, *_tol()), "AEI")
    assert ctx.provisional is True and AL12 in ctx.alertas and "horario_faltante" in ctx.motivos
    assert ctx.horario is None and ctx.dia_horario is None
    assert ctx.tope_diario_s is None  # no se inventan 8 h; el regimen sale del horario


def test_contexto_marca_cada_dato_faltante_sin_lanzar_excepcion():
    ctx = resolver_contexto(date(2027, 3, 3), [cinco_por_ocho_mas_seis()], [], n.SEMILLA_LEGAL, "AEI")
    assert ctx.provisional is True and AL12 in ctx.alertas
    assert {"calendario_faltante", f"falta:{n.TOL_ENTRADA_ANTICIPADA_S}"} <= set(ctx.motivos)
    assert ctx.tolerancias is None and ctx.calendario is None
    assert ctx.horario is not None  # lo que si hay se conserva


def test_contexto_calendario_sin_confirmar_es_provisional():
    ctx = resolver_contexto(date(2027, 3, 3), [cinco_por_ocho_mas_seis()], [_cal(False)], (*VERS, *_tol()), "AEI")
    assert ctx.provisional is True and "calendario_sin_confirmar" in ctx.motivos


def test_contexto_toma_las_tolerancias_del_horario_antes_que_las_de_la_empresa():
    propias = Tolerancias.desde_minutos(0, 3, 0, 0, 0)
    h = horario({0: dia(bloque(7, 16))}, tolerancias=propias)
    ctx = resolver_contexto(date(2027, 3, 1), [h], [_cal()], (*VERS, *_tol()), "AEI")
    assert ctx.tolerancias == propias


def test_contexto_usa_la_empresa_del_horario_para_resolver_tolerancias():
    h = horario({0: dia(bloque(7, 16))}, empresa="CATAB")
    vers = (*VERS, *_tol(5, "AEI"), *_tol(12, "CATAB"))
    assert resolver_contexto(date(2027, 3, 1), [h], [_cal()], vers).tolerancias.entrada_tardia_s == 12 * M


# --- Correccion T3: configuracion invalida degrada a provisional; zona del horario ---------------

def test_i2_contexto_con_horarios_ambiguos_no_elige_uno_y_es_provisional():
    a = horario({0: dia(bloque(7, 16))}, codigo="A")
    b = horario({0: dia(bloque(8, 17))}, codigo="B")
    ctx = resolver_contexto(date(2027, 3, 1), [a, b], [_cal()], (*VERS, *_tol()), "AEI")
    assert ctx.provisional is True and AL12 in ctx.alertas and "horario_ambiguo" in ctx.motivos
    assert ctx.horario is None and ctx.dia_horario is None


def test_i2_contexto_con_calendarios_duplicados_y_tolerancia_invalida_no_aborta():
    from Dominio.modelos import ORIGEN_PATRONAL, VersionParametro

    malas = _tol()
    malas[1] = VersionParametro(n.TOL_ENTRADA_TARDIA_S, 16 * M, Vigencia(date(2027, 1, 1)), "x", ORIGEN_PATRONAL, "AEI")
    ctx = resolver_contexto(date(2027, 3, 1), [cinco_por_ocho_mas_seis()], [_cal(), _cal()], (*VERS, *malas), "AEI")
    assert ctx.provisional is True and AL12 in ctx.alertas
    assert {"calendario_ambiguo", f"tolerancia_invalida:{n.TOL_ENTRADA_TARDIA_S}"} <= set(ctx.motivos)
    assert ctx.horario is not None and ctx.tolerancias is None and ctx.calendario is None


def test_n3_fin_de_jornada_previa_usa_la_zona_propia_del_horario():
    tijuana = ZoneInfo("America/Tijuana")
    nocturno = horario({0: dia(bloque(22, 29))}, zona="America/Tijuana")
    previa = fin_de_jornada_previa([nocturno])
    assert previa(date(2027, 1, 4)) == instante_local(date(2027, 1, 5), hm(5), tijuana)
    assert fin_de_jornada_previa([nocturno], tijuana)(date(2027, 1, 4)) == previa(date(2027, 1, 4))


def test_n3_una_zona_distinta_a_la_del_horario_se_rechaza_sin_discrepar_en_silencio():
    nocturno = horario({0: dia(bloque(22, 29))}, zona="America/Tijuana")
    with pytest.raises(ValueError):
        fin_de_jornada_previa([nocturno], CDMX)


def test_i2_fin_de_jornada_previa_ignora_horarios_ambiguos():
    a = horario({0: dia(bloque(22, 29))}, codigo="A")
    b = horario({0: dia(bloque(22, 28))}, codigo="B")
    assert fin_de_jornada_previa([a, b])(date(2027, 1, 4)) is None
