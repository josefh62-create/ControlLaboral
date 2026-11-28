"""Derecho a alimentos por tiempo extra (BATAB, Q11; plan 4.4/17.1): desayuno, almuerzo y cena por dia,
SOLO si ese dia genero extra, con reglas de configuracion patronal por empresa y vigencia. Sin regla no se
marca nada; sin importes. Los valores de estas pruebas son de prueba: el propietario aun no dio reglas
reales y no se siembra ninguna (Q-L: semantica de las reglas por confirmar)."""
from dataclasses import replace
from datetime import date
from zoneinfo import ZoneInfo

from Dominio import alimentos as al
from Dominio.alimentos import DerechoAlimento, derivar_alimentos
from Dominio.criterios_extra import asignar_extra
from Dominio.modelos import ORIGEN_PATRONAL, VersionParametro, Vigencia
from Dominio.tramos_extra import repartir_tramos
from _semanas_extra import BASE, H, LUN_2027, M, PROGRAMA_46, dia_de, segmentar_semana

CDMX = ZoneInfo("America/Mexico_City")
DESDE = Vigencia(date(2026, 1, 1))


def clasificar(trabajado, versiones=BASE):
    seg, vers = segmentar_semana(LUN_2027, trabajado, versiones=versiones)
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


def regla(clave, valor, empresa=None, vigencia=DESDE):
    return VersionParametro(clave, valor, vigencia, "prueba", ORIGEN_PATRONAL, empresa)


def _en_empresa(res, empresa):
    return replace(res, segmentos=tuple(
        replace(c, segmento=replace(c.segmento, empresa=empresa)) for c in res.segmentos
    ))


def derechos(res, reglas, empresa="AEI"):
    return derivar_alimentos(res, tuple(reglas), CDMX, empresa=empresa)


def pares(resultado):
    return [(d.dia_logico, d.comida) for d in resultado.derechos]


LUN = LUN_2027
CENA_MIN_2H = regla(al.clave_extra_min("cena"), 2 * H)


# --- Sin regla o sin extra no se marca nada ----------------------------------------------------------

def test_sin_regla_configurada_no_se_marca_nada_aunque_haya_extra():
    res = clasificar(con_extras(lun=4))
    r = derechos(res, ())
    assert r.derechos == () and r.motivos == ()


def test_dia_sin_extra_no_genera_alimentos_ni_con_regla_de_cero_minutos():
    res = clasificar({d: list(p) for d, p in PROGRAMA_46.items()})
    assert derechos(res, [regla(al.clave_extra_min("cena"), 0)]).derechos == ()


def test_el_tiempo_pendiente_de_clasificar_no_cuenta_como_extra():
    # Sin tope art. 66 resuelto no se sabe si el tiempo es extra: categoria neutra, sin derecho a alimentos.
    sin_tope = tuple(v for v in BASE if v.clave != "art66_semanal_s")
    res = clasificar(con_extras(lun=4), versiones=sin_tope)
    assert res.por_clasificar_s > 0 and derechos(res, [regla(al.clave_extra_min("cena"), 0)]).derechos == ()


# --- Reglas: minutos minimos, hora de inicio, hora de fin -------------------------------------------------

def test_minutos_minimos_de_extra_del_dia_con_limite_exacto():
    reglas = [CENA_MIN_2H]
    assert pares(derechos(clasificar(con_extras(lun=2)), reglas)) == [(LUN, "cena")]
    assert derechos(clasificar(con_extras(lun=(1, 59))), reglas).derechos == ()


def test_el_derecho_registra_los_minutos_de_extra_del_dia_y_nada_monetario():
    (d,) = derechos(clasificar(con_extras(lun=3)), [CENA_MIN_2H]).derechos
    assert d == DerechoAlimento(LUN, "AEI", "cena", 3 * H)
    assert set(d.__dataclass_fields__) == {"dia_logico", "empresa", "comida", "extra_s"}


def test_hora_de_inicio_de_la_extra_se_compara_con_la_hora_local_del_dia_logico():
    # La extra del lunes empieza a las 16:00 (fin del horario).
    res = clasificar(con_extras(lun=3))
    assert pares(derechos(res, [regla(al.clave_inicio_desde("cena"), 16 * H)])) == [(LUN, "cena")]
    assert derechos(res, [regla(al.clave_inicio_desde("cena"), 16 * H + 1)]).derechos == ()


def test_hora_de_fin_de_la_extra_incluye_turnos_que_cruzan_la_medianoche():
    trabajado = {**{d: list(p) for d, p in PROGRAMA_46.items()}, 0: [(8, 26)]}  # lunes hasta las 02:00 del martes
    res = clasificar(trabajado)
    assert pares(derechos(res, [regla(al.clave_fin_desde("desayuno"), 26 * H)])) == [(LUN, "desayuno")]
    assert derechos(res, [regla(al.clave_fin_desde("desayuno"), 26 * H + 1)]).derechos == ()


def test_todas_las_condiciones_configuradas_de_una_comida_deben_cumplirse():
    res = clasificar(con_extras(lun=3))
    cumple = [regla(al.clave_extra_min("cena"), 2 * H), regla(al.clave_fin_desde("cena"), 19 * H)]
    falla_fin = [regla(al.clave_extra_min("cena"), 2 * H), regla(al.clave_fin_desde("cena"), 19 * H + 1)]
    falla_min = [regla(al.clave_extra_min("cena"), 3 * H + 1), regla(al.clave_fin_desde("cena"), 19 * H)]
    assert pares(derechos(res, cumple)) == [(LUN, "cena")]
    assert derechos(res, falla_fin).derechos == () and derechos(res, falla_min).derechos == ()


def test_cada_comida_tiene_su_propia_regla_y_salen_en_orden_desayuno_almuerzo_cena():
    res = clasificar(con_extras(lun=3, mar=1))
    reglas = [
        regla(al.clave_extra_min("cena"), 3 * H),
        regla(al.clave_extra_min("desayuno"), 1 * H),
        regla(al.clave_extra_min("almuerzo"), 2 * H),
    ]
    assert pares(derechos(res, reglas)) == [
        (LUN, "desayuno"), (LUN, "almuerzo"), (LUN, "cena"), (dia_de(LUN, 1), "desayuno"),
    ]


# --- Por empresa y con vigencia (resolver_vigente) -----------------------------------------------------------

def test_regla_de_otra_empresa_no_aplica_y_la_de_la_empresa_gana_a_la_general():
    res = clasificar(con_extras(lun=3))
    solo_catab = [regla(al.clave_extra_min("cena"), 0, empresa="CATAB")]
    assert derechos(res, solo_catab, empresa="AEI").derechos == ()
    general_y_propia = [regla(al.clave_extra_min("cena"), 0), regla(al.clave_extra_min("cena"), 4 * H, empresa="AEI")]
    assert derechos(res, general_y_propia, empresa="AEI").derechos == ()  # la propia exige 4 h
    en_catab = _en_empresa(res, "CATAB")
    assert pares(derechos(en_catab, general_y_propia)) == [(LUN, "cena")]  # CATAB no tiene regla propia: usa la general


def test_la_regla_se_resuelve_por_el_dia_logico_de_la_extra():
    res = clasificar(con_extras(lun=3, mar=3))
    desde_martes = regla(al.clave_extra_min("cena"), 0, vigencia=Vigencia(dia_de(LUN, 1)))
    assert pares(derechos(res, [desde_martes])) == [(dia_de(LUN, 1), "cena")]
    vencida = regla(al.clave_extra_min("cena"), 0, vigencia=Vigencia(date(2026, 1, 1), dia_de(LUN, 1)))
    assert pares(derechos(res, [vencida])) == [(LUN, "cena")]


def test_el_derecho_pertenece_a_la_empresa_donde_se_trabajo_la_extra():
    res = clasificar(con_extras(lun=3))
    cambiada = _en_empresa(res, "CATAB")
    solo_catab = [regla(al.clave_extra_min("cena"), 0, empresa="CATAB")]
    (d,) = derechos(cambiada, solo_catab, empresa="AEI").derechos
    assert d.empresa == "CATAB"


# --- Configuracion invalida: sin marcar y con motivo ----------------------------------------------------------------

def test_regla_ambigua_no_marca_esa_comida_y_deja_motivo_sin_lanzar():
    res = clasificar(con_extras(lun=3))
    ambigua = [regla(al.clave_extra_min("cena"), 0), regla(al.clave_extra_min("cena"), H)]
    r = derechos(res, ambigua + [regla(al.clave_extra_min("desayuno"), 0)])
    assert pares(r) == [(LUN, "desayuno")]
    assert r.motivos == (f"parametro_ambiguo:{al.clave_extra_min('cena')}",)


def test_derivar_no_modifica_el_resultado_de_extra():
    res = clasificar(con_extras(lun=3))
    copia = replace(res)
    derechos(res, [CENA_MIN_2H])
    assert res == copia and res.confirmado_s == 46 * H + 3 * H


def test_sin_empresa_de_origen_en_el_segmento_se_usa_la_empresa_de_respaldo():
    res = _en_empresa(clasificar(con_extras(lun=3)), None)
    reglas = [regla(al.clave_extra_min("cena"), 0, empresa="CATAB")]
    assert derechos(res, reglas, empresa="AEI").derechos == ()
    (d,) = derechos(res, reglas, empresa="CATAB").derechos
    assert d.empresa == "CATAB"


def test_una_condicion_ambigua_impide_marcar_aunque_otra_condicion_se_cumpla():
    res = clasificar(con_extras(lun=3))
    reglas = [
        regla(al.clave_extra_min("cena"), 0), regla(al.clave_extra_min("cena"), H),  # ambigua
        regla(al.clave_fin_desde("cena"), 19 * H),  # esta si se cumple
    ]
    r = derechos(res, reglas)
    assert r.derechos == () and r.motivos == (f"parametro_ambiguo:{al.clave_extra_min('cena')}",)


def test_el_orden_de_los_derechos_no_depende_del_orden_de_los_segmentos():
    res = clasificar(con_extras(lun=3, mar=3, mie=3))
    invertido = replace(res, segmentos=tuple(reversed(res.segmentos)))
    reglas = [CENA_MIN_2H]
    assert derechos(invertido, reglas) == derechos(res, reglas)
    assert [d.dia_logico for d in derechos(res, reglas).derechos] == [dia_de(LUN, i) for i in range(3)]
