"""Tramos de extra (plan 5.3, doc. 03 8.2 paso 11): doble hasta el tope art. 66 semanal, el resto triple;
limites de 4 h/dia, 4 dias/semana (art. 66) y 12 h totales por dia (art. 68), cada uno evaluado por
separado; exceso legal como etiqueta (el tiempo se conserva integro); lo que cae fuera de la distribucion
art. 66 queda `extra_pendiente_clasificacion` (propuesta doc. 03 8.2-11, por validar con el asesor).
Casos: P-08 a P-17, P-35, P-38, P-40, P-47 (parte pura), P-01 a P-05 en tramos, mas el tope art. 61
leido del tipo declarado y propiedades con semillas fijas. Todo tope sale de `resolver_vigente`."""
import random
from dataclasses import replace
from datetime import date, timedelta

from Dominio import normatividad as n
from Dominio.calendario import AL12
from Dominio.criterios_extra import asignar_extra
from Dominio.horarios import CONFIRMADO, HO03, PENDIENTE as ESTADO_PENDIENTE
from Dominio.modelos import VersionParametro, Vigencia
from Dominio.segmentacion import (
    BANDA_DIURNA,
    CLASE_DENTRO,
    CLASE_EXCESO,
    CLASE_SIN_CLASIFICAR,
    ResultadoSegmentacion,
    Segmento,
)
from Dominio.tiempo import Intervalo
from Dominio.tramos_extra import (
    AL02,
    AL03,
    AUT_AUTORIZADA,
    AUT_NO_AUTORIZADA,
    AUT_SIN_REGISTRO,
    AVISO_ART66_ALCANZADO,
    AVISO_ART66_PREVENTIVO,
    AVISO_ART66_SUPERADO,
    AVISO_ART68_ALCANZADO,
    AVISO_ART68_SUPERADO,
    AVISO_DISTRIBUCION_DIARIA,
    AVISO_DISTRIBUCION_DIAS,
    AVISO_TOTAL_DIARIO_ALCANZADO,
    AVISO_TOTAL_DIARIO_SUPERADO,
    CAT_DOBLE,
    CAT_ORDINARIO,
    CAT_PENDIENTE,
    CAT_POR_CLASIFICAR,
    CAT_TRIPLE,
    ETQ_EXCESO_LEGAL,
    Autorizacion,
    repartir_tramos,
)
from _semanas_extra import (
    BASE,
    H,
    LUN_2026,
    LUN_2027,
    LUN_2028,
    LUN_2029,
    LUN_2030,
    M,
    PROGRAMA_40,
    PROGRAMA_42,
    PROGRAMA_44,
    PROGRAMA_46,
    PROGRAMA_48,
    dia_de,
    segmentar_semana,
    t,
)


def exacto(programa):
    return {d: list(p) for d, p in programa.items()}


def clasificar(lunes, trabajado, programa=None, *, autorizaciones=(), extra=(), **kw):
    versiones = tuple(BASE) + tuple(extra)
    seg, versiones = segmentar_semana(lunes, trabajado, programa, versiones=versiones, **kw)
    asignaciones = asignar_extra(seg, versiones)
    assert len(asignaciones) == 1
    return repartir_tramos(asignaciones[0], versiones, autorizaciones)


def horas(res):
    """(ordinario, doble, triple, pendiente): suma las dos categorias de pendiente (ver `test_q_e_*`)."""
    pendiente = res.total_s(CAT_PENDIENTE) + res.total_s(CAT_POR_CLASIFICAR)
    return tuple(res.total_s(c) for c in (CAT_ORDINARIO, CAT_DOBLE, CAT_TRIPLE)) + (pendiente,)


def piezas(res, categoria):
    return [(c.segmento.intervalo.inicio, c.segmento.intervalo.fin) for c in res.segmentos if c.categoria == categoria]


def con_extras(programa, **horas_por_dia):
    """Trabajado = programa + salida mas tarde: `extras(lun=3)` sale 3 h despues de las 16:00."""
    nombres = {"lun": 0, "mar": 1, "mie": 2, "jue": 3, "vie": 4, "sab": 5}
    trabajado = exacto(programa)
    for nombre, extra in horas_por_dia.items():
        d = nombres[nombre]
        ini, fin = trabajado[d][-1]
        h, m = (extra, 0) if not isinstance(extra, tuple) else extra
        trabajado[d][-1] = (ini, ((fin if isinstance(fin, int) else fin[0]) + h, m))
    return trabajado


# --- Doble hasta el tope art. 66, el resto triple (P-08 a P-14) ----------------------------------

def test_p08_2027_nueve_horas_extra_distribuidas_validamente_son_9_dobles_y_aviso_de_tope_alcanzado():
    res = clasificar(LUN_2027, con_extras(PROGRAMA_46, lun=3, mar=3, mie=3))
    assert horas(res) == (46 * H, 9 * H, 0, 0)
    assert AVISO_ART66_ALCANZADO in res.avisos and AVISO_ART66_SUPERADO not in res.avisos
    assert "AL04" in res.alertas and AL02 in res.alertas
    assert res.provisional is False


def test_p09_2027_nueve_horas_y_un_minuto_son_9_dobles_y_1_minuto_triple_con_aviso_de_excedente():
    res = clasificar(LUN_2027, con_extras(PROGRAMA_46, lun=3, mar=3, mie=(3, 1)))
    assert horas(res) == (46 * H, 9 * H, M, 0)
    assert piezas(res, CAT_TRIPLE) == [(t(dia_de(LUN_2027, 2), 19), t(dia_de(LUN_2027, 2), (19, 1)))]
    assert AVISO_ART66_SUPERADO in res.avisos and "AL04" in res.alertas


def test_p10_2027_trece_horas_extra_alcanzan_el_limite_agregado_art_66_mas_art_68():
    res = clasificar(LUN_2027, con_extras(PROGRAMA_46, lun=4, mar=4, mie=4, jue=1))
    assert horas(res) == (46 * H, 9 * H, 4 * H, 0)
    assert AVISO_ART68_ALCANZADO in res.avisos and AVISO_ART68_SUPERADO not in res.avisos
    assert "AL06" in res.alertas
    assert not any(ETQ_EXCESO_LEGAL in c.etiquetas for c in res.segmentos)


def test_p11_2027_trece_horas_y_un_minuto_alerta_critica_y_el_minuto_excedente_se_conserva_como_exceso_legal():
    res = clasificar(LUN_2027, con_extras(PROGRAMA_46, lun=4, mar=4, mie=4, jue=(1, 1)))
    assert horas(res) == (46 * H, 9 * H, 4 * H + M, 0)  # sin cuarta categoria de pago: sigue siendo triple
    legal = [c for c in res.segmentos if ETQ_EXCESO_LEGAL in c.etiquetas]
    assert [c.segmento.intervalo.duracion for c in legal] == [M] and legal[0].categoria == CAT_TRIPLE
    assert AVISO_ART68_SUPERADO in res.avisos and "AL06" in res.alertas
    assert res.confirmado_s == 46 * H + 13 * H + M  # tiempo integro


def test_p12_2028_diez_horas_y_luego_un_minuto_el_cruce_doble_triple_esta_en_10_h():
    res = clasificar(LUN_2028, con_extras(PROGRAMA_44, lun=4, mar=4, mie=(2, 1)), PROGRAMA_44)
    assert horas(res) == (44 * H, 10 * H, M, 0)
    assert piezas(res, CAT_TRIPLE) == [(t(dia_de(LUN_2028, 2), 18), t(dia_de(LUN_2028, 2), (18, 1)))]


def test_p13_2029_once_horas_y_luego_un_minuto_el_cruce_esta_en_11_h():
    res = clasificar(LUN_2029, con_extras(PROGRAMA_42, lun=4, mar=4, mie=(3, 1)), PROGRAMA_42)
    assert horas(res) == (42 * H, 11 * H, M, 0)


def test_p14_2030_doce_horas_y_luego_un_minuto_el_cruce_esta_en_12_h():
    res = clasificar(LUN_2030, con_extras(PROGRAMA_40, lun=4, mar=4, mie=4, jue=(0, 1)), PROGRAMA_40)
    assert horas(res) == (40 * H, 12 * H, M, 0)
    assert piezas(res, CAT_TRIPLE) == [(t(dia_de(LUN_2030, 3), 16), t(dia_de(LUN_2030, 3), (16, 1)))]


def test_p03_p04_p05_extras_en_distribucion_valida_de_2028_a_2030_son_dobles():
    p03 = clasificar(LUN_2028, con_extras(PROGRAMA_44, lun=2, mar=2), PROGRAMA_44)
    assert horas(p03) == (44 * H, 4 * H, 0, 0)
    p04 = clasificar(LUN_2029, con_extras(PROGRAMA_42, lun=2, mar=2, mie=2), PROGRAMA_42)
    assert horas(p04) == (42 * H, 6 * H, 0, 0)
    p05 = clasificar(LUN_2030, con_extras(PROGRAMA_40, lun=2, mar=2, mie=2, jue=2), PROGRAMA_40)
    assert horas(p05) == (40 * H, 8 * H, 0, 0)


def test_p01_2026_sin_extra_no_hay_dobles_ni_alerta_de_extra():
    res = clasificar(LUN_2026, exacto(PROGRAMA_48), PROGRAMA_48)
    assert horas(res) == (48 * H, 0, 0, 0) and res.alertas == ()


# --- Distribucion art. 66 y total diario art. 68: alertas independientes, tiempo integro --------

def test_p15_mas_de_4h_art_66_en_un_dia_y_mas_de_12h_totales_son_alertas_independientes_sin_perder_tiempo():
    trabajado = {**exacto(PROGRAMA_46), 0: [(6, 22)]}  # lunes: 2 h antes y 6 h despues del horario; total 16 h
    res = clasificar(LUN_2027, trabajado)
    assert res.confirmado_s == 54 * H
    assert horas(res) == (46 * H, 4 * H, 0, 4 * H)
    assert {AVISO_DISTRIBUCION_DIARIA, AVISO_TOTAL_DIARIO_SUPERADO} <= res.avisos
    assert {"AL05", "AL07"} <= set(res.alertas)
    pendientes = [c for c in res.segmentos if c.categoria == CAT_PENDIENTE]
    assert all(c.motivo == "fuera_distribucion_art66:diario" for c in pendientes)
    legales = sum(c.segmento.intervalo.duracion for c in res.segmentos if ETQ_EXCESO_LEGAL in c.etiquetas)
    assert legales == 4 * H  # las horas 13 a 16 del dia (18:00-22:00)


def test_p16_extras_art_66_en_cinco_dias_con_solo_5h_semanales_alertan_la_distribucion():
    trabajado = {d: [(8, 17)] for d in range(5)} | {5: [(8, 14)]}  # 1 h extra de lunes a viernes
    res = clasificar(LUN_2027, trabajado)
    assert horas(res) == (46 * H, 4 * H, 0, H)  # el quinto dia queda fuera de la distribucion: pendiente
    assert AVISO_DISTRIBUCION_DIAS in res.avisos and "AL05" in res.alertas
    assert AVISO_ART66_ALCANZADO not in res.avisos  # 5 h < 9 h: la alerta es de distribucion, no de tope
    (pendiente,) = [c for c in res.segmentos if c.categoria == CAT_PENDIENTE]
    assert pendiente.motivo == "fuera_distribucion_art66:dias"
    assert pendiente.segmento.dia_logico == dia_de(LUN_2027, 4)


def test_p17_jornada_total_de_12h_exactas_alcanza_el_limite_y_12h_1min_lo_supera():
    exactas = clasificar(LUN_2027, con_extras(PROGRAMA_46, lun=4))
    assert AVISO_TOTAL_DIARIO_ALCANZADO in exactas.avisos and AVISO_TOTAL_DIARIO_SUPERADO not in exactas.avisos
    assert "AL07" in exactas.alertas
    assert not any(ETQ_EXCESO_LEGAL in c.etiquetas for c in exactas.segmentos)
    superada = clasificar(LUN_2027, con_extras(PROGRAMA_46, lun=(4, 1)))
    assert AVISO_TOTAL_DIARIO_SUPERADO in superada.avisos
    legal = [c for c in superada.segmentos if ETQ_EXCESO_LEGAL in c.etiquetas]
    assert [c.segmento.intervalo.duracion for c in legal] == [M]  # el minuto 12h01 se conserva y se etiqueta
    assert superada.confirmado_s == 46 * H + 4 * H + M


def test_el_plan_52_cinco_por_ocho_mas_seis_a_9_horas_alerta_el_limite_de_4_dias_sin_borrar_tiempo():
    res = clasificar(LUN_2027, {d: [(8, 17)] for d in range(6)})  # 54 h: 8 h de extra en seis dias
    assert res.confirmado_s == 54 * H and res.extra_s == 8 * H
    assert horas(res)[1:] == (4 * H, 0, 4 * H)  # lunes a jueves en distribucion; viernes y sabado pendientes
    assert AVISO_DISTRIBUCION_DIAS in res.avisos


def test_los_limites_diario_dias_y_total_salen_de_la_version_vigente_no_del_codigo():
    otros = tuple(
        VersionParametro(c, v, Vigencia(date(2026, 1, 1)), "prueba")
        for c, v in ((n.ART66_DIARIO_S, 2 * H), (n.ART66_DIAS_SEMANA, 2))
    )
    versiones = tuple(v for v in BASE if v.clave not in (n.ART66_DIARIO_S, n.ART66_DIAS_SEMANA)) + otros
    res = clasificar(LUN_2027, con_extras(PROGRAMA_46, lun=3, mar=3, mie=3), extra=otros)  # BASE aun tiene 4 h / 4 d
    assert res.provisional and f"parametro_ambiguo:{n.ART66_DIARIO_S}" in res.motivos  # duplicado: no se elige uno
    seg, vers = segmentar_semana(LUN_2027, con_extras(PROGRAMA_46, lun=3, mar=3, mie=3), versiones=versiones)
    res2 = repartir_tramos(asignar_extra(seg, vers)[0], vers)
    assert horas(res2) == (46 * H, 4 * H, 0, 5 * H)  # 2 h el lunes y 2 h el martes; el resto, fuera de la distribucion


# --- P-35: corregir el lunes cambia el acumulado del viernes y su cruce doble/triple ---------------

def test_p35_corregir_el_lunes_recalcula_el_viernes_y_mueve_el_cruce_doble_triple():
    antes = clasificar(LUN_2027, con_extras(PROGRAMA_46, lun=2, mie=4, jue=3, vie=3))  # 12 h de extra
    assert horas(antes) == (46 * H, 9 * H, 3 * H, 0)
    viernes = lambda r, c: [x for x in r.segmentos if x.categoria == c and x.segmento.dia_logico == dia_de(LUN_2027, 4)]
    assert not viernes(antes, CAT_DOBLE) and sum(x.segmento.intervalo.duracion for x in viernes(antes, CAT_TRIPLE)) == 3 * H
    despues = clasificar(LUN_2027, con_extras(PROGRAMA_46, lun=1, mie=4, jue=3, vie=3))  # el lunes se corrige a 1 h
    assert horas(despues) == (46 * H, 9 * H, 2 * H, 0)
    assert sum(x.segmento.intervalo.duracion for x in viernes(despues, CAT_DOBLE)) == H
    assert piezas(despues, CAT_TRIPLE)[-1][0] == t(dia_de(LUN_2027, 4), 17)  # el cruce se movio de 16:00 a 17:00


# --- P-38: la autorizacion es un atributo independiente; el tiempo se conserva ---------------------

def test_p38_extra_no_autorizada_pero_trabajada_conserva_el_tiempo_y_la_etiqueta_de_autorizacion():
    lunes, martes, miercoles = (dia_de(LUN_2027, d) for d in range(3))
    autorizaciones = (
        Autorizacion(Intervalo(t(lunes, 16), t(lunes, 18)), True),
        Autorizacion(Intervalo(t(martes, 16), t(martes, 18)), False),
    )
    res = clasificar(LUN_2027, con_extras(PROGRAMA_46, lun=2, mar=2, mie=2), autorizaciones=autorizaciones)
    assert horas(res) == (46 * H, 6 * H, 0, 0)  # lo no autorizado igual cuenta como extra trabajada
    por_dia = {c.segmento.dia_logico: c.autorizacion for c in res.segmentos if c.categoria == CAT_DOBLE}
    assert por_dia == {lunes: AUT_AUTORIZADA, martes: AUT_NO_AUTORIZADA, miercoles: AUT_SIN_REGISTRO}
    assert all(c.autorizacion is None for c in res.segmentos if c.categoria == CAT_ORDINARIO)


def test_la_autorizacion_parcial_divide_la_extra_exactamente_en_el_limite():
    lunes = dia_de(LUN_2027, 0)
    parcial = (Autorizacion(Intervalo(t(lunes, 16), t(lunes, 17)), True),)
    res = clasificar(LUN_2027, con_extras(PROGRAMA_46, lun=3), autorizaciones=parcial)
    partes = [(c.segmento.intervalo.duracion, c.autorizacion) for c in res.segmentos if c.categoria == CAT_DOBLE]
    assert partes == [(H, AUT_AUTORIZADA), (2 * H, AUT_SIN_REGISTRO)]


def test_los_avisos_semanales_leen_el_tope_art_66_en_la_fecha_de_la_ultima_extra():
    # Semana 27/12/2027-02/01/2028: el tope art. 66 pasa de 9 h a 10 h. Se fija el ordinario en 46 h todo el
    # periodo para aislar este efecto; 9 h 30 de extra con la ultima extra en 2028 (tope 10 h) no superan el tope.
    ordinario = VersionParametro(n.ORDINARIA_SEMANAL_S, 46 * H, Vigencia(date(2026, 1, 1)), "prueba")
    versiones = tuple(v for v in BASE if v.clave != n.ORDINARIA_SEMANAL_S) + (ordinario,)
    lunes = date(2027, 12, 27)
    trabajado = {**exacto(PROGRAMA_46), 2: [(8, 20)], 3: [(8, 20)], 5: [(8, (15, 30))]}
    seg, vers = segmentar_semana(lunes, trabajado, versiones=versiones)
    res = repartir_tramos(asignar_extra(seg, vers)[0], vers)
    assert res.extra_s == 9 * H + 30 * M and res.total_s(CAT_TRIPLE) == 0
    assert AVISO_ART66_SUPERADO not in res.avisos and AVISO_ART66_ALCANZADO not in res.avisos


def test_un_tope_que_baja_a_mitad_de_semana_no_produce_tiempo_negativo_ni_pierde_segundos():
    miercoles = dia_de(LUN_2027, 2)
    topes = (
        VersionParametro(n.ART66_SEMANAL_S, 9 * H, Vigencia(date(2026, 1, 1), miercoles), "prueba"),
        VersionParametro(n.ART66_SEMANAL_S, 1 * H, Vigencia(miercoles), "prueba"),
    )
    versiones = tuple(v for v in BASE if v.clave != n.ART66_SEMANAL_S) + topes
    seg, vers = segmentar_semana(LUN_2027, con_extras(PROGRAMA_46, lun=4, mar=4, mie=2), versiones=versiones)
    res = repartir_tramos(asignar_extra(seg, vers)[0], vers)
    assert horas(res) == (46 * H, 8 * H, 2 * H, 0) and min(horas(res)) >= 0  # el miercoles ya todo es triple


def sin(*claves):
    return tuple(v for v in BASE if v.clave not in claves)


def _con_versiones(versiones, trabajado, programa=None):
    seg, vers = segmentar_semana(LUN_2027, trabajado, programa, versiones=versiones)
    return repartir_tramos(asignar_extra(seg, vers)[0], vers)


# --- P-47: aviso preventivo con anticipacion configurable (parte pura) ----------------------------

def test_p47_umbral_preventivo_de_8h_con_acumulado_7_59_sin_aviso_y_8_00_con_aviso():
    # La anticipacion general de 60 min sale de la semilla patronal versionada (decision Q-I, 28/11/2026).
    justo_antes = clasificar(LUN_2027, con_extras(PROGRAMA_46, lun=4, mar=(3, 59)))
    assert AVISO_ART66_PREVENTIVO not in justo_antes.avisos and AL03 not in justo_antes.alertas
    en_el_umbral = clasificar(LUN_2027, con_extras(PROGRAMA_46, lun=4, mar=4))
    assert AVISO_ART66_PREVENTIVO in en_el_umbral.avisos and AL03 in en_el_umbral.alertas
    assert AVISO_ART66_ALCANZADO not in en_el_umbral.avisos  # 8 h < 9 h: solo preventivo


def test_la_anticipacion_de_la_empresa_gana_a_la_general_sembrada():
    propia = VersionParametro(n.ANTICIPACION_PREVENTIVA_S, 120 * M, Vigencia(date(2026, 1, 1)), "prueba", "patronal", "AEI")
    seg, versiones = segmentar_semana(LUN_2027, con_extras(PROGRAMA_46, lun=4, mar=3), versiones=tuple(BASE) + (propia,))
    asig = asignar_extra(seg, versiones)[0]  # 7 h de extra
    assert AVISO_ART66_PREVENTIVO not in repartir_tramos(asig, versiones).avisos  # general: 60 min -> desde 8 h
    assert AVISO_ART66_PREVENTIVO in repartir_tramos(asig, versiones, empresa="AEI").avisos  # AEI: 120 min -> desde 7 h
    assert AVISO_ART66_PREVENTIVO not in repartir_tramos(asig, versiones, empresa="CATAB").avisos


def test_sin_anticipacion_configurada_no_hay_aviso_preventivo_ni_provisional():
    versiones = sin(n.ANTICIPACION_PREVENTIVA_S)
    res = _con_versiones(versiones, con_extras(PROGRAMA_46, lun=4, mar=4))
    assert AVISO_ART66_PREVENTIVO not in res.avisos and res.provisional is False


# --- P-40: ene-abr 2026 con la norma anterior (3 h diarias, 3 dias), sin limites de la reforma -----

def test_p40_enero_2026_usa_la_distribucion_anterior_y_queda_provisional_por_no_tener_art_68_documentado():
    lunes = date(2026, 1, 5)
    res = clasificar(lunes, con_extras(PROGRAMA_48, lun=4), PROGRAMA_48)
    assert horas(res) == (48 * H, 3 * H, 0, H)  # 3 h diarias (norma anterior), no 4 h
    assert res.provisional and AL12 in res.alertas
    assert f"falta:{n.ART68_SEMANAL_S}" in res.motivos and f"falta:{n.TOTAL_DIARIO_MAX_S}" in res.motivos
    tres_dias = clasificar(lunes, con_extras(PROGRAMA_48, lun=1, mar=1, mie=1, jue=1), PROGRAMA_48)
    assert horas(tres_dias) == (48 * H, 3 * H, 0, H)  # el cuarto dia ya no cabe en la norma anterior


# --- Parametros faltantes: provisional + AL12, nunca excepcion ----------------------------------

def test_sin_distribucion_art_66_la_extra_queda_pendiente_de_clasificacion_con_al12():
    res = _con_versiones(sin(n.ART66_DIARIO_S), con_extras(PROGRAMA_46, lun=2))
    assert horas(res) == (46 * H, 0, 0, 2 * H)
    assert res.provisional and AL12 in res.alertas and f"falta:{n.ART66_DIARIO_S}" in res.motivos


def test_sin_tope_semanal_art_66_no_se_inventa_el_corte_doble_triple():
    res = _con_versiones(sin(n.ART66_SEMANAL_S), con_extras(PROGRAMA_46, lun=2))
    assert horas(res) == (46 * H, 0, 0, 2 * H)
    assert res.provisional and f"falta:{n.ART66_SEMANAL_S}" in res.motivos


def test_sin_art_68_el_reparto_doble_triple_sigue_pero_no_se_etiqueta_exceso_legal():
    res = _con_versiones(sin(n.ART68_SEMANAL_S), con_extras(PROGRAMA_46, lun=4, mar=4, mie=4, jue=2))
    assert horas(res) == (46 * H, 9 * H, 5 * H, 0)
    assert res.provisional and f"falta:{n.ART68_SEMANAL_S}" in res.motivos
    assert not any(ETQ_EXCESO_LEGAL in c.etiquetas for c in res.segmentos)


def test_sin_total_diario_no_se_evalua_el_limite_de_12h_y_queda_provisional():
    res = _con_versiones(sin(n.TOTAL_DIARIO_MAX_S), {**exacto(PROGRAMA_46), 0: [(6, 22)]})
    assert res.provisional and f"falta:{n.TOTAL_DIARIO_MAX_S}" in res.motivos
    assert AVISO_TOTAL_DIARIO_SUPERADO not in res.avisos


def test_los_pendientes_de_la_asignacion_pasan_a_pendiente_de_clasificacion_con_su_motivo():
    res = _con_versiones(sin(n.ORDINARIA_SEMANAL_S), exacto(PROGRAMA_46))
    assert horas(res) == (0, 0, 0, 46 * H) and res.provisional
    assert all(c.motivo == f"falta:{n.ORDINARIA_SEMANAL_S}" for c in res.segmentos)


def test_lo_no_confirmado_pasa_intacto():
    seg, vers = segmentar_semana(LUN_2027, {**exacto(PROGRAMA_46), 0: [(8, (16, 10))]}, tolerancia=10)
    res = repartir_tramos(asignar_extra(seg, vers)[0], vers)
    assert sum(s.intervalo.duracion for s in res.no_confirmados) == 10 * M


# --- Q-E: dos categorias de pendiente; `extra_pendiente_clasificacion` solo es fuera de distribucion ---

def test_q_e_la_categoria_neutra_tiene_su_propio_identificador_y_no_es_extra():
    assert CAT_POR_CLASIFICAR == "tiempo_pendiente_de_clasificar" != CAT_PENDIENTE == "extra_pendiente_clasificacion"


def test_q_e_semana_sin_tope_resuelto_queda_en_la_categoria_neutra_y_no_cuenta_como_extra():
    res = _con_versiones(sin(n.ORDINARIA_SEMANAL_S), exacto(PROGRAMA_46))
    assert res.total_s(CAT_POR_CLASIFICAR) == 46 * H and res.total_s(CAT_PENDIENTE) == 0
    assert res.extra_s == 0 and res.provisional and AL12 in res.alertas


def test_q_e_semana_sin_resolver_queda_en_la_categoria_neutra():
    res = _con_versiones(sin(n.SEMANA_INICIO_DIA), exacto(PROGRAMA_46))
    assert res.total_s(CAT_POR_CLASIFICAR) == 46 * H and res.total_s(CAT_PENDIENTE) == 0


def test_q_e_q_f_franja_dudosa_de_la_semana_de_transicion_es_neutra_y_la_extra_segura_sigue_siendo_extra():
    programa = {d: [(8, 16)] for d in range(6)}
    res = clasificar(date(2026, 12, 28), {**exacto(programa), 0: [(8, 17)]}, programa)  # 49 h
    assert res.total_s(CAT_POR_CLASIFICAR) == 2 * H and res.total_s(CAT_PENDIENTE) == 0
    assert res.total_s(CAT_DOBLE) == H and res.total_s(CAT_ORDINARIO) == 46 * H
    assert res.extra_s == H  # la franja dudosa no se declara extra
    assert res.provisional and AL12 in res.alertas
    assert all(c.motivo == f"semana_transicion:{n.ORDINARIA_SEMANAL_S}" for c in res.segmentos if c.categoria == CAT_POR_CLASIFICAR)


def test_q_e_lo_fuera_de_la_distribucion_art_66_sigue_en_extra_pendiente_de_clasificacion():
    res = clasificar(LUN_2027, con_extras(PROGRAMA_46, lun=5))  # 4 h caben; 1 h pasa de 4 h/dia
    assert res.total_s(CAT_PENDIENTE) == H and res.total_s(CAT_POR_CLASIFICAR) == 0
    assert res.extra_s == 5 * H


def test_q_e_sin_distribucion_art_66_no_se_afirma_que_sea_extra_fuera_de_distribucion():
    res = _con_versiones(sin(n.ART66_DIARIO_S), con_extras(PROGRAMA_46, lun=2))
    assert res.total_s(CAT_POR_CLASIFICAR) == 2 * H and res.total_s(CAT_PENDIENTE) == 0
    assert f"falta:{n.ART66_DIARIO_S}" in res.motivos


def test_q_e_el_resumen_por_dia_cuenta_la_categoria_neutra():
    res = _con_versiones(sin(n.ORDINARIA_SEMANAL_S), exacto(PROGRAMA_46))
    assert sum(d.por_clasificar_s for d in res.dias) == 46 * H
    assert all(d.total_s == d.ordinario_s + d.doble_s + d.triple_s + d.pendiente_s + d.por_clasificar_s for d in res.dias)


# --- Tope art. 61 diario: sale del tipo DECLARADO (tipo_efectivo), nunca de lo trabajado ----------

def test_el_tope_art_61_diario_se_lee_del_tipo_declarado_y_no_del_tiempo_trabajado():
    programa = {0: [(8, 18)], 1: [(8, 16)], 2: [(8, 16)], 3: [(8, 16)], 4: [(8, 14)], 5: [(8, 14)]}  # 46 h
    mixta = clasificar(LUN_2027, exacto(programa), programa, regimen="mixta")  # todo diurno, declarado mixta
    lunes = {d.dia_logico: d for d in mixta.dias}[LUN_2027]
    assert lunes.tipo_efectivo == "mixta" and lunes.tope_art61_s == 7 * H + 30 * M
    assert lunes.excede_tope_art61 and lunes.ordinario_s == 10 * H
    diurna = clasificar(LUN_2027, exacto(programa), programa, regimen="diurna")
    lunes_d = {d.dia_logico: d for d in diurna.dias}[LUN_2027]
    assert lunes_d.tope_art61_s == 8 * H and lunes_d.excede_tope_art61
    martes_d = {d.dia_logico: d for d in diurna.dias}[dia_de(LUN_2027, 1)]
    assert martes_d.tope_art61_s == 8 * H and not martes_d.excede_tope_art61  # 8 h exactas
    assert horas(diurna)[1:] == (0, 0, 0)  # el tope diario art. 61 no convierte ordinario en extra (plan 5.2)


def test_parcial_no_tiene_tope_art_61_propio_y_no_marca_exceso():
    res = clasificar(LUN_2027, exacto(PROGRAMA_46), regimen="parcial")
    assert all(d.tope_art61_s is None and not d.excede_tope_art61 for d in res.dias)


def test_sin_tipo_declarado_no_se_infiere_del_tiempo_trabajado():
    seg, vers = segmentar_semana(LUN_2027, exacto(PROGRAMA_46))
    jornadas = tuple(replace(j, regimen_declarado=None) for j in seg.jornadas)
    asig = asignar_extra(replace(seg, jornadas=jornadas), vers)[0]
    res = repartir_tramos(asig, vers)
    assert all(d.tipo_efectivo is None and d.tope_art61_s is None for d in res.dias)


def test_sin_tope_art_61_vigente_queda_provisional():
    res = _con_versiones(sin(n.JORNADA_DIURNA_S), exacto(PROGRAMA_46))
    assert res.provisional and f"falta:{n.JORNADA_DIURNA_S}" in res.motivos


def test_resumen_por_dia_suma_las_categorias():
    res = clasificar(LUN_2027, con_extras(PROGRAMA_46, lun=3, mar=2))
    por_dia = {d.dia_logico: d for d in res.dias}
    assert por_dia[LUN_2027].doble_s == 3 * H and por_dia[LUN_2027].ordinario_s == 8 * H
    assert all(d.total_s == d.ordinario_s + d.doble_s + d.triple_s + d.pendiente_s for d in res.dias)


# --- Propiedades con semillas fijas ------------------------------------------------------------

def _semana_al_azar(rng, lunes):
    semana = Vigencia(lunes, lunes + timedelta(days=7))
    segmentos = []
    for d in range(7):
        dia = lunes + timedelta(days=d)
        cursor = 0
        for _ in range(rng.randint(0, 3)):
            inicio = cursor + rng.randint(0, 4 * H)
            fin = inicio + rng.choice([1, M, 2 * H, rng.randint(1, 12 * H)])
            if fin > 24 * H:
                break
            cursor = fin
            segmentos.append(Segmento(
                Intervalo(t(dia, 0) + inicio, t(dia, 0) + fin), dia, dia, semana,
                rng.choice([CLASE_DENTRO, CLASE_EXCESO, CLASE_EXCESO, CLASE_SIN_CLASIFICAR]), BANDA_DIURNA,
                frozenset(), "checada", rng.choice([CONFIRMADO, CONFIRMADO, ESTADO_PENDIENTE]), "x",
            ))
    return ResultadoSegmentacion(tuple(segmentos))


def _tramos(res, versiones=BASE):
    return repartir_tramos(asignar_extra(res, versiones)[0], versiones) if res.segmentos else None


def test_propiedad_ordinario_doble_triple_y_pendiente_suman_el_confirmado_sin_duplicar_ni_negativos():
    for semilla in range(400):
        rng = random.Random(semilla)
        entrada = _semana_al_azar(rng, LUN_2027)
        res = _tramos(entrada)
        if res is None:
            continue
        confirmado = sum(s.intervalo.duracion for s in entrada.segmentos if s.estado == CONFIRMADO)
        assert res.confirmado_s == confirmado, semilla
        assert sum(horas(res)) == confirmado and min(horas(res)) >= 0, semilla
        ordenados = sorted((c.segmento.intervalo for c in res.segmentos), key=lambda i: i.inicio)
        assert all(a.fin <= b.inicio for a, b in zip(ordenados, ordenados[1:])), semilla
        assert all(i.duracion > 0 for i in ordenados), semilla
        assert res.extra_s == res.total_s(CAT_DOBLE) + res.total_s(CAT_TRIPLE) + res.total_s(CAT_PENDIENTE), semilla


def test_propiedad_la_extra_solo_cae_en_segmentos_de_exceso_salvo_remanente_con_ho03():
    for semilla in range(400):
        rng = random.Random(semilla)
        entrada = _semana_al_azar(rng, LUN_2027)
        if not entrada.segmentos:
            continue
        asig = asignar_extra(entrada, BASE)[0]
        res = repartir_tramos(asig, BASE)
        if HO03 not in asig.alertas:
            for c in res.segmentos:
                if c.categoria != CAT_ORDINARIO:
                    assert c.segmento.clase in (CLASE_EXCESO, CLASE_SIN_CLASIFICAR), semilla
        for c in res.segmentos:
            if c.categoria == CAT_ORDINARIO:
                assert c.autorizacion is None, semilla


def test_propiedad_los_limites_de_distribucion_y_el_corte_doble_triple_se_respetan():
    for semilla in range(400):
        rng = random.Random(semilla)
        res = _tramos(_semana_al_azar(rng, LUN_2027))
        if res is None:
            continue
        art66 = [c for c in res.segmentos if c.categoria in (CAT_DOBLE, CAT_TRIPLE)]
        por_dia: dict = {}
        for c in art66:
            por_dia[c.segmento.dia_logico] = por_dia.get(c.segmento.dia_logico, 0) + c.segmento.intervalo.duracion
        assert all(v <= 4 * H for v in por_dia.values()), semilla  # 4 h diarias de la semilla art. 66
        assert len(por_dia) <= 4, semilla
        assert res.total_s(CAT_DOBLE) <= 9 * H, semilla
        if res.total_s(CAT_TRIPLE):
            assert res.total_s(CAT_DOBLE) == 9 * H, semilla  # no hay triple antes de agotar el doble
            dobles = [c.segmento.intervalo.fin for c in res.segmentos if c.categoria == CAT_DOBLE]
            triples = [c.segmento.intervalo.inicio for c in res.segmentos if c.categoria == CAT_TRIPLE]
            assert max(dobles) <= min(triples), semilla  # el doble va primero en el tiempo
        legales = sum(c.segmento.intervalo.duracion for c in res.segmentos if ETQ_EXCESO_LEGAL in c.etiquetas)
        assert legales >= max(0, res.total_s(CAT_TRIPLE) - 4 * H), semilla  # triple sobre el tope art. 68 = exceso legal


def test_propiedad_entradas_permutadas_dan_el_mismo_resultado():
    for semilla in range(150):
        rng = random.Random(semilla)
        entrada = _semana_al_azar(rng, LUN_2027)
        if not entrada.segmentos:
            continue
        mezcladas = list(entrada.segmentos)
        rng.shuffle(mezcladas)
        a = repartir_tramos(asignar_extra(entrada, BASE)[0], BASE)
        b = repartir_tramos(asignar_extra(replace(entrada, segmentos=tuple(mezcladas)), BASE)[0], BASE)
        assert a == b, semilla


def test_propiedad_de_punta_a_punta_desde_checadas_no_se_pierde_ni_se_duplica_ningun_segundo():
    for semilla in range(150):
        rng = random.Random(semilla)
        programa = {d: [(8, 16)] for d in range(7) if rng.random() < 0.8}
        trabajado, fisico = {}, 0
        for d in range(7):
            cursor, partes = 0, []
            for _ in range(rng.randint(0, 2)):
                ini = cursor + rng.randint(0, 5 * 60)
                fin = ini + rng.randint(1, 13 * 60)
                if fin > 24 * 60:
                    break
                cursor = fin
                partes.append(((ini // 60, ini % 60), (fin // 60, fin % 60)))
                fisico += (fin - ini) * M
            if partes:
                trabajado[d] = partes
        seg, vers = segmentar_semana(LUN_2027, trabajado, programa)
        asignaciones = asignar_extra(seg, vers)
        resultados = [repartir_tramos(a, vers) for a in asignaciones]
        total = sum(r.confirmado_s + sum(s.intervalo.duracion for s in r.no_confirmados) for r in resultados)
        assert total == fisico, semilla  # confirmado + no confirmado = lo checado, sin duplicar
        for r in resultados:
            assert sum(horas(r)) == r.confirmado_s and min(horas(r)) >= 0, semilla
