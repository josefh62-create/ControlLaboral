"""construir_intervalos_efectivos (paso 6): descansos segun horario, complementos aprobados,
tolerancias sin alterar tiempo fisico y pendientes. P-18..P-25 (parte de tiempo efectivo),
P-26, P-33, P-45, plan 5.2 (ejemplo 06:50/12:00/13:00/16:25)."""
import random
from datetime import date, datetime
from zoneinfo import ZoneInfo

from Dominio.calendario import AL12
from Dominio.checadas import Checada
from Dominio.emparejamiento import NORMAL, TRASLADO, IntervaloEmparejado
from Dominio.horarios import (
    CHECADA,
    COMPLEMENTO,
    CONFIRMADO,
    DENTRO_HORARIO,
    DESCANSO_COMPUTABLE,
    DESCANSO_NO_COMPUTABLE,
    DIA_NO_PROGRAMADO,
    FUERA_HORARIO,
    NO_LABORADO,
    PENDIENTE,
    SIN_HORARIO,
    Complemento,
    Confirmacion,
    DescansoHorario,
    DiaHorario,
    Horario,
    construir_intervalos_efectivos,
)
from Dominio.modelos import Vigencia
from Dominio.tiempo import Intervalo, instante_local
from Dominio.tolerancias import CLAVES_TOLERANCIA, Tolerancias, version_de_tolerancia

CDMX = ZoneInfo("America/Mexico_City")
H, M = 3600, 60
LUNES, MARTES, DOMINGO = date(2027, 1, 4), date(2027, 1, 5), date(2027, 1, 10)
D2027 = Vigencia(date(2027, 1, 1), date(2028, 1, 1))


def t(fecha, h, m=0, s=0):
    return instante_local(fecha, h * H + m * M + s, CDMX)


def par(inicio, fin, empresa="AEI", reloj="R-AEI", etiqueta=NORMAL, empresa_hasta=None):
    def ck(id_, s, emp):
        return Checada(id_, datetime.fromtimestamp(s, tz=CDMX), reloj, emp)

    return IntervaloEmparejado(
        Intervalo(inicio, fin), ck(f"e{inicio}", inicio, empresa), ck(f"s{fin}", fin, empresa_hasta or empresa), etiqueta
    )


def hs(h, m=0):
    return h * H + m * M


def horario_partido(**kw):
    """Plan 5.2: 07:00-12:00 y 13:00-16:00 (8 h) todos los lunes."""
    dia = DiaHorario((Intervalo(hs(7), hs(12)), Intervalo(hs(13), hs(16))))
    return Horario("HP", D2027, "diurna", "America/Mexico_City", {0: dia}, empresa="AEI", **kw)


def horario_continuo(descanso=None, **kw):
    dia = DiaHorario((Intervalo(hs(7), hs(16)),), (descanso,) if descanso else ())
    return Horario("HC", D2027, "diurna", "America/Mexico_City", {0: dia}, empresa="AEI", **kw)


def tol(minutos, empresa="AEI"):
    return [version_de_tolerancia(k, minutos, Vigencia(date(2027, 1, 1)), "prueba", empresa) for k in CLAVES_TOLERANCIA]


def efectivos(pares, horarios, **kw):
    kw.setdefault("versiones", tol(10))
    return construir_intervalos_efectivos(pares, horarios, CDMX, **kw)


def total(res, **filtros):
    return sum(
        p.intervalo.duracion for p in res.piezas
        if all(getattr(p, k) == v for k, v in filtros.items())
    )


# --- Plan 5.2: ejemplo 06:50 / 12:00 / 13:00 / 16:25 -----------------------------------------

def ejemplo_plan():
    return [par(t(LUNES, 6, 50), t(LUNES, 12)), par(t(LUNES, 13), t(LUNES, 16, 25))]


def test_plan52_sin_certeza_las_ventanas_de_tolerancia_quedan_pendientes_y_lo_demas_se_cuenta():
    res = efectivos(ejemplo_plan(), [horario_partido()])
    assert total(res, ubicacion=DENTRO_HORARIO, estado=CONFIRMADO) == 8 * H
    assert total(res, ubicacion=FUERA_HORARIO, estado=CONFIRMADO) == 15 * M  # 16:10-16:25
    assert total(res, estado=PENDIENTE) == 20 * M  # 06:50-07:00 y 16:00-16:10
    assert res.provisional is False


def test_plan52_con_trabajo_acreditado_todo_lo_fuera_de_horario_se_reconoce_sin_tocar_el_horario():
    confirmaciones = [
        Confirmacion(Intervalo(t(LUNES, 6, 50), t(LUNES, 7)), True, "reparto previo"),
        Confirmacion(Intervalo(t(LUNES, 16), t(LUNES, 16, 10)), True, "cierre"),
    ]
    res = efectivos(ejemplo_plan(), [horario_partido()], confirmaciones=confirmaciones)
    assert total(res, ubicacion=DENTRO_HORARIO) == 8 * H  # la tolerancia no suma horas ordinarias
    assert total(res, ubicacion=FUERA_HORARIO, estado=CONFIRMADO) == 35 * M
    assert total(res, estado=PENDIENTE) == 0


def test_plan52_si_los_10_min_previos_fueron_solo_presencia_quedan_no_laborados():
    confirmaciones = [Confirmacion(Intervalo(t(LUNES, 6, 50), t(LUNES, 7)), False, "esperaba para checar")]
    res = efectivos(ejemplo_plan(), [horario_partido()], confirmaciones=confirmaciones)
    assert total(res, estado=NO_LABORADO) == 10 * M
    assert total(res, ubicacion=FUERA_HORARIO, estado=CONFIRMADO) == 15 * M
    assert total(res, estado=PENDIENTE) == 10 * M  # los 10 min de 16:00-16:10 siguen sin certeza


# --- TO04 / TO06: P-21, P-22, P-23 -------------------------------------------------------------

def test_p21_salida_1610_con_tolerancia_10_y_trabajo_acreditado_conserva_10_min_fuera_de_horario():
    pares = [par(t(LUNES, 7), t(LUNES, 12)), par(t(LUNES, 13), t(LUNES, 16, 10))]
    confirmacion = [Confirmacion(Intervalo(t(LUNES, 16), t(LUNES, 16, 10)), True, "trabajo hasta las 16:10")]
    res = efectivos(pares, [horario_partido()], confirmaciones=confirmacion)
    assert total(res, ubicacion=FUERA_HORARIO, estado=CONFIRMADO) == 10 * M
    assert total(res, ubicacion=DENTRO_HORARIO) == 8 * H


def test_p22_salida_1610_sin_certeza_deja_10_min_pendientes_y_el_original_intacto():
    pares = [par(t(LUNES, 7), t(LUNES, 12)), par(t(LUNES, 13), t(LUNES, 16, 10))]
    res = efectivos(pares, [horario_partido()])
    assert total(res, estado=PENDIENTE, ubicacion=FUERA_HORARIO) == 10 * M
    assert pares[1].intervalo == Intervalo(t(LUNES, 13), t(LUNES, 16, 10))  # entrada original sin tocar
    assert total(res) == 5 * H + 3 * H + 10 * M  # todo el tiempo fisico esta representado


def test_p23_entrada_anticipada_efectiva_de_10_min_es_fuera_de_horario_aunque_este_en_tolerancia():
    pares = [par(t(LUNES, 6, 50), t(LUNES, 12)), par(t(LUNES, 13), t(LUNES, 16))]
    confirmacion = [Confirmacion(Intervalo(t(LUNES, 6, 50), t(LUNES, 7)), True, "efectivo")]
    res = efectivos(pares, [horario_partido()], confirmaciones=confirmacion)
    assert total(res, ubicacion=FUERA_HORARIO, estado=CONFIRMADO) == 10 * M
    assert total(res, ubicacion=DENTRO_HORARIO) == 8 * H


def test_to04_tolerancia_cero_no_crea_ventana_de_pendientes():
    pares = [par(t(LUNES, 7), t(LUNES, 12)), par(t(LUNES, 13), t(LUNES, 16, 10))]
    res = efectivos(pares, [horario_partido()], versiones=tol(0))
    assert total(res, estado=PENDIENTE) == 0
    assert total(res, ubicacion=FUERA_HORARIO, estado=CONFIRMADO) == 10 * M


def test_to06_la_permanencia_mas_alla_de_la_tolerancia_se_cuenta_como_exceso_sin_borrarla():
    pares = [par(t(LUNES, 7), t(LUNES, 12)), par(t(LUNES, 13), t(LUNES, 17))]
    res = efectivos(pares, [horario_partido()])
    assert total(res, estado=PENDIENTE) == 10 * M  # 16:00-16:10
    assert total(res, ubicacion=FUERA_HORARIO, estado=CONFIRMADO) == 50 * M  # 16:10-17:00


def test_la_tolerancia_del_horario_prevalece_sobre_la_de_la_empresa():
    propias = Tolerancias.desde_minutos(0, 0, 0, 3, 0)
    pares = [par(t(LUNES, 7), t(LUNES, 12)), par(t(LUNES, 13), t(LUNES, 16, 10))]
    res = efectivos(pares, [horario_partido(tolerancias=propias)])
    assert total(res, estado=PENDIENTE) == 3 * M and total(res, ubicacion=FUERA_HORARIO, estado=CONFIRMADO) == 7 * M


def test_sin_tolerancias_configuradas_es_provisional_con_al12_y_nada_se_pierde():
    pares = [par(t(LUNES, 7), t(LUNES, 12)), par(t(LUNES, 13), t(LUNES, 16, 10))]
    res = efectivos(pares, [horario_partido()], versiones=())
    assert res.provisional is True and AL12 in res.alertas
    assert any(m.startswith("falta:") for m in res.motivos)
    assert total(res) == 5 * H + 3 * H + 10 * M


# --- Descansos segun horario (Q03): P-24, P-25 ----------------------------------------------------

def test_p24_comida_no_computable_de_60_min_se_excluye_aunque_no_haya_checada():
    h = horario_continuo(DescansoHorario(Intervalo(hs(12), hs(13)), False, "art. 63"))
    res = efectivos([par(t(LUNES, 7), t(LUNES, 17))], [h], versiones=tol(0))
    assert total(res, estado=DESCANSO_NO_COMPUTABLE) == H
    efectivo = sum(p.intervalo.duracion for p in res.piezas if p.estado == CONFIRMADO)
    assert efectivo == 9 * H == res.confirmado_s
    assert total(res, ubicacion=DENTRO_HORARIO, estado=CONFIRMADO) == 8 * H
    assert total(res, ubicacion=FUERA_HORARIO, estado=CONFIRMADO) == H  # 16:00-17:00


def test_p24_si_el_trabajador_checo_la_comida_no_se_resta_dos_veces():
    h = horario_continuo(DescansoHorario(Intervalo(hs(12), hs(13)), False))
    res = efectivos([par(t(LUNES, 7), t(LUNES, 12)), par(t(LUNES, 13), t(LUNES, 16))], [h])
    assert total(res, estado=DESCANSO_NO_COMPUTABLE) == 0
    assert res.confirmado_s == 8 * H


def test_p25_comida_computable_de_30_min_se_incluye_aunque_el_trabajador_haya_checado():
    h = horario_continuo(DescansoHorario(Intervalo(hs(12), hs(12, 30)), True, "art. 64"))
    corrido = efectivos([par(t(LUNES, 7), t(LUNES, 16))], [h])
    assert corrido.confirmado_s == 9 * H
    con_checada = efectivos([par(t(LUNES, 7), t(LUNES, 12)), par(t(LUNES, 12, 30), t(LUNES, 16))], [h])
    assert con_checada.confirmado_s == 9 * H
    relleno = [p for p in con_checada.piezas if p.origen == DESCANSO_COMPUTABLE]
    assert [p.intervalo for p in relleno] == [Intervalo(t(LUNES, 12), t(LUNES, 12, 30))]
    assert relleno[0].ubicacion == DENTRO_HORARIO and relleno[0].estado == CONFIRMADO


def test_descanso_computable_no_se_rellena_si_no_hay_trabajo_despues():
    h = horario_continuo(DescansoHorario(Intervalo(hs(12), hs(12, 30)), True))
    res = efectivos([par(t(LUNES, 7), t(LUNES, 12))], [h])
    assert total(res, origen=DESCANSO_COMPUTABLE) == 0
    assert res.confirmado_s == 5 * H


# --- Complementos aprobados --------------------------------------------------------------------------

def test_complemento_aprobado_se_incorpora_con_su_origen_marcado():
    comp = Complemento("C-1", Intervalo(t(LUNES, 7), t(LUNES, 16)), "AEI", aprobado=True)
    res = efectivos([], [horario_continuo()], complementos=[comp])
    assert {p.origen for p in res.piezas} == {COMPLEMENTO}
    assert {p.referencia for p in res.piezas} == {"C-1"}
    assert res.confirmado_s == 9 * H


def test_complemento_no_aprobado_queda_pendiente_y_no_se_cuenta():
    comp = Complemento("C-2", Intervalo(t(LUNES, 7), t(LUNES, 16)), "AEI", aprobado=False)
    res = efectivos([], [horario_continuo()], complementos=[comp])
    assert res.confirmado_s == 0 and total(res, estado=PENDIENTE) == 9 * H


def test_complemento_que_coincide_con_checadas_no_duplica_tiempo():
    comp = Complemento("C-3", Intervalo(t(LUNES, 7), t(LUNES, 16)), "AEI", aprobado=True)
    res = efectivos([par(t(LUNES, 8), t(LUNES, 12))], [horario_continuo()], complementos=[comp])
    assert total(res) == 9 * H  # ningun segundo dos veces
    assert total(res, origen=CHECADA) == 4 * H and total(res, origen=COMPLEMENTO) == 5 * H


# --- Dias sin horario / no programado: P-33 -------------------------------------------------------------

def test_p33_sin_horario_el_resultado_es_provisional_con_al12_y_los_datos_se_conservan():
    res = efectivos([par(t(LUNES, 7), t(LUNES, 16))], [])
    assert res.provisional is True and AL12 in res.alertas and "horario_faltante" in res.motivos
    assert {p.ubicacion for p in res.piezas} == {SIN_HORARIO}
    assert total(res) == 9 * H


def test_dia_sin_programacion_todo_es_exceso_candidato_sin_ser_provisional():
    res = efectivos([par(t(DOMINGO, 8), t(DOMINGO, 12))], [horario_continuo()])
    assert {p.ubicacion for p in res.piezas} == {DIA_NO_PROGRAMADO}
    assert res.provisional is False and total(res) == 4 * H


# --- Multi-reloj, traslado, medianoche, determinismo -------------------------------------------------

def test_p45_dos_relojes_que_se_encimaron_cuentan_el_tiempo_una_sola_vez():
    a = par(t(LUNES, 7), t(LUNES, 12), reloj="R-AEI")
    b = par(t(LUNES, 11), t(LUNES, 16), empresa="CATAB", reloj="R-CATAB")
    res = efectivos([a, b], [horario_continuo()])
    assert total(res) == 9 * H


def test_traslado_entre_empresas_conserva_origen_y_se_atribuye_a_la_empresa_destino():
    traslado = par(t(LUNES, 12), t(LUNES, 12, 30), etiqueta=TRASLADO, empresa="AEI", empresa_hasta="CATAB")
    res = efectivos([par(t(LUNES, 7), t(LUNES, 12)), traslado], [horario_continuo()])
    pieza = next(p for p in res.piezas if p.origen == "traslado")
    assert pieza.intervalo.duracion == 30 * M and pieza.empresa == "CATAB"


def test_p26_turno_nocturno_se_separa_por_fecha_real_sin_duplicar_y_conserva_un_dia_logico():
    dia = DiaHorario((Intervalo(hs(22), hs(29)),))
    nocturno = Horario("HN", D2027, "nocturna", "America/Mexico_City", {0: dia}, empresa="AEI")
    res = efectivos([par(t(LUNES, 22), t(MARTES, 5))], [nocturno])
    assert {p.dia_logico for p in res.piezas} == {LUNES}
    assert {(p.fecha_real, p.intervalo.duracion) for p in res.piezas} == {(LUNES, 2 * H), (MARTES, 5 * H)}
    assert {p.ubicacion for p in res.piezas} == {DENTRO_HORARIO} and res.confirmado_s == 7 * H


def test_regreso_de_un_turno_nocturno_partido_pertenece_al_dia_logico_del_inicio():
    dia = DiaHorario((Intervalo(hs(22), hs(29)),))
    nocturno = Horario("HN", D2027, "nocturna", "America/Mexico_City", {0: dia}, empresa="AEI")
    res = efectivos([par(t(LUNES, 22), t(MARTES, 0, 30)), par(t(MARTES, 1), t(MARTES, 5))], [nocturno])
    assert {p.dia_logico for p in res.piezas} == {LUNES} and res.confirmado_s == 6 * H + 30 * M


def test_resultado_determinista_con_entradas_permutadas():
    pares = [
        par(t(LUNES, 6, 50), t(LUNES, 12)),
        par(t(LUNES, 13), t(LUNES, 16, 25), reloj="R-2"),
        par(t(LUNES, 11), t(LUNES, 11, 30), empresa="CATAB", reloj="R-C"),
    ]
    comps = [Complemento("C", Intervalo(t(LUNES, 17), t(LUNES, 18)), "AEI", aprobado=True)]
    base = efectivos(pares, [horario_partido()], complementos=comps)
    for semilla in range(5):
        barajado = pares[:]
        random.Random(semilla).shuffle(barajado)
        assert efectivos(barajado, [horario_partido()], complementos=comps) == base


def test_no_se_pierde_ni_se_duplica_tiempo_fisico():
    pares = [par(t(LUNES, 6, 50), t(LUNES, 12)), par(t(LUNES, 13), t(LUNES, 16, 25))]
    res = efectivos(pares, [horario_partido()])
    fisico = sum(p.intervalo.duracion for p in pares)
    assert total(res) == fisico
    ordenadas = sorted(res.piezas, key=lambda p: p.intervalo.inicio)
    assert all(a.intervalo.fin <= b.intervalo.inicio for a, b in zip(ordenadas, ordenadas[1:]))


# --- Correccion T3 ----------------------------------------------------------------------------

def test_i1_complemento_no_aprobado_dentro_de_descanso_computable_no_duplica_presencia():
    h = horario_continuo(DescansoHorario(Intervalo(hs(12), hs(13)), True, "art. 64"))
    comp = Complemento("C-9", Intervalo(t(LUNES, 12, 10), t(LUNES, 12, 20)), "AEI", aprobado=False)
    res = efectivos([par(t(LUNES, 7), t(LUNES, 12)), par(t(LUNES, 13), t(LUNES, 16))], [h], complementos=[comp])
    assert total(res) == 9 * H  # presencia 07:00-16:00, ni un segundo mas
    assert total(res, estado=PENDIENTE) == 10 * M
    assert total(res, origen=DESCANSO_COMPUTABLE) == 50 * M


def test_i1_propiedad_piezas_disjuntas_y_la_presencia_cuadra_con_semilla_fija():
    from Dominio.emparejamiento import tiempo_sin_traslape

    for semilla in range(400):
        rng = random.Random(semilla)
        bloques = [(7 * 60, 16 * 60)] if rng.random() < 0.5 else [(7 * 60, 12 * 60), (13 * 60, 17 * 60)]
        descansos = []
        for a, b in bloques:
            if rng.random() < 0.7:
                largo = rng.choice([15, 30, 45, 60])
                ini = rng.randrange(a + 15, b - largo - 14, 15)
                descansos.append(DescansoHorario(Intervalo(hs(0, ini), hs(0, ini + largo)), rng.random() < 0.5))
        dia = DiaHorario(tuple(Intervalo(hs(0, a), hs(0, b)) for a, b in bloques), tuple(descansos))
        horario = Horario("HR", D2027, "diurna", "America/Mexico_City", {0: dia}, empresa="AEI")

        def azar():
            ini = rng.randrange(6 * 60, 19 * 60, 5)
            return Intervalo(t(LUNES, 0, ini), t(LUNES, 0, ini + rng.randrange(10, 300, 5)))

        pares = [par(i.inicio, i.fin) for i in (azar() for _ in range(rng.randint(0, 3)))]
        comps = [Complemento(f"C{k}", azar(), "AEI", aprobado=rng.random() < 0.5) for k in range(rng.randint(0, 3))]
        res = efectivos(pares, [horario], complementos=comps)

        piezas = sorted(res.piezas, key=lambda p: p.intervalo.inicio)
        assert all(a.intervalo.fin <= b.intervalo.inicio for a, b in zip(piezas, piezas[1:])), semilla
        fuentes = [p.intervalo for p in pares] + [c.intervalo for c in comps]
        unidos = tiempo_sin_traslape(fuentes)
        relleno = total(res, origen=DESCANSO_COMPUTABLE)
        # presencia = tiempo fisico (union) + descanso computable incorporado (plan 5.4)
        assert total(res) == sum(i.duracion for i in unidos) + relleno, semilla
        assert all(
            any(u.inicio <= p.intervalo.inicio and p.intervalo.fin <= u.fin for u in unidos)
            for p in res.piezas
            if p.origen != DESCANSO_COMPUTABLE
        ), semilla


def test_i2_horarios_ambiguos_se_tratan_como_sin_horario_y_no_abortan():
    a = Horario("A", D2027, "diurna", "America/Mexico_City", {0: DiaHorario((Intervalo(hs(7), hs(16)),))})
    b = Horario("B", D2027, "diurna", "America/Mexico_City", {0: DiaHorario((Intervalo(hs(8), hs(17)),))})
    res = efectivos([par(t(LUNES, 7), t(LUNES, 16))], [a, b])
    assert res.provisional is True and AL12 in res.alertas and "horario_ambiguo" in res.motivos
    assert {p.ubicacion for p in res.piezas} == {SIN_HORARIO} and total(res) == 9 * H


def test_i2_tolerancia_almacenada_invalida_degrada_a_provisional_y_deja_lo_dudoso_pendiente():
    from Dominio.modelos import VersionParametro

    malas = tol(10)
    v = malas[1]
    malas[1] = VersionParametro(v.clave, 16 * M, v.vigencia, "x", v.origen, v.empresa)
    pares = [par(t(LUNES, 7), t(LUNES, 12)), par(t(LUNES, 13), t(LUNES, 16, 10))]
    res = efectivos(pares, [horario_partido()], versiones=malas)
    assert res.provisional is True and f"tolerancia_invalida:{CLAVES_TOLERANCIA[1]}" in res.motivos
    assert total(res) == 8 * H + 10 * M and total(res, estado=PENDIENTE) == 10 * M


def test_gap2_sin_tolerancias_configuradas_lo_que_esta_fuera_de_horario_queda_pendiente():
    pares = [par(t(LUNES, 7), t(LUNES, 12)), par(t(LUNES, 13), t(LUNES, 17))]
    res = efectivos(pares, [horario_partido()], versiones=())
    assert res.provisional is True and AL12 in res.alertas
    assert f"falta:{CLAVES_TOLERANCIA[0]}" in res.motivos
    assert total(res, ubicacion=FUERA_HORARIO, estado=PENDIENTE) == H
    assert total(res, ubicacion=FUERA_HORARIO, estado=CONFIRMADO) == 0
    assert total(res, ubicacion=DENTRO_HORARIO, estado=CONFIRMADO) == 8 * H
    conf = [Confirmacion(Intervalo(t(LUNES, 16), t(LUNES, 17)), True, "trabajo")]  # RH lo resuelve
    assert total(efectivos(pares, [horario_partido()], versiones=(), confirmaciones=conf), estado=PENDIENTE) == 0
