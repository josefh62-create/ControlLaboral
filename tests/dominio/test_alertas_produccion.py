"""Normalizacion de las alertas que ya producen T1-T5 y evaluadores puros de AL01, AL08 (P-28) y AL11.

Cada AL01-AL14 tiene aqui al menos una prueba: las producidas por T2-T5 se leen de resultados reales
(codigos + avisos) y se convierten en `Alerta` sin tocar los minutos; las de umbral/descanso se
evaluan con funciones puras. Persistencia y destinatarios son de E3/E4."""
from dataclasses import replace
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from Dominio import normatividad as n
from Dominio import regimenes as r
from Dominio.alertas import (
    ContextoAlerta,
    alertas_de_codigos,
    alertas_de_emparejamiento,
    alertas_de_extra,
    alertas_de_infracciones,
    alertas_de_segmentacion,
    clave_deduplicacion,
    consolidar,
    evaluar_descanso_semanal,
    evaluar_proximidad_limite_ordinario,
    evaluar_umbral_interno,
)
from Dominio.checadas import Checada, marcar_checadas
from Dominio.criterios_extra import asignar_extra
from Dominio.emparejamiento import emparejar
from Dominio.horarios import DiaHorario, Horario, evaluar_compatibilidad
from Dominio.modelos import VersionParametro, Vigencia
from Dominio.tiempo import Intervalo
from Dominio.tramos_extra import repartir_tramos
from _semanas_extra import BASE, H, LUN_2027, M, PROGRAMA_46, segmentar_semana

CDMX = ZoneInfo("America/Mexico_City")
SEMANA = Vigencia(LUN_2027, date(2027, 1, 11))
CTX = ContextoAlerta("T-1", "AEI", SEMANA, "n1")


def clasificar(trabajado, programa=None, versiones=BASE):
    seg, vers = segmentar_semana(LUN_2027, trabajado, programa, versiones=versiones)
    return repartir_tramos(asignar_extra(seg, vers)[0], vers)


def con_extras(**horas_por_dia):
    nombres = {"lun": 0, "mar": 1, "mie": 2, "jue": 3, "vie": 4, "sab": 5}
    trabajado = {d: list(p) for d, p in PROGRAMA_46.items()}
    for nombre, extra in horas_por_dia.items():
        d = nombres[nombre]
        ini, fin = trabajado[d][-1]
        h, m = (extra, 0) if not isinstance(extra, tuple) else extra
        trabajado[d][-1] = (ini, (fin + h, m))
    return trabajado


def por_codigo(alertas):
    return {(a.codigo, a.severidad, a.sujeto) for a in alertas}


# --- AL02-AL07 desde el resultado de T5 (avisos con alcanzado/superado diferenciados) ---------------

def test_al02_y_al04_con_9_h_extra_exactas_son_informativa_y_advertencia_de_tope_alcanzado():
    res = clasificar(con_extras(lun=3, mar=3, mie=3))
    alertas = alertas_de_extra(res, CTX)
    assert por_codigo(alertas) == {("AL02", "informativo", ""), ("AL04", "advertencia", "art66_alcanzado")}


def test_alcanzado_y_superado_del_tope_art_66_son_alertas_distintas_pero_del_mismo_codigo():
    alcanzado = alertas_de_extra(clasificar(con_extras(lun=3, mar=3, mie=3)), CTX)
    superado = alertas_de_extra(clasificar(con_extras(lun=3, mar=3, mie=(3, 1))), CTX)
    (a,) = [x for x in alcanzado if x.codigo == "AL04"]
    (s,) = [x for x in superado if x.codigo == "AL04"]
    assert a.sujeto == "art66_alcanzado" and s.sujeto == "art66_superado"
    assert clave_deduplicacion(a) != clave_deduplicacion(s)


def test_al03_preventiva_con_anticipacion_de_60_min():
    alertas = alertas_de_extra(clasificar(con_extras(lun=4, mar=4)), CTX)
    assert ("AL03", "preventivo", "art66_preventivo") in por_codigo(alertas)


def test_al06_art_68_alcanzado_es_preventiva_y_superado_es_critica():
    alcanzado = alertas_de_extra(clasificar(con_extras(lun=4, mar=4, mie=4, jue=1)), CTX)
    superado = alertas_de_extra(clasificar(con_extras(lun=4, mar=4, mie=4, jue=(1, 1))), CTX)
    assert ("AL06", "preventivo", "art68_alcanzado") in por_codigo(alcanzado)
    assert ("AL06", "critico", "art68_superado") in por_codigo(superado)


def test_al05_y_al07_distribucion_y_total_diario_son_alertas_independientes():
    trabajado = {**{d: list(p) for d, p in PROGRAMA_46.items()}, 0: [(6, 22)]}  # 16 h el lunes
    alertas = por_codigo(alertas_de_extra(clasificar(trabajado), CTX))
    assert ("AL05", "critico", "distribucion_art66_diaria") in alertas
    assert ("AL07", "critico", "total_diario_superado") in alertas


def test_al07_12_h_exactas_es_preventiva():
    alertas = por_codigo(alertas_de_extra(clasificar(con_extras(lun=4)), CTX))
    assert ("AL07", "preventivo", "total_diario_alcanzado") in alertas


def test_normalizar_no_cambia_los_minutos_ni_el_resultado():
    res = clasificar(con_extras(lun=3, mar=3, mie=(3, 1)))
    copia = replace(res)
    alertas_de_extra(res, CTX)
    assert res == copia and res.confirmado_s == 46 * H + 9 * H + M


def test_sin_extra_no_hay_alertas():
    assert alertas_de_extra(clasificar({d: list(p) for d, p in PROGRAMA_46.items()}), CTX) == ()


def test_el_aviso_informativo_art_61_no_genera_alerta():
    res = clasificar(con_extras(lun=(1, 0), mar=(1, 0)))
    assert alertas_de_extra(replace(res, avisos_informativos=frozenset({"tope_art61_diario_compensado_en_semana"})),
                            CTX) == alertas_de_extra(res, CTX)


def test_dos_calculos_de_la_misma_semana_consolidan_a_las_mismas_alertas():
    una = alertas_de_extra(clasificar(con_extras(lun=3, mar=3, mie=(3, 1))), CTX)
    otra = alertas_de_extra(clasificar(con_extras(lun=3, mar=3, mie=(3, 1))), CTX)
    assert consolidar(una + otra) == consolidar(una)


# --- AL12 (T3-T5), AL14 (T4), HO03 y AL09 (T3) ----------------------------------------------------------

def test_al12_un_aviso_por_cada_motivo_de_dato_faltante():
    sin_franja = tuple(v for v in BASE if v.clave != n.NOCTURNO_INICIO_S)
    seg, vers = segmentar_semana(LUN_2027, {0: [(8, 16)]}, versiones=sin_franja)
    alertas = alertas_de_segmentacion(seg, CTX)
    assert ("AL12", "calculo_pendiente", f"falta:{n.NOCTURNO_INICIO_S}") in por_codigo(alertas)
    assert all(a.bloquea_cierre for a in alertas if a.codigo == "AL12")


def test_al12_tambien_sale_del_resultado_de_extra():
    sin_tope = tuple(v for v in BASE if v.clave != n.ART66_SEMANAL_S)
    alertas = alertas_de_extra(clasificar(con_extras(lun=3), versiones=sin_tope), CTX)
    assert any(a.codigo == "AL12" for a in alertas)


def test_al14_se_atribuye_al_dia_logico_de_su_jornada():
    seg, _ = segmentar_semana(LUN_2027, {0: [(14, 22)]}, {0: [(14, 22)]}, regimen="diurna")
    (al14,) = [a for a in alertas_de_segmentacion(seg, CTX) if a.codigo == "AL14"]
    assert al14.severidad == "configuracion" and al14.dia_logico == LUN_2027 and not al14.bloquea_cierre


def _horario_48h():
    dias = {d: DiaHorario((Intervalo(7 * H, 15 * H),)) for d in range(6)}
    return Horario("H1", Vigencia(date(2026, 1, 1)), "diurna", "America/Mexico_City", dias, empresa="AEI")


def test_ho03_y_al09_vienen_de_la_compatibilidad_del_horario():
    ho03 = evaluar_compatibilidad(_horario_48h(), BASE, date(2027, 3, 1))
    al09 = evaluar_compatibilidad(_horario_48h(), BASE, date(2027, 3, 1), fecha_referencia=date(2026, 11, 26))
    assert por_codigo(alertas_de_codigos(ho03.alertas, CTX)) == {("HO03", "revision", "")}
    assert por_codigo(alertas_de_codigos(al09.alertas, CTX)) == {("AL09", "preventivo", "")}


def test_codigo_fuera_del_catalogo_en_alertas_de_codigos_se_rechaza():
    with pytest.raises(ValueError):
        alertas_de_codigos(("AL99",), CTX)


# --- AL13 (T1) ----------------------------------------------------------------------------------------

def test_al13_cada_prohibicion_de_menores_es_una_alerta_critica_con_su_codigo_de_infraccion():
    infs = r.evaluar_prohibiciones(
        r.obtener_regimen("menor_16_18"), n.SEMILLA_LEGAL, date(2027, 3, 3), tiempo_extra_s=60, es_domingo=True
    )
    alertas = alertas_de_infracciones(infs, CTX, date(2027, 3, 7))
    assert {a.sujeto for a in alertas} == {r.EXTRA_PROHIBIDA, r.DOMINGO_PROHIBIDO}
    assert all(a.codigo == "AL13" and a.severidad == "critico" and a.dia_logico == date(2027, 3, 7) for a in alertas)


# --- AL10 (T2) ----------------------------------------------------------------------------------------

def _ck(id_, h, m=0, dia=4, **kw):
    return Checada(id_, datetime(2027, 1, dia, h, m, tzinfo=CDMX), kw.pop("reloj", "R-AEI"), "AEI", **kw)


def test_al10_checada_impar_genera_una_alerta_de_revision_por_dia():
    marcadas = marcar_checadas([_ck("e", 8)], n.SEMILLA_PATRONAL)
    alertas = alertas_de_emparejamiento(emparejar(marcadas, n.SEMILLA_PATRONAL), CTX)
    (a,) = alertas
    assert a.codigo == "AL10" and a.severidad == "revision" and a.dia_logico == date(2027, 1, 4)


def test_al10_marcas_duplicada_y_cercana_sin_resolver_tambien_alertan():
    lote = [_ck("a", 8), _ck("b", 8, 10), _ck("c", 17)]
    marcadas = marcar_checadas(lote, n.SEMILLA_PATRONAL)
    alertas = alertas_de_emparejamiento(emparejar(marcadas, n.SEMILLA_PATRONAL), CTX, marcadas)
    assert any(a.sujeto.startswith("posible_duplicado:") for a in alertas)


def test_p48_al10_reimportado_con_otros_ids_conserva_la_clave():
    uno = marcar_checadas([_ck("a1", 8)], n.SEMILLA_PATRONAL)
    dos = marcar_checadas([_ck("zz-otro-id", 8)], n.SEMILLA_PATRONAL)
    a = alertas_de_emparejamiento(emparejar(uno, n.SEMILLA_PATRONAL), CTX, uno)
    b = alertas_de_emparejamiento(emparejar(dos, n.SEMILLA_PATRONAL), CTX, dos)
    assert [clave_deduplicacion(x) for x in a] == [clave_deduplicacion(x) for x in b]


def test_al10_sin_incidencias_ni_marcas_no_alerta():
    marcadas = marcar_checadas([_ck("e", 8), _ck("s", 17)], n.SEMILLA_PATRONAL)
    assert alertas_de_emparejamiento(emparejar(marcadas, n.SEMILLA_PATRONAL), CTX, marcadas) == ()


# --- AL01: proximidad al limite ordinario (parte pura) ----------------------------------------------------

def test_al01_con_anticipacion_de_60_min_avisa_desde_7_h_hasta_el_tope_de_8_h():
    def evaluar(acumulado):
        return evaluar_proximidad_limite_ordinario(acumulado, 8 * H, 60 * M, CTX, ambito="diario",
                                                   dia_logico=LUN_2027)

    assert evaluar(7 * H - 1) is None
    assert evaluar(7 * H).codigo == "AL01" and evaluar(7 * H).severidad == "preventivo"
    assert evaluar(8 * H).sujeto == "diario"
    assert evaluar(8 * H + 1) is None  # ya es extra: lo avisa AL02, no AL01


def test_al01_sin_anticipacion_o_sin_tope_configurados_no_alerta():
    assert evaluar_proximidad_limite_ordinario(8 * H, 8 * H, None, CTX, ambito="semanal") is None
    assert evaluar_proximidad_limite_ordinario(8 * H, None, 60 * M, CTX, ambito="semanal") is None


def test_al01_rechaza_ambito_desconocido_y_acumulados_negativos():
    with pytest.raises(ValueError):
        evaluar_proximidad_limite_ordinario(1, 8 * H, 60 * M, CTX, ambito="mensual")
    with pytest.raises(ValueError):
        evaluar_proximidad_limite_ordinario(-1, 8 * H, 60 * M, CTX, ambito="diario")


# --- AL08 / P-28: descanso semanal no acreditado -------------------------------------------------------------

def _dias(n_dias, desde=LUN_2027):
    return [date.fromordinal(desde.toordinal() + i) for i in range(n_dias)]


def test_p28_siete_dias_seguidos_trabajados_sin_descanso_acreditado_alertan_el_septimo_dia():
    (a,) = evaluar_descanso_semanal(_dias(7), BASE, CTX)
    assert a.codigo == "AL08" and a.severidad == "critico"
    assert a.dia_logico == _dias(7)[-1] and a.sujeto == "7_dias_seguidos"


def test_p28_seis_dias_o_siete_con_un_descanso_en_medio_no_alertan():
    assert evaluar_descanso_semanal(_dias(6), BASE, CTX) == ()
    con_descanso = _dias(7)
    con_descanso.pop(3)
    assert evaluar_descanso_semanal(con_descanso, BASE, CTX) == ()


def test_p28_un_dia_solo_con_tiempo_pendiente_no_acredita_descanso():
    dias = _dias(7)
    trabajados, pendiente = [d for d in dias if d != dias[3]], [dias[3]]
    (a,) = evaluar_descanso_semanal(trabajados, BASE, CTX, dias_pendientes=pendiente)
    assert a.codigo == "AL08"


def test_p28_una_racha_larga_genera_una_sola_alerta_estable_al_recalcular_con_mas_dias():
    corta = evaluar_descanso_semanal(_dias(7), BASE, CTX)
    larga = evaluar_descanso_semanal(_dias(10), BASE, CTX)
    assert [clave_deduplicacion(a) for a in corta] == [clave_deduplicacion(a) for a in larga]


def test_p28_la_racha_cruza_semanas_y_el_orden_de_los_dias_no_importa():
    dias = _dias(7, date(2027, 1, 1))  # viernes a jueves: cruza la semana laboral
    revueltos = list(reversed(dias))
    assert evaluar_descanso_semanal(revueltos, BASE, CTX) == evaluar_descanso_semanal(dias, BASE, CTX)
    assert len(evaluar_descanso_semanal(dias, BASE, CTX)) == 1


def test_p28_el_limite_sale_de_la_norma_versionada_y_sin_ella_es_al12():
    siete = VersionParametro(n.DESCANSO_DIAS_TRABAJO_MAX, 7, Vigencia(date(2026, 1, 1)), "prueba")
    versiones = tuple(v for v in BASE if v.clave != n.DESCANSO_DIAS_TRABAJO_MAX) + (siete,)
    assert evaluar_descanso_semanal(_dias(7), versiones, CTX) == ()
    assert len(evaluar_descanso_semanal(_dias(8), versiones, CTX)) == 1
    sin_norma = tuple(v for v in BASE if v.clave != n.DESCANSO_DIAS_TRABAJO_MAX)
    (a,) = evaluar_descanso_semanal(_dias(7), sin_norma, CTX)
    assert a.codigo == "AL12" and a.sujeto == f"falta:{n.DESCANSO_DIAS_TRABAJO_MAX}"


def test_sin_dias_no_hay_alertas_de_descanso():
    assert evaluar_descanso_semanal([], BASE, CTX) == ()


# --- AL11: umbral interno patronal (parte pura; el umbral lo configura la empresa) -------------------------------

def test_al11_solo_al_rebasar_el_umbral_interno():
    assert evaluar_umbral_interno(9 * H, 9 * H, CTX, sujeto="extra_semanal") is None
    a = evaluar_umbral_interno(9 * H + 1, 9 * H, CTX, sujeto="extra_semanal")
    assert a.codigo == "AL11" and a.severidad == "advertencia" and a.sujeto == "extra_semanal"


def test_al11_sin_umbral_configurado_no_alerta_y_valores_negativos_se_rechazan():
    assert evaluar_umbral_interno(99 * H, None, CTX, sujeto="extra_semanal") is None
    with pytest.raises(ValueError):
        evaluar_umbral_interno(-1, 9 * H, CTX, sujeto="extra_semanal")
