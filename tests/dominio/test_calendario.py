"""Calendario: semana laboral (RE01, P-46), jornada logica (P-26), art. 74 (RE02),
clasificacion de dia (HO05, P-29) y calendario faltante (AL12)."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from Dominio import normatividad as n
from Dominio.calendario import (
    AL12,
    CalendarioAnual,
    PENDIENTES_MANUALES_ART74,
    asignar_dia_logico,
    asignar_jornada_logica,
    calendario_del_anio,
    calendario_siguiente_pendiente,
    clasificar_dia,
    dia_inicio_semana,
    dividir_por_fecha_real,
    semana_laboral,
    sugerir_descansos_obligatorios,
)
from Dominio.checadas import Checada
from Dominio.emparejamiento import IntervaloEmparejado
from Dominio.tiempo import Intervalo, instante_local

CDMX = ZoneInfo("America/Mexico_City")
H = 3600


def ep(fecha, h, m=0):
    return instante_local(fecha, h * H + m * 60, CDMX)


def emparejado(inicio, fin):
    def ck(i, s):
        return Checada(i, datetime.fromtimestamp(s, tz=CDMX), "R", "AEI")

    return IntervaloEmparejado(Intervalo(inicio, fin), ck("e", inicio), ck("s", fin))


# --- RE01 / P-46: semana laboral ----------------------------------------------------

def test_semana_laboral_lunes_a_domingo():
    sem = semana_laboral(date(2027, 3, 3), 0)  # miercoles
    assert (sem.desde, sem.hasta) == (date(2027, 3, 1), date(2027, 3, 8))


def test_semana_laboral_con_inicio_configurable():
    assert semana_laboral(date(2027, 3, 3), 6).desde == date(2027, 2, 28)  # domingo
    assert semana_laboral(date(2027, 3, 7), 6).desde == date(2027, 3, 7)  # el propio domingo abre


def test_p46_semana_partida_por_cierre_de_mes_o_anio_no_se_reinicia():
    assert semana_laboral(date(2027, 1, 31), 0) == semana_laboral(date(2027, 1, 25), 0)  # corte 31/01
    assert semana_laboral(date(2027, 2, 1), 0).desde == date(2027, 2, 1)
    transicion = semana_laboral(date(2027, 1, 1), 0)
    assert (transicion.desde, transicion.hasta) == (date(2026, 12, 28), date(2027, 1, 4))
    assert semana_laboral(date(2026, 12, 28), 0) == semana_laboral(date(2027, 1, 3), 0) == transicion


@pytest.mark.parametrize("dia", [-1, 7, 1.0, True, "0", None])
def test_semana_laboral_rechaza_dia_de_inicio_invalido(dia):
    with pytest.raises(ValueError):
        semana_laboral(date(2027, 3, 3), dia)


def test_dia_inicio_semana_sale_de_la_politica_versionada_por_empresa():
    from Dominio.modelos import ORIGEN_PATRONAL, VersionParametro, Vigencia

    assert dia_inicio_semana(n.SEMILLA_PATRONAL, date(2027, 3, 3), "AEI") == 0
    vers = (
        *n.SEMILLA_PATRONAL,
        VersionParametro(n.SEMANA_INICIO_DIA, 6, Vigencia(date(2027, 1, 1)), "prueba", ORIGEN_PATRONAL, "CATAB"),
    )
    assert dia_inicio_semana(vers, date(2027, 3, 3), "CATAB") == 6
    assert dia_inicio_semana(vers, date(2027, 3, 3), "AEI") == 0


# --- RE02: art. 74 como sugerencia ----------------------------------------------------

def _fechas(anio):
    return {s.fecha for s in sugerir_descansos_obligatorios(anio)}


def test_art74_2027_fechas_fijas_y_moviles():
    assert _fechas(2027) == {
        date(2027, 1, 1), date(2027, 2, 1), date(2027, 3, 15), date(2027, 5, 1),
        date(2027, 9, 16), date(2027, 11, 15), date(2027, 12, 25),
    }


def test_art74_2026_y_2028_lunes_por_regla():
    assert {date(2026, 2, 2), date(2026, 3, 16), date(2026, 11, 16)} <= _fechas(2026)
    assert {date(2028, 2, 7), date(2028, 3, 20), date(2028, 11, 20)} <= _fechas(2028)


def test_art74_primero_de_octubre_solo_cada_seis_anos_de_transmision():
    assert date(2024, 10, 1) in _fechas(2024)
    assert date(2030, 10, 1) in _fechas(2030)
    for anio in (2025, 2026, 2027, 2028, 2029):
        assert date(anio, 10, 1) not in _fechas(anio)


def test_art74_son_sugerencias_con_fundamento_y_ordenadas():
    sugeridos = sugerir_descansos_obligatorios(2027)
    assert [s.fecha for s in sugeridos] == sorted(s.fecha for s in sugeridos)
    assert all(s.fundamento.startswith("LFT art. 74") for s in sugeridos)
    assert all(not s.confirmado for s in sugeridos)  # RH confirma


def test_art74_jornada_electoral_queda_como_captura_manual():
    assert any("electoral" in p.lower() for p in PENDIENTES_MANUALES_ART74)


def test_art74_el_calendario_precargado_no_es_valido_hasta_confirmar():
    cal = CalendarioAnual(2027, frozenset(_fechas(2027)))
    assert cal.confirmado is False
    with pytest.raises(ValueError):
        CalendarioAnual(2027, frozenset({date(2026, 12, 25)}))  # fuera del anio


# --- AL12: calendario faltante ----------------------------------------------------------

def _cal(anio=2027, confirmado=True, extra=()):
    return CalendarioAnual(anio, frozenset(_fechas(anio)), frozenset(extra), confirmado)


def test_calendario_del_anio_none_si_falta_y_error_si_hay_dos():
    assert calendario_del_anio([], 2027) is None
    assert calendario_del_anio([_cal()], 2027).anio == 2027
    with pytest.raises(ValueError):
        calendario_del_anio([_cal(), _cal()], 2027)


def test_calendario_siguiente_pendiente_desde_el_1_de_diciembre():
    cals = [_cal(2027)]
    assert calendario_siguiente_pendiente(date(2027, 11, 30), cals) is False
    assert calendario_siguiente_pendiente(date(2027, 12, 1), cals) is True  # falta 2028
    assert calendario_siguiente_pendiente(date(2027, 12, 1), [*cals, _cal(2028)]) is False
    assert calendario_siguiente_pendiente(date(2027, 12, 1), [*cals, _cal(2028, confirmado=False)]) is True


def test_sin_calendario_el_dia_es_provisional_con_al12_y_no_se_pierde_el_dato():
    c = clasificar_dia(date(2027, 5, 1), [], programado=True, descanso_semanal=False, trabajado_s=8 * H)
    assert c.provisional is True and AL12 in c.alertas
    assert "trabajado" in c.etiquetas


def test_calendario_sin_confirmar_tambien_es_provisional():
    c = clasificar_dia(
        date(2027, 5, 1), [_cal(confirmado=False)], programado=True, descanso_semanal=False, trabajado_s=0
    )
    assert c.provisional is True and AL12 in c.alertas


# --- HO05: clasificacion de dia ---------------------------------------------------------

def _cl(fecha, **kw):
    base = dict(programado=True, descanso_semanal=False, trabajado_s=0)
    base.update(kw)
    return clasificar_dia(fecha, [_cal(extra=[date(2027, 7, 2)])], **base)


def test_ho05_los_cuatro_estados_se_distinguen():
    assert _cl(date(2027, 3, 3)).base == "programado"
    assert _cl(date(2027, 3, 3), programado=False).base == "no_programado"
    assert _cl(date(2027, 3, 3), programado=False, descanso_semanal=True).base == "descanso_semanal"
    assert "descanso_obligatorio" in _cl(date(2027, 5, 1), programado=False).etiquetas
    assert "dia_empresa" in _cl(date(2027, 7, 2), programado=False).etiquetas


def test_ho05_ausencia_solo_si_estaba_programado_sin_trabajo_ni_justificacion():
    assert _cl(date(2027, 3, 3)).ausencia is True
    assert _cl(date(2027, 3, 3), trabajado_s=H).ausencia is False
    justificada = _cl(date(2027, 3, 3), justificacion="vacaciones")
    assert justificada.ausencia is False and "justificado:vacaciones" in justificada.etiquetas
    assert _cl(date(2027, 3, 3), programado=False).ausencia is False  # dia no programado
    assert _cl(date(2027, 5, 1)).ausencia is False  # descanso obligatorio: no es falta


def test_p29_domingo_trabajado_se_etiqueta_sin_asumir_tiempo_extra():
    c = _cl(date(2027, 3, 7), programado=False, trabajado_s=4 * H)  # domingo
    assert {"domingo", "domingo_trabajado", "trabajado"} <= c.etiquetas
    assert not any("extra" in e for e in c.etiquetas)
    assert not hasattr(c, "extra_s")


def test_p29_descanso_obligatorio_y_semanal_trabajados():
    obligatorio = _cl(date(2027, 5, 1), programado=False, trabajado_s=H)  # sabado
    assert {"descanso_obligatorio", "descanso_obligatorio_trabajado"} <= obligatorio.etiquetas
    semanal = _cl(date(2027, 3, 6), programado=False, descanso_semanal=True, trabajado_s=H)
    assert {"descanso_semanal", "descanso_semanal_trabajado"} <= semanal.etiquetas
    assert "descanso_obligatorio" not in semanal.etiquetas


def test_p29_festivo_en_domingo_conserva_ambas_etiquetas():
    cal = CalendarioAnual(2027, frozenset({date(2027, 3, 7)}), confirmado=True)  # domingo simulado
    c = clasificar_dia(date(2027, 3, 7), [cal], programado=False, descanso_semanal=False, trabajado_s=H)
    assert {"domingo_trabajado", "descanso_obligatorio_trabajado"} <= c.etiquetas


# --- P-26: jornada logica y fecha real ---------------------------------------------------

def test_p26_turno_2200_a_0500_se_asigna_al_dia_de_inicio_y_suma_7_h_sin_duplicar():
    lunes, martes = date(2027, 1, 4), date(2027, 1, 5)
    inicio, fin = ep(lunes, 22), ep(martes, 5)
    (asig,) = asignar_jornada_logica([emparejado(inicio, fin)], CDMX)
    assert asig.dia_logico == lunes
    assert [(p.fecha_real, p.intervalo.duracion) for p in asig.partes] == [(lunes, 2 * H), (martes, 5 * H)]
    assert sum(p.intervalo.duracion for p in asig.partes) == 7 * H == fin - inicio


def test_dividir_por_fecha_real_en_la_medianoche_exacta():
    partes = dividir_por_fecha_real(Intervalo(ep(date(2027, 1, 4), 23), ep(date(2027, 1, 5), 1)), CDMX)
    assert partes[0].intervalo.fin == partes[1].intervalo.inicio == ep(date(2027, 1, 5), 0)
    una = dividir_por_fecha_real(Intervalo(ep(date(2027, 1, 4), 8), ep(date(2027, 1, 4), 9)), CDMX)
    assert [p.fecha_real for p in una] == [date(2027, 1, 4)]
    # un intervalo que termina justo en la medianoche no abre un tramo vacio del dia siguiente
    assert len(dividir_por_fecha_real(Intervalo(ep(date(2027, 1, 4), 22), ep(date(2027, 1, 5), 0)), CDMX)) == 1


def test_jornada_logica_continua_un_turno_nocturno_partido_por_una_comida():
    lunes, martes = date(2027, 1, 4), date(2027, 1, 5)
    fin_programado = ep(martes, 6)  # el horario del lunes termina el martes 06:00

    def previa(fecha):
        return fin_programado if fecha == lunes else None

    segundo = Intervalo(ep(martes, 1), ep(martes, 5))
    assert asignar_dia_logico(segundo, CDMX) == martes  # sin horario: dia de inicio
    assert asignar_dia_logico(segundo, CDMX, previa) == lunes
    despues = Intervalo(ep(martes, 6), ep(martes, 14))  # empieza al terminar el turno nocturno
    assert asignar_dia_logico(despues, CDMX, previa) == martes


def test_jornada_logica_no_depende_del_orden_de_entrada():
    a = emparejado(ep(date(2027, 1, 4), 22), ep(date(2027, 1, 5), 5))
    b = emparejado(ep(date(2027, 1, 6), 7), ep(date(2027, 1, 6), 15))
    assert asignar_jornada_logica([a, b], CDMX) == asignar_jornada_logica([b, a], CDMX)
