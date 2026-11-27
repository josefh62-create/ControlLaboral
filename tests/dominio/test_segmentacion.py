"""Segmentacion y clasificacion base (doc. 03 8.2 pasos 4 y 8): fronteras de horario, descanso,
medianoche, semana laboral, franja nocturna y vigencia; dentro de horario vs exceso diario;
diurna/nocturna/mixta; etiquetas domingo/festivo/descanso trabajado.
P-26 (22:00-05:00 sin duplicar por fecha), P-27 (mixta 3 h 29 / nocturna 3 h 30),
P-29 (etiquetas sin asumir extras), mas propiedades con semillas fijas."""
import random
from datetime import date, datetime
from zoneinfo import ZoneInfo

from Dominio import normatividad as n
from Dominio.calendario import AL12, CalendarioAnual
from Dominio.checadas import Checada
from Dominio.emparejamiento import NORMAL, IntervaloEmparejado
from Dominio.horarios import (
    CHECADA,
    CONFIRMADO,
    DENTRO_HORARIO,
    DIA_NO_PROGRAMADO,
    FUERA_HORARIO,
    PENDIENTE,
    SIN_HORARIO,
    DescansoHorario,
    DiaHorario,
    Horario,
    PiezaEfectiva,
    ResultadoEfectivo,
    construir_intervalos_efectivos,
)
from Dominio.modelos import VersionParametro, Vigencia
from Dominio.normatividad import SEMILLA_LEGAL, SEMILLA_PATRONAL
from Dominio.segmentacion import (
    BANDA_DIURNA,
    BANDA_NOCTURNA,
    CLASE_DENTRO,
    CLASE_EXCESO,
    CLASE_SIN_CLASIFICAR,
    segmentar,
)
from Dominio.tiempo import Intervalo, instante_local
from Dominio.tolerancias import CLAVES_TOLERANCIA, version_de_tolerancia

CDMX = ZoneInfo("America/Mexico_City")
H, M = 3600, 60
DOMINGO_ANT, LUNES, MARTES, DOMINGO = date(2027, 1, 3), date(2027, 1, 4), date(2027, 1, 5), date(2027, 1, 10)
D2027 = Vigencia(date(2027, 1, 1), date(2028, 1, 1))
BASE = tuple(SEMILLA_LEGAL) + tuple(SEMILLA_PATRONAL)
CAL = CalendarioAnual(2027, frozenset({date(2027, 1, 1)}), confirmado=True)


def t(fecha, h, m=0, s=0):
    return instante_local(fecha, h * H + m * M + s, CDMX)


def par(inicio, fin):
    def ck(id_, s):
        return Checada(id_, datetime.fromtimestamp(s, tz=CDMX), "R-AEI", "AEI")

    return IntervaloEmparejado(Intervalo(inicio, fin), ck(f"e{inicio}", inicio), ck(f"s{fin}", fin), NORMAL)


def hs(h, m=0):
    return h * H + m * M


def horario(dias, regimen="diurna", **kw):
    return Horario("H1", D2027, regimen, "America/Mexico_City", dias, empresa="AEI", **kw)


def tol(minutos):
    return [version_de_tolerancia(k, minutos, Vigencia(date(2027, 1, 1)), "prueba", "AEI") for k in CLAVES_TOLERANCIA]


def correr(pares, horarios, versiones=None, calendarios=(CAL,), **kw):
    versiones = BASE + tuple(tol(10)) if versiones is None else versiones
    efectivo = construir_intervalos_efectivos(pares, horarios, CDMX, versiones=versiones)
    return segmentar(efectivo, CDMX, horarios, calendarios, versiones, empresa="AEI", **kw)


def total(res, **filtros):
    return sum(
        s.intervalo.duracion for s in res.segmentos if all(getattr(s, k) == v for k, v in filtros.items())
    )


# --- P-26: turno 22:00-05:00 ---------------------------------------------------------------------

def horario_nocturno():
    return horario({0: DiaHorario((Intervalo(hs(22), hs(29)),))}, regimen="nocturna")


def test_p26_turno_2200_0500_son_7h_nocturnas_sin_duplicar_por_fecha():
    res = correr([par(t(LUNES, 22), t(MARTES, 5))], [horario_nocturno()])
    assert total(res) == 7 * H
    assert total(res, banda=BANDA_NOCTURNA, clase=CLASE_DENTRO) == 7 * H
    assert [(s.fecha_real, s.dia_logico) for s in res.segmentos] == [(LUNES, LUNES), (MARTES, LUNES)]
    assert [s.intervalo.duracion for s in res.segmentos] == [2 * H, 5 * H]
    assert len(res.jornadas) == 1  # una sola jornada logica, no una por fecha
    assert res.jornadas[0].nocturnos_s == 7 * H
    assert res.jornadas[0].clasificacion == "nocturna"
    assert res.provisional is False


def test_p26_la_franja_corta_a_la_hora_de_inicio_y_fin_versionada():
    # 18:00-23:00: diurno hasta las 20:00 y nocturno despues (franja 20:00-06:00, art. 60)
    h = horario({0: DiaHorario((Intervalo(hs(18), hs(23)),))})
    res = correr([par(t(LUNES, 18), t(LUNES, 23))], [h])
    assert total(res, banda=BANDA_DIURNA) == 2 * H
    assert total(res, banda=BANDA_NOCTURNA) == 3 * H
    # madrugada: 04:00-08:00 es nocturno hasta las 06:00
    h2 = horario({0: DiaHorario((Intervalo(hs(4), hs(8)),))})
    res2 = correr([par(t(LUNES, 4), t(LUNES, 8))], [h2])
    assert total(res2, banda=BANDA_NOCTURNA) == 2 * H
    assert total(res2, banda=BANDA_DIURNA) == 2 * H


def test_p26_un_cambio_de_vigencia_de_la_franja_corta_en_la_medianoche_de_la_fecha_trabajada():
    versiones = tuple(v for v in BASE if v.clave != n.NOCTURNO_INICIO_S) + (
        VersionParametro(n.NOCTURNO_INICIO_S, hs(20), Vigencia(date(2026, 1, 1), MARTES), "prueba"),
        VersionParametro(n.NOCTURNO_INICIO_S, hs(21), Vigencia(MARTES), "prueba"),
    ) + tuple(tol(10))
    dia = DiaHorario((Intervalo(hs(19), hs(23)),))
    h = horario({0: dia, 1: dia})
    res = correr([par(t(LUNES, 19), t(LUNES, 23)), par(t(MARTES, 19), t(MARTES, 23))], [h], versiones)
    lunes = [s for s in res.segmentos if s.fecha_real == LUNES]
    martes = [s for s in res.segmentos if s.fecha_real == MARTES]
    assert sum(s.intervalo.duracion for s in lunes if s.banda == BANDA_NOCTURNA) == 3 * H  # 20:00
    assert sum(s.intervalo.duracion for s in martes if s.banda == BANDA_NOCTURNA) == 2 * H  # 21:00


# --- P-27: mixta / nocturna por umbral de 3 h 30 ------------------------------------------------

def test_p27_mixta_con_3h29_nocturnas_es_mixta():
    h = horario({0: DiaHorario((Intervalo(hs(17), hs(23, 29)),))}, regimen="mixta")
    res = correr([par(t(LUNES, 17), t(LUNES, 23, 29))], [h])
    jornada = res.jornadas[0]
    assert (jornada.nocturnos_s, jornada.diurnos_s) == (3 * H + 29 * M, 3 * H)
    assert jornada.clasificacion == "mixta"


def test_p27_con_3h30_nocturnas_la_jornada_mixta_se_reputa_nocturna():
    h = horario({0: DiaHorario((Intervalo(hs(17), hs(23, 30)),))}, regimen="mixta")
    res = correr([par(t(LUNES, 17), t(LUNES, 23, 30))], [h])
    assert res.jornadas[0].nocturnos_s == 3 * H + 30 * M
    assert res.jornadas[0].clasificacion == "nocturna"


def test_jornada_totalmente_diurna_se_clasifica_diurna():
    h = horario({0: DiaHorario((Intervalo(hs(8), hs(16)),))})
    res = correr([par(t(LUNES, 8), t(LUNES, 16))], [h])
    assert res.jornadas[0].clasificacion == "diurna"
    assert res.jornadas[0].regimen_declarado == "diurna"


# --- Dentro de horario / exceso diario ---------------------------------------------------------

def horario_partido():
    return horario({0: DiaHorario((Intervalo(hs(7), hs(12)), Intervalo(hs(13), hs(16))))})


def test_lo_fuera_del_horario_del_dia_es_exceso_diario_y_lo_dudoso_sigue_pendiente():
    pares = [par(t(LUNES, 6, 50), t(LUNES, 12)), par(t(LUNES, 13), t(LUNES, 16, 25))]
    res = correr(pares, [horario_partido()])
    assert total(res, clase=CLASE_DENTRO, estado=CONFIRMADO) == 8 * H
    assert total(res, clase=CLASE_EXCESO, estado=CONFIRMADO) == 15 * M
    assert total(res, clase=CLASE_EXCESO, estado=PENDIENTE) == 20 * M
    assert total(res) == 8 * H + 35 * M


def test_dia_no_programado_es_todo_exceso_diario():
    res = correr([par(t(MARTES, 8), t(MARTES, 10))], [horario_partido()])
    assert total(res, clase=CLASE_EXCESO) == 2 * H


def test_sin_tolerancias_configuradas_lo_fuera_de_horario_sigue_pendiente_to06():
    res = correr([par(t(LUNES, 13), t(LUNES, 16, 20))], [horario_partido()], versiones=BASE)
    assert total(res, clase=CLASE_EXCESO, estado=PENDIENTE) == 20 * M
    assert total(res, estado=CONFIRMADO, clase=CLASE_EXCESO) == 0


def test_los_descansos_no_computables_se_conservan_como_segmento_aparte():
    h = horario({0: DiaHorario((Intervalo(hs(7), hs(16)),), (DescansoHorario(Intervalo(hs(12), hs(13)), False),))})
    res = correr([par(t(LUNES, 7), t(LUNES, 16))], [h])
    assert total(res, estado="descanso_no_computable") == H
    assert total(res, estado=CONFIRMADO) == 8 * H
    # el descanso no computable no entra al calculo de la jornada diurna/nocturna
    assert res.jornadas[0].diurnos_s == 8 * H


def test_sin_horario_queda_sin_clasificar_y_provisional_con_al12():
    res = correr([par(t(LUNES, 8), t(LUNES, 10))], [])
    assert total(res, clase=CLASE_SIN_CLASIFICAR) == 2 * H
    assert res.provisional is True and AL12 in res.alertas
    assert "horario_faltante" in res.motivos
    assert all(j.clasificacion is None for j in res.jornadas)


# --- P-29: etiquetas, nunca extras automaticos ---------------------------------------------------

def test_p29_domingo_trabajado_se_etiqueta_sin_asumir_extras():
    h = horario({6: DiaHorario((Intervalo(hs(7), hs(15)),))})
    res = correr([par(t(DOMINGO, 7), t(DOMINGO, 15))], [h])
    for s in res.segmentos:
        assert {"domingo", "domingo_trabajado"} <= s.etiquetas
        assert s.clase == CLASE_DENTRO  # el domingo programado no es exceso ni extra
    assert not any("extra" in e for s in res.segmentos for e in s.etiquetas)
    assert total(res) == 8 * H


def test_p29_festivo_trabajado_se_etiqueta_descanso_obligatorio_trabajado():
    h = horario({4: DiaHorario((Intervalo(hs(8), hs(16)),))})
    res = correr([par(t(date(2027, 1, 1), 8), t(date(2027, 1, 1), 16))], [h])
    assert all({"descanso_obligatorio", "descanso_obligatorio_trabajado"} <= s.etiquetas for s in res.segmentos)
    assert all(s.clase == CLASE_DENTRO for s in res.segmentos)


def test_p29_descanso_semanal_trabajado_es_exceso_etiquetado_no_extra():
    h = horario({0: DiaHorario((Intervalo(hs(8), hs(16)),))}, descansos_semanales=frozenset({6}))
    res = correr([par(t(DOMINGO, 8), t(DOMINGO, 10))], [h])
    assert all("descanso_semanal_trabajado" in s.etiquetas for s in res.segmentos)
    assert all(s.clase == CLASE_EXCESO for s in res.segmentos)


def test_p29_lo_pendiente_en_domingo_se_etiqueta_domingo_pero_no_como_trabajado():
    h = horario({6: DiaHorario((Intervalo(hs(8), hs(16)),))})
    res = correr([par(t(DOMINGO, 16), t(DOMINGO, 16, 20))], [h], versiones=BASE)  # sin tolerancias: pendiente
    assert res.segmentos and all(s.estado == PENDIENTE for s in res.segmentos)
    assert all("domingo" in s.etiquetas and "domingo_trabajado" not in s.etiquetas for s in res.segmentos)


def test_p29_la_continuacion_de_un_turno_nocturno_hereda_la_base_del_dia_logico():
    # lunes 22:00-05:00, el martes es descanso semanal: la parte del martes no es descanso trabajado
    h = horario({0: DiaHorario((Intervalo(hs(22), hs(29)),))}, regimen="nocturna", descansos_semanales=frozenset({1}))
    res = correr([par(t(LUNES, 22), t(MARTES, 5))], [h])
    assert all("descanso_semanal_trabajado" not in s.etiquetas for s in res.segmentos)


def test_calendario_faltante_o_ambiguo_degrada_a_provisional_sin_excepcion():
    h = horario({0: DiaHorario((Intervalo(hs(8), hs(16)),))})
    res = correr([par(t(LUNES, 8), t(LUNES, 16))], [h], calendarios=())
    assert res.provisional and AL12 in res.alertas and "calendario_faltante" in res.motivos
    assert total(res) == 8 * H
    doble = (CalendarioAnual(2027, frozenset(), confirmado=True), CalendarioAnual(2027, frozenset(), confirmado=True))
    res2 = correr([par(t(LUNES, 8), t(LUNES, 16))], [h], calendarios=doble)
    assert res2.provisional and "calendario_ambiguo" in res2.motivos


# --- Semana laboral ---------------------------------------------------------------------------

def test_la_semana_laboral_es_frontera_y_cada_segmento_lleva_su_semana():
    dia = DiaHorario((Intervalo(hs(22), hs(29)),))
    h = horario({6: dia}, regimen="nocturna")
    res = correr([par(t(DOMINGO_ANT, 22), t(LUNES, 5))], [h])  # domingo 22:00 -> lunes 05:00
    assert [s.fecha_real for s in res.segmentos] == [DOMINGO_ANT, LUNES]
    assert res.segmentos[0].semana == Vigencia(date(2026, 12, 28), LUNES)
    assert res.segmentos[1].semana == Vigencia(LUNES, date(2027, 1, 11))
    assert total(res) == 7 * H


def test_el_dia_de_inicio_de_semana_se_toma_de_la_politica_patronal_por_empresa():
    domingo_inicio = VersionParametro(
        n.SEMANA_INICIO_DIA, 6, Vigencia(date(2027, 1, 1)), "prueba", "patronal", "AEI"
    )
    versiones = BASE + (domingo_inicio,) + tuple(tol(10))
    h = horario({0: DiaHorario((Intervalo(hs(8), hs(16)),))})
    res = correr([par(t(LUNES, 8), t(LUNES, 16))], [h], versiones)
    assert res.segmentos[0].semana == Vigencia(DOMINGO_ANT, date(2027, 1, 10))


# --- Parametros faltantes o ambiguos: provisional, nunca excepcion ------------------------------

def test_sin_franja_nocturna_el_segmento_queda_sin_banda_y_provisional():
    versiones = tuple(v for v in BASE if v.clave != n.NOCTURNO_INICIO_S) + tuple(tol(10))
    h = horario({0: DiaHorario((Intervalo(hs(8), hs(16)),))})
    res = correr([par(t(LUNES, 8), t(LUNES, 16))], [h], versiones)
    assert total(res) == 8 * H
    assert all(s.banda is None for s in res.segmentos)
    assert res.provisional and AL12 in res.alertas and f"falta:{n.NOCTURNO_INICIO_S}" in res.motivos
    assert res.jornadas[0].clasificacion is None


def test_franja_ambigua_o_invalida_no_aborta_ni_inventa_criterio():
    duplicada = BASE + (VersionParametro(n.NOCTURNO_INICIO_S, hs(21), Vigencia(date(2026, 1, 1)), "dup"),)
    h = horario({0: DiaHorario((Intervalo(hs(8), hs(16)),))})
    res = correr([par(t(LUNES, 8), t(LUNES, 16))], [h], duplicada + tuple(tol(10)))
    assert res.provisional and f"parametro_ambiguo:{n.NOCTURNO_INICIO_S}" in res.motivos
    assert all(s.banda is None for s in res.segmentos)
    igual = tuple(v for v in BASE if v.clave != n.NOCTURNO_FIN_S) + (
        VersionParametro(n.NOCTURNO_FIN_S, hs(20), Vigencia(date(2026, 1, 1)), "prueba"),
    )
    res2 = correr([par(t(LUNES, 8), t(LUNES, 16))], [h], igual + tuple(tol(10)))
    assert res2.provisional and "franja_nocturna_invalida" in res2.motivos


def test_sin_dia_de_inicio_de_semana_el_segmento_queda_sin_semana_y_provisional():
    versiones = tuple(v for v in BASE if v.clave != n.SEMANA_INICIO_DIA) + tuple(tol(10))
    h = horario({0: DiaHorario((Intervalo(hs(8), hs(16)),))})
    res = correr([par(t(LUNES, 8), t(LUNES, 16))], [h], versiones)
    assert all(s.semana is None for s in res.segmentos)
    assert res.provisional and f"falta:{n.SEMANA_INICIO_DIA}" in res.motivos


def test_sin_umbral_nocturno_la_jornada_mixta_queda_sin_clasificar():
    versiones = tuple(v for v in BASE if v.clave != n.UMBRAL_NOCTURNA_S) + tuple(tol(10))
    h = horario({0: DiaHorario((Intervalo(hs(17), hs(23)),))}, regimen="mixta")
    res = correr([par(t(LUNES, 17), t(LUNES, 23))], [h], versiones)
    assert res.jornadas[0].clasificacion is None
    assert res.provisional and f"falta:{n.UMBRAL_NOCTURNA_S}" in res.motivos


# --- Propiedades con semillas fijas -------------------------------------------------------------

def _piezas_al_azar(rng):
    piezas, cursor = [], t(date(2026, 12, 26), 0)
    for _ in range(rng.randint(1, 12)):
        inicio = cursor + rng.randint(0, 20 * H)
        fin = inicio + rng.randint(1, 40 * H)
        cursor = fin
        piezas.append(PiezaEfectiva(
            Intervalo(inicio, fin), date(2027, 1, 1), date(2027, 1, 1), CHECADA,
            rng.choice([CONFIRMADO, PENDIENTE]),
            rng.choice([DENTRO_HORARIO, FUERA_HORARIO, DIA_NO_PROGRAMADO, SIN_HORARIO]),
        ))
    return piezas


def test_propiedad_la_suma_se_conserva_sin_traslapes_ni_cruces_de_frontera():
    for semilla in range(300):
        rng = random.Random(semilla)
        piezas = _piezas_al_azar(rng)
        res = segmentar(ResultadoEfectivo(tuple(piezas)), CDMX, [], [CAL], BASE)
        assert sum(s.intervalo.duracion for s in res.segmentos) == sum(p.intervalo.duracion for p in piezas), semilla
        ordenados = sorted(res.segmentos, key=lambda s: s.intervalo.inicio)
        for a, b in zip(ordenados, ordenados[1:]):
            assert a.intervalo.fin <= b.intervalo.inicio, semilla
        for s in res.segmentos:
            assert s.intervalo.duracion > 0
            ini = datetime.fromtimestamp(s.intervalo.inicio, tz=CDMX)
            fin = datetime.fromtimestamp(s.intervalo.fin - 1, tz=CDMX)
            assert ini.date() == fin.date() == s.fecha_real, semilla  # nunca cruza medianoche ni semana
            assert s.semana is not None and s.semana.contiene(s.fecha_real)
            if s.banda == BANDA_NOCTURNA:
                assert (ini.hour >= 20 or ini.hour < 6) and (fin.hour >= 20 or fin.hour < 6), semilla
            else:
                assert s.banda == BANDA_DIURNA
                assert 6 <= ini.hour < 20 and 6 <= fin.hour < 20, semilla


def test_propiedad_entradas_permutadas_dan_el_mismo_resultado():
    for semilla in range(100):
        rng = random.Random(semilla)
        piezas = _piezas_al_azar(rng)
        mezcladas = list(piezas)
        rng.shuffle(mezcladas)
        a = segmentar(ResultadoEfectivo(tuple(piezas)), CDMX, [], [CAL], BASE)
        b = segmentar(ResultadoEfectivo(tuple(mezcladas)), CDMX, [], [CAL], BASE)
        assert a == b, semilla
