"""Criterio de inicio de extra `semanal_con_acuerdo` (plan 5.2, doc. 03 8.2 pasos 9-10; decision Q05).

Cuanto: extra semanal = max(0, confirmado - tope ordinario semanal vigente). Donde: solo en segmentos de
exceso diario, los mas recientes primero (los mas antiguos compensan faltantes); si sobra, a los ultimos
minutos programados + HO03. Casos: ejemplos del plan 5.2, P-01, P-02, P-06, P-07, P-32, P-46 y
propiedades con semillas fijas. Los topes salen siempre de `resolver_vigente` (aqui, de la semilla)."""
import random
from dataclasses import replace
from datetime import date, timedelta

import pytest

from Dominio import normatividad as n
from Dominio.calendario import AL12
from Dominio.criterios_extra import (
    CODIGO_SEMANAL_CON_ACUERDO,
    CRITERIOS,
    EXTRA,
    ORDINARIO,
    ORIGEN_EXCESO,
    ORIGEN_REMANENTE,
    PENDIENTE,
    AsignacionSemana,
    CriterioDesconocido,
    CriterioExtra,
    PiezaAsignada,
    asignar_extra,
    obtener_criterio,
)
from Dominio.horarios import CONFIRMADO, HO03, PENDIENTE as ESTADO_PENDIENTE, Confirmacion
from Dominio.modelos import VersionParametro, Vigencia
from Dominio.segmentacion import (
    BANDA_DIURNA,
    CLASE_DENTRO,
    CLASE_EXCESO,
    CLASE_SIN_CLASIFICAR,
    ResultadoSegmentacion,
    Segmento,
)
from Dominio.tiempo import Intervalo, fecha_local
from _semanas_extra import (
    BASE,
    CDMX,
    H,
    LUN_2026,
    LUN_2027,
    M,
    PROGRAMA_46,
    dia_de,
    segmentar_semana,
    t,
)


def exacto(programa=None):
    return {d: list(p) for d, p in (PROGRAMA_46 if programa is None else programa).items()}


def semana_asignada(lunes, trabajado, programa=None, **kw):
    seg, versiones = segmentar_semana(lunes, trabajado, programa, **kw)
    asignaciones = asignar_extra(seg, versiones)
    assert len(asignaciones) == 1
    return asignaciones[0]


def extras(asig, origen=None):
    return [p for p in asig.piezas if p.tipo == EXTRA and (origen is None or p.origen == origen)]


def intervalos_extra(asig):
    return [(p.segmento.intervalo.inicio, p.segmento.intervalo.fin) for p in extras(asig)]


# --- Registro y Protocol -----------------------------------------------------------------------

def test_el_registro_ofrece_semanal_con_acuerdo_y_cumple_el_protocol():
    criterio = obtener_criterio(CODIGO_SEMANAL_CON_ACUERDO)
    assert CODIGO_SEMANAL_CON_ACUERDO == "semanal_con_acuerdo"
    assert criterio.codigo == CODIGO_SEMANAL_CON_ACUERDO
    assert isinstance(criterio, CriterioExtra)
    assert CRITERIOS[CODIGO_SEMANAL_CON_ACUERDO] is criterio


def test_un_criterio_desconocido_se_rechaza_sin_inventar_otro():
    with pytest.raises(CriterioDesconocido):
        obtener_criterio("inventado")


def test_se_agrega_otro_criterio_sin_tocar_el_resto(monkeypatch):
    class TodoOrdinario:
        codigo = "todo_ordinario"

        def asignar(self, segmentos, jornadas, versiones, semana):
            confirmados = [s for s in segmentos if s.estado == CONFIRMADO]
            return AsignacionSemana(
                semana, self.codigo, tuple(PiezaAsignada(s, ORDINARIO) for s in confirmados),
                tuple(s for s in segmentos if s.estado != CONFIRMADO), tuple(jornadas),
            )

    monkeypatch.setitem(CRITERIOS, "todo_ordinario", TodoOrdinario())
    seg, versiones = segmentar_semana(LUN_2027, {**exacto(), 0: [(8, 20)]})
    asig = asignar_extra(seg, versiones, criterio="todo_ordinario")[0]
    assert asig.criterio == "todo_ordinario" and asig.extra_s == 0
    assert asig.ordinario_s == asig.confirmado_s


# --- Cuanto y donde: ejemplos del plan 5.2 ------------------------------------------------------

def test_p02_2027_horario_46_trabajo_48_con_2h_fuera_de_horario_da_2h_extra_en_el_exceso():
    asig = semana_asignada(LUN_2027, {**exacto(), 0: [(8, 18)]})
    assert asig.semana == Vigencia(LUN_2027, LUN_2027 + timedelta(days=7))
    assert asig.confirmado_s == 48 * H
    assert (asig.ordinario_s, asig.extra_s, asig.pendiente_s) == (46 * H, 2 * H, 0)
    assert intervalos_extra(asig) == [(t(LUN_2027, 16), t(LUN_2027, 18))]
    assert extras(asig)[0].origen == ORIGEN_EXCESO
    assert asig.tope_semanal_s == 46 * H
    assert asig.provisional is False and HO03 not in asig.alertas


def test_p01_2026_48_horas_acordadas_trabajadas_son_48_ordinarias_sin_extra():
    programa = {d: [(8, 16)] for d in range(6)}
    asig = semana_asignada(LUN_2026, exacto(programa), programa)
    assert (asig.confirmado_s, asig.ordinario_s, asig.extra_s) == (48 * H, 48 * H, 0)
    assert asig.tope_semanal_s == 48 * H and asig.alertas == ()


def test_plan_52_ejemplo_06_50_12_13_16_25_son_8h_normales_y_35_min_extra():
    programa = {**PROGRAMA_46, 0: [(7, 12), (13, 16)]}
    trabajado = {**exacto(programa), 0: [((6, 50), 12), (13, (16, 25))]}
    asig = semana_asignada(LUN_2027, trabajado, programa)  # tolerancia 0: todo lo de fuera es trabajo confirmado
    assert asig.extra_s == 35 * M and asig.ordinario_s == 46 * H
    assert intervalos_extra(asig) == [
        (t(LUN_2027, (6, 50)), t(LUN_2027, 7)),
        (t(LUN_2027, 16), t(LUN_2027, (16, 25))),
    ]
    lunes_normal = sum(
        p.segmento.intervalo.duracion for p in asig.piezas if p.tipo == ORDINARIO and p.segmento.dia_logico == LUN_2027
    )
    assert lunes_normal == 8 * H


def test_plan_52_ejemplo_si_los_10_min_previos_fueron_solo_presencia_son_25_min_extra():
    programa = {**PROGRAMA_46, 0: [(7, 12), (13, 16)]}
    trabajado = {**exacto(programa), 0: [((6, 50), 12), (13, (16, 25))]}
    presencia = Confirmacion(Intervalo(t(LUN_2027, (6, 50)), t(LUN_2027, 7)), trabajado=False)
    asig = semana_asignada(LUN_2027, trabajado, programa, confirmaciones=(presencia,))
    assert asig.extra_s == 25 * M
    assert sum(s.intervalo.duracion for s in asig.no_confirmados) == 10 * M  # nunca se pierde: queda visible


def test_plan_52_ejemplo_si_no_se_sabe_lo_dudoso_queda_pendiente_y_no_cuenta_como_extra():
    programa = {**PROGRAMA_46, 0: [(7, 12), (13, 16)]}
    trabajado = {**exacto(programa), 0: [((6, 50), 12), (13, (16, 25))]}
    asig = semana_asignada(LUN_2027, trabajado, programa, tolerancia=10)
    assert all(s.estado == ESTADO_PENDIENTE for s in asig.no_confirmados)
    assert sum(s.intervalo.duracion for s in asig.no_confirmados) == 20 * M  # 10 min antes y 10 min despues
    assert asig.extra_s == 15 * M  # solo lo confirmado fuera de la ventana de tolerancia


def test_plan_52_compensacion_5x8_mas_6_con_46_horas_no_hay_extra():
    trabajado = {**exacto(), 0: [(8, 18)], 1: [(8, 18)], 2: [(8, 12)]}  # 10 + 10 + 4 + 8 + 8 + 6 = 46
    asig = semana_asignada(LUN_2027, trabajado)
    assert asig.confirmado_s == 46 * H
    assert asig.extra_s == 0 and asig.ordinario_s == 46 * H


def test_plan_52_compensacion_con_48_horas_la_extra_cae_en_el_exceso_mas_reciente_el_martes():
    trabajado = {**exacto(), 0: [(8, 18)], 1: [(8, 18)], 2: [(8, 14)]}  # 10 + 10 + 6 + 8 + 8 + 6 = 48
    asig = semana_asignada(LUN_2027, trabajado)
    assert asig.extra_s == 2 * H
    assert intervalos_extra(asig) == [(t(dia_de(LUN_2027, 1), 16), t(dia_de(LUN_2027, 1), 18))]  # martes, no lunes


def test_plan_52_cinco_por_ocho_mas_seis_trabajando_9_horas_los_seis_dias_son_8_horas_extra():
    trabajado = {d: [(8, 17)] for d in range(6)}  # 54 h
    asig = semana_asignada(LUN_2027, trabajado)
    assert asig.confirmado_s == 54 * H and asig.extra_s == 8 * H
    por_dia = {}
    for p in extras(asig):
        por_dia[p.segmento.dia_logico] = por_dia.get(p.segmento.dia_logico, 0) + p.segmento.intervalo.duracion
    assert [por_dia[dia_de(LUN_2027, d)] for d in range(6)] == [H, H, H, H, H, 3 * H]
    assert all(p.origen == ORIGEN_EXCESO for p in extras(asig))


def test_plan_52_ejemplo_2027_40h_mas_sabado_07_13_trabajado_hasta_las_15_son_2h_extra():
    programa = {**{d: [(8, 16)] for d in range(5)}, 5: [(7, 13)]}
    asig = semana_asignada(LUN_2027, {**exacto(programa), 5: [(7, 15)]}, programa)
    assert asig.extra_s == 2 * H
    assert intervalos_extra(asig) == [(t(dia_de(LUN_2027, 5), 13), t(dia_de(LUN_2027, 5), 15))]
    assert asig.ordinario_s == 46 * H


def test_plan_52_horario_48_horas_trabajado_exacto_asigna_2h_a_los_ultimos_minutos_programados_y_ho03():
    programa = {d: [(8, 16)] for d in range(6)}  # 6 x 8 = 48 h en 2027
    asig = semana_asignada(LUN_2027, exacto(programa), programa)
    assert asig.extra_s == 2 * H and asig.ordinario_s == 46 * H
    assert intervalos_extra(asig) == [(t(dia_de(LUN_2027, 5), 14), t(dia_de(LUN_2027, 5), 16))]
    assert all(p.origen == ORIGEN_REMANENTE for p in extras(asig))
    assert HO03 in asig.alertas
    assert asig.provisional is False  # el tiempo no se pierde ni se bloquea el calculo


def test_el_remanente_recorre_los_dias_en_orden_cronologico_inverso():
    programa = {d: [(8, 16)] for d in range(6)}
    trabajado = {**exacto(programa), 0: [(8, 20)]}  # 4 h de exceso el lunes + 48 h programadas = 52 h
    asig = semana_asignada(LUN_2027, trabajado, programa)
    assert asig.extra_s == 6 * H
    assert sum(p.segmento.intervalo.duracion for p in extras(asig, ORIGEN_EXCESO)) == 4 * H
    # el remanente de 2 h sale del final de la semana, no del lunes
    assert intervalos_extra(asig)[-1] == (t(dia_de(LUN_2027, 5), 14), t(dia_de(LUN_2027, 5), 16))


def test_la_extra_parcial_toma_los_ultimos_segundos_del_segmento_de_exceso_y_el_resto_es_ordinario():
    trabajado = {**exacto(), 0: [(8, 20)], 2: [(8, 13)]}  # 12 + 8 + 5 + 8 + 8 + 6 = 47 h
    asig = semana_asignada(LUN_2027, trabajado)
    assert asig.extra_s == H
    assert intervalos_extra(asig) == [(t(LUN_2027, 19), t(LUN_2027, 20))]
    ordinario_lunes = sum(
        p.segmento.intervalo.duracion for p in asig.piezas if p.tipo == ORDINARIO and p.segmento.dia_logico == LUN_2027
    )
    assert ordinario_lunes == 11 * H  # 8 programadas + 3 de exceso que compensan el miercoles corto


def test_p06_p07_con_el_criterio_semanal_vigente_los_dias_cortos_compensan_a_los_largos():
    # La matriz (cap. 9) fue escrita con el criterio diario: P-06 espera 2 extras y P-07 espera 2 extras y 2
    # faltantes. Con el criterio semanal adoptado (Q05, plan 5.2, tope vigente 46 h) no hay extra en ninguno:
    # divergencia consultada al propietario (ver reporte de T5). Aqui se fija el comportamiento adoptado.
    programa_40 = {d: [(8, 16)] for d in range(5)}
    p06 = semana_asignada(LUN_2027, {**exacto(programa_40), 0: [(8, 18)]}, programa_40)
    assert (p06.confirmado_s, p06.extra_s) == (42 * H, 0)
    p07 = semana_asignada(LUN_2027, {**exacto(), 0: [(8, 18)], 1: [(8, 14)]})
    assert (p07.confirmado_s, p07.extra_s) == (46 * H, 0)


def test_lo_no_confirmado_no_cuenta_para_el_tope_y_se_conserva_aparte():
    asig = semana_asignada(LUN_2027, {**exacto(), 0: [(8, 16), (16, (16, 10))]}, tolerancia=10)
    assert asig.confirmado_s == 46 * H
    assert sum(s.intervalo.duracion for s in asig.no_confirmados) == 10 * M
    assert asig.extra_s == 0


# --- P-46: la semana no se parte por el cierre de mes -------------------------------------------

def test_p46_semana_de_nomina_partida_por_cierre_de_mes_se_acumula_sin_reinicio():
    lunes = date(2027, 3, 29)  # lunes a miercoles en marzo, jueves a domingo en abril
    asig = semana_asignada(lunes, {d: [(8, 17)] for d in range(6)})
    assert asig.semana == Vigencia(lunes, date(2027, 4, 5))
    assert asig.extra_s == 8 * H
    assert {p.segmento.fecha_real.month for p in extras(asig)} == {3, 4}
    igual = semana_asignada(LUN_2027, {d: [(8, 17)] for d in range(6)})
    assert [p.segmento.intervalo.duracion for p in extras(asig)] == [
        p.segmento.intervalo.duracion for p in extras(igual)
    ]


# --- Datos faltantes o semana de transicion: provisional, nunca excepcion ni criterio inventado -----

def sin(clave):
    return tuple(v for v in BASE if v.clave != clave)


def test_sin_tope_semanal_vigente_la_semana_queda_pendiente_provisional_con_al12():
    asig = semana_asignada(LUN_2027, {**exacto(), 0: [(8, 18)]}, versiones=sin(n.ORDINARIA_SEMANAL_S))
    assert asig.provisional and AL12 in asig.alertas and f"falta:{n.ORDINARIA_SEMANAL_S}" in asig.motivos
    assert asig.tope_semanal_s is None
    assert (asig.ordinario_s, asig.extra_s, asig.pendiente_s) == (0, 0, 48 * H)  # nada se pierde ni se inventa
    assert all(p.motivo == f"falta:{n.ORDINARIA_SEMANAL_S}" for p in asig.piezas)


def test_tope_semanal_ambiguo_tampoco_aborta():
    duplicado = BASE + (VersionParametro(n.ORDINARIA_SEMANAL_S, 45 * H, Vigencia(date(2027, 1, 1)), "dup"),)
    asig = semana_asignada(LUN_2027, exacto(), versiones=duplicado)
    assert asig.provisional and f"parametro_ambiguo:{n.ORDINARIA_SEMANAL_S}" in asig.motivos
    assert asig.pendiente_s == asig.confirmado_s


def test_semana_de_transicion_28_12_2026_a_03_01_2027_no_prorratea_ni_aplica_46_o_48_a_toda_la_semana():
    programa = {d: [(8, 16)] for d in range(6)}  # 6 x 8 = 48 h
    trabajado = {**exacto(programa), 0: [(8, 17)]}  # 49 h
    asig = semana_asignada(date(2026, 12, 28), trabajado, programa)
    assert asig.provisional and AL12 in asig.alertas
    assert f"semana_transicion:{n.ORDINARIA_SEMANAL_S}" in asig.motivos
    # Con 48 h hay 1 h de extra segura (la mas reciente); con 46 h hay 3 h: las 2 h de diferencia (las
    # mas antiguas de la extra posible) quedan pendientes de criterio, sin decidirlas.
    assert asig.extra_s == H and asig.pendiente_s == 2 * H
    assert asig.ordinario_s == 46 * H
    assert asig.tope_semanal_s is None  # no hay un solo tope en la semana
    assert all(p.motivo == f"semana_transicion:{n.ORDINARIA_SEMANAL_S}" for p in asig.piezas if p.tipo == PENDIENTE)
    assert intervalos_extra(asig) == [(t(dia_de(date(2026, 12, 28), 5), 15), t(dia_de(date(2026, 12, 28), 5), 16))]


def test_sin_semana_resuelta_todo_lo_confirmado_queda_pendiente():
    seg, versiones = segmentar_semana(LUN_2027, exacto(), versiones=sin(n.SEMANA_INICIO_DIA))
    asignaciones = asignar_extra(seg, versiones)
    assert len(asignaciones) == 1 and asignaciones[0].semana is None
    asig = asignaciones[0]
    assert asig.provisional and "semana_sin_resolver" in asig.motivos
    assert asig.pendiente_s == asig.confirmado_s == 46 * H


def test_sin_dias_programados_todo_es_exceso_y_la_extra_cae_en_lo_mas_reciente():
    seg, versiones = segmentar_semana(LUN_2027, {d: [(8, 17)] for d in range(6)}, programa={})
    # horario sin dias programados: todo es dia no programado (exceso); 54 h - 46 h = 8 h al final
    asig = asignar_extra(seg, versiones)[0]
    assert asig.extra_s == 8 * H


# --- Determinismo (P-32) y propiedades con semillas fijas ----------------------------------------

def test_p32_el_orden_de_los_segmentos_no_cambia_el_resultado():
    seg, versiones = segmentar_semana(LUN_2027, {d: [(8, 17)] for d in range(6)})
    invertida = replace(seg, segmentos=tuple(reversed(seg.segmentos)))
    assert asignar_extra(seg, versiones) == asignar_extra(invertida, versiones)


def _segmento(inicio, fin, clase, estado, lunes):
    dia = fecha_local(inicio, CDMX)
    return Segmento(
        Intervalo(inicio, fin), dia, dia, Vigencia(lunes, lunes + timedelta(days=7)), clase, BANDA_DIURNA,
        frozenset(), "checada", estado, "x",
    )


def _semana_al_azar(rng, lunes):
    cursor, fin_semana, segmentos = t(lunes, 0), t(lunes + timedelta(days=7), 0), []
    for _ in range(rng.randint(1, 14)):
        inicio = cursor + rng.randint(0, 6 * H)
        fin = inicio + rng.choice([1, 59, M, 90 * M, rng.randint(1, 10 * H)])
        if fin > fin_semana:
            break
        cursor = fin
        segmentos.append(_segmento(
            inicio, fin, rng.choice([CLASE_DENTRO, CLASE_EXCESO, CLASE_EXCESO, CLASE_SIN_CLASIFICAR]),
            rng.choice([CONFIRMADO, CONFIRMADO, ESTADO_PENDIENTE]), lunes,
        ))
    return segmentos


def test_propiedad_ordinario_mas_extra_mas_pendiente_es_el_confirmado_y_la_extra_es_max_0_confirmado_menos_tope():
    tope = 46 * H
    for semilla in range(400):
        rng = random.Random(semilla)
        segmentos = _semana_al_azar(rng, LUN_2027)
        asig = asignar_extra(ResultadoSegmentacion(tuple(segmentos)), BASE)[0]
        confirmado = sum(s.intervalo.duracion for s in segmentos if s.estado == CONFIRMADO)
        assert asig.confirmado_s == confirmado, semilla
        assert asig.ordinario_s + asig.extra_s + asig.pendiente_s == confirmado, semilla
        assert asig.pendiente_s == 0 and asig.extra_s == max(0, confirmado - tope), semilla
        # sin segundos duplicados ni perdidos: cada segmento se reparte exactamente en sus piezas
        for original in segmentos:
            if original.estado != CONFIRMADO:
                continue
            partes = sorted(
                (p.segmento.intervalo for p in asig.piezas if original.intervalo.contiene(p.segmento.intervalo.inicio)),
                key=lambda i: i.inicio,
            )
            assert partes[0].inicio == original.intervalo.inicio and partes[-1].fin == original.intervalo.fin, semilla
            assert all(a.fin == b.inicio for a, b in zip(partes, partes[1:])), semilla
        assert all(p.segmento.intervalo.duracion > 0 for p in asig.piezas), semilla


def test_propiedad_la_extra_solo_cae_en_exceso_o_en_el_remanente_programado_y_en_lo_mas_reciente():
    for semilla in range(400):
        rng = random.Random(semilla)
        asig = asignar_extra(ResultadoSegmentacion(tuple(_semana_al_azar(rng, LUN_2027))), BASE)[0]
        de_exceso = [p for p in extras(asig, ORIGEN_EXCESO)]
        assert all(p.segmento.clase in (CLASE_EXCESO, CLASE_SIN_CLASIFICAR) for p in de_exceso), semilla
        assert all(p.segmento.clase == CLASE_DENTRO for p in extras(asig, ORIGEN_REMANENTE)), semilla
        if extras(asig, ORIGEN_REMANENTE):
            assert HO03 in asig.alertas, semilla
            # el remanente solo existe si TODO el exceso ya es extra
            assert not any(
                p.tipo == ORDINARIO and p.segmento.clase in (CLASE_EXCESO, CLASE_SIN_CLASIFICAR) for p in asig.piezas
            ), semilla
        elif HO03 in asig.alertas:
            pytest.fail(f"HO03 sin remanente (semilla {semilla})")
        ordinario_exceso = [
            p.segmento.intervalo for p in asig.piezas
            if p.tipo == ORDINARIO and p.segmento.clase in (CLASE_EXCESO, CLASE_SIN_CLASIFICAR)
        ]
        if de_exceso and ordinario_exceso:  # mas antiguo = ordinario; mas reciente = extra
            assert max(i.fin for i in ordinario_exceso) <= min(p.segmento.intervalo.inicio for p in de_exceso), semilla


def test_propiedad_entradas_permutadas_dan_el_mismo_resultado():
    for semilla in range(150):
        rng = random.Random(semilla)
        segmentos = _semana_al_azar(rng, LUN_2027)
        mezcladas = list(segmentos)
        rng.shuffle(mezcladas)
        a = asignar_extra(ResultadoSegmentacion(tuple(segmentos)), BASE)
        b = asignar_extra(ResultadoSegmentacion(tuple(mezcladas)), BASE)
        assert a == b, semilla


def test_propiedad_el_tope_se_lee_de_la_version_vigente_y_no_del_codigo():
    otro = tuple(v for v in BASE if v.clave != n.ORDINARIA_SEMANAL_S) + (
        VersionParametro(n.ORDINARIA_SEMANAL_S, 40 * H, Vigencia(date(2026, 1, 1)), "prueba"),
    )
    seg, _ = segmentar_semana(LUN_2027, {d: [(8, 17)] for d in range(6)})
    asig = asignar_extra(seg, otro)[0]
    assert asig.tope_semanal_s == 40 * H and asig.extra_s == 14 * H
