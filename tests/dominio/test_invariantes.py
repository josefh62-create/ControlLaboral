"""Invariantes de calculo del plan 5.4 sobre el resultado de T5, devueltos como datos (nunca excepciones en
la operacion normal): sin totales negativos, sin minutos duplicados, la suma de categorias excluyentes
(ordinario, doble, triple, pendiente art. 66 y la categoria neutra `tiempo_pendiente_de_clasificar`) es el
tiempo efectivo confirmado, pendientes explicitos, el aviso informativo del art. 61 no cambia minutos ni
es alerta, y presencia = efectivo + no confirmado. Incluye el gancho de independencia del orden."""
import random
from dataclasses import replace

from Dominio import normatividad as n
from Dominio.criterios_extra import asignar_extra
from Dominio.invariantes import (
    INV_AVISO_INFORMATIVO,
    INV_CATEGORIA_DESCONOCIDA,
    INV_MINUTO_DUPLICADO,
    INV_ORDEN,
    INV_PENDIENTE_SIN_MOTIVO,
    INV_PRESENCIA,
    INV_PROVISIONAL,
    INV_SUMA_DE_CATEGORIAS,
    INV_TOTAL_NEGATIVO,
    Violacion,
    verificar_equivalencia,
    verificar_invariantes,
)
from Dominio.tiempo import Intervalo
from Dominio.tramos_extra import (
    AVISO_INFO_TOPE_ART61_COMPENSADO,
    CAT_DOBLE,
    CAT_ORDINARIO,
    CAT_PENDIENTE,
    CAT_POR_CLASIFICAR,
    CAT_TRIPLE,
    repartir_tramos,
)
from _semanas_extra import BASE, H, LUN_2027, M, PROGRAMA_46, segmentar_semana


def clasificar(trabajado, versiones=BASE, programa=None):
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


def codigos(violaciones):
    return {v.codigo for v in violaciones}


def con_pendiente_art66():
    # P-16: 1 h extra de lunes a viernes; el quinto dia queda fuera de la distribucion art. 66.
    return clasificar({d: [(8, 17)] for d in range(5)} | {5: [(8, 14)]})


PROGRAMA_LUNES_LARGO = {0: [(8, 18)], 1: [(8, 16)], 2: [(8, 16)], 3: [(8, 16)], 4: [(8, 14)], 5: [(8, 14)]}  # 46 h


def con_exceso_art61(versiones=BASE):
    # Lunes ordinario de 10 h sobre un tope diurno de 8 h, compensado en la semana (Q-H).
    return clasificar({d: list(p) for d, p in PROGRAMA_LUNES_LARGO.items()}, versiones, PROGRAMA_LUNES_LARGO)


def con_categoria_neutra():
    sin_tope = tuple(v for v in BASE if v.clave != n.ART66_SEMANAL_S)
    res = clasificar(con_extras(lun=4), versiones=sin_tope)
    assert res.por_clasificar_s > 0
    return res


SEMANAS = {
    "sin_extra": lambda: clasificar({d: list(p) for d, p in PROGRAMA_46.items()}),
    "doble_y_triple": lambda: clasificar(con_extras(lun=3, mar=3, mie=(3, 1))),
    "art68_superado": lambda: clasificar(con_extras(lun=4, mar=4, mie=4, jue=(1, 1))),
    "pendiente_art66": con_pendiente_art66,
    "categoria_neutra": con_categoria_neutra,
    "exceso_art61": con_exceso_art61,
}


# --- Resultados reales: ninguna violacion ------------------------------------------------------------------

def test_los_resultados_reales_de_t5_cumplen_todos_los_invariantes():
    for nombre, construir in SEMANAS.items():
        assert verificar_invariantes(construir()) == (), nombre


def test_la_categoria_neutra_forma_parte_del_tiempo_efectivo():
    res = con_categoria_neutra()
    assert res.por_clasificar_s > 0 and res.extra_s == 0  # lo neutro no es extra
    assert verificar_invariantes(res) == ()
    sin_neutro = replace(res, dias=tuple(replace(d, por_clasificar_s=0) for d in res.dias))
    assert INV_SUMA_DE_CATEGORIAS in codigos(verificar_invariantes(sin_neutro))


def _semana_al_azar(rng):
    trabajado = {}
    for d in range(7):
        if rng.random() < 0.75:
            cursor, partes = rng.randint(5, 8), []
            for _ in range(rng.randint(1, 2)):
                duracion = rng.randint(2, 6)
                partes.append((cursor, cursor + duracion))
                cursor += duracion + rng.randint(1, 2)
            trabajado[d] = partes
    return trabajado


def test_propiedad_semanas_al_azar_con_semillas_fijas_no_violan_invariantes():
    for semilla in range(200):
        rng = random.Random(semilla)
        trabajado = _semana_al_azar(rng)
        if not trabajado:
            continue
        res = clasificar(trabajado)
        assert verificar_invariantes(res) == (), (semilla, trabajado)


# --- Cada invariante detecta su violacion ---------------------------------------------------------------------

def test_total_negativo_se_reporta_como_dato():
    res = SEMANAS["doble_y_triple"]()
    roto = replace(res, dias=(replace(res.dias[0], doble_s=-1),) + res.dias[1:])
    vs = verificar_invariantes(roto)
    assert INV_TOTAL_NEGATIVO in codigos(vs) and all(isinstance(v, Violacion) for v in vs)


def test_minuto_duplicado_entre_segmentos_confirmados():
    res = SEMANAS["doble_y_triple"]()
    roto = replace(res, segmentos=res.segmentos + (res.segmentos[0],))
    assert INV_MINUTO_DUPLICADO in codigos(verificar_invariantes(roto))


def test_minuto_duplicado_entre_confirmado_y_no_confirmado():
    res = SEMANAS["doble_y_triple"]()
    roto = replace(res, no_confirmados=res.no_confirmados + (res.segmentos[0].segmento,))
    assert INV_MINUTO_DUPLICADO in codigos(verificar_invariantes(roto))


def test_segmentos_contiguos_no_son_minuto_duplicado():
    res = SEMANAS["doble_y_triple"]()
    assert INV_MINUTO_DUPLICADO not in codigos(verificar_invariantes(res))


def test_categoria_desconocida_no_se_suma_en_silencio():
    res = SEMANAS["doble_y_triple"]()
    roto = replace(res, segmentos=(replace(res.segmentos[0], categoria="otra"),) + res.segmentos[1:])
    assert INV_CATEGORIA_DESCONOCIDA in codigos(verificar_invariantes(roto))


def test_la_suma_por_dia_debe_coincidir_con_los_segmentos():
    res = SEMANAS["doble_y_triple"]()
    roto = replace(res, dias=(replace(res.dias[0], ordinario_s=res.dias[0].ordinario_s + 1),) + res.dias[1:])
    assert INV_SUMA_DE_CATEGORIAS in codigos(verificar_invariantes(roto))


def test_el_exceso_legal_es_etiqueta_no_puede_superar_el_tiempo_del_dia():
    res = SEMANAS["doble_y_triple"]()
    dia = res.dias[0]
    roto = replace(res, dias=(replace(dia, exceso_legal_s=dia.total_s + 1),) + res.dias[1:])
    assert INV_SUMA_DE_CATEGORIAS in codigos(verificar_invariantes(roto))


def test_pendiente_sin_motivo_viola_la_regla_de_pendientes_explicitos():
    res = SEMANAS["pendiente_art66"]()
    segmentos = tuple(replace(c, motivo=None) if c.categoria == CAT_PENDIENTE else c for c in res.segmentos)
    assert INV_PENDIENTE_SIN_MOTIVO in codigos(verificar_invariantes(replace(res, segmentos=segmentos)))
    neutro = SEMANAS["categoria_neutra"]()
    segmentos = tuple(replace(c, motivo=None) if c.categoria == CAT_POR_CLASIFICAR else c for c in neutro.segmentos)
    assert INV_PENDIENTE_SIN_MOTIVO in codigos(verificar_invariantes(replace(neutro, segmentos=segmentos)))


def test_motivos_sin_provisional_es_inconsistente():
    res = SEMANAS["categoria_neutra"]()
    assert res.motivos and res.provisional
    assert INV_PROVISIONAL in codigos(verificar_invariantes(replace(res, provisional=False)))


# --- Aviso informativo del art. 61 --------------------------------------------------------------------------------

def test_aviso_art61_no_cambia_los_minutos_ni_es_alerta():
    con_aviso = SEMANAS["exceso_art61"]()
    assert AVISO_INFO_TOPE_ART61_COMPENSADO in con_aviso.avisos_informativos
    assert AVISO_INFO_TOPE_ART61_COMPENSADO not in con_aviso.avisos | set(con_aviso.alertas)
    sin_tope = tuple(v for v in BASE if v.clave != n.JORNADA_DIURNA_S)
    sin_aviso = con_exceso_art61(sin_tope)  # sin tope art. 61 no hay aviso
    assert AVISO_INFO_TOPE_ART61_COMPENSADO not in sin_aviso.avisos_informativos
    def minutos(r):
        return tuple(r.total_s(c) for c in (CAT_ORDINARIO, CAT_DOBLE, CAT_TRIPLE, CAT_PENDIENTE, CAT_POR_CLASIFICAR))
    assert minutos(con_aviso) == minutos(sin_aviso)


def test_aviso_informativo_presente_sin_dia_excedido_o_ausente_con_dia_excedido_se_reporta():
    con_aviso = SEMANAS["exceso_art61"]()
    sin_notificar = replace(con_aviso, avisos_informativos=frozenset())
    assert INV_AVISO_INFORMATIVO in codigos(verificar_invariantes(sin_notificar))
    limpia = SEMANAS["sin_extra"]()
    notificada = replace(limpia, avisos_informativos=frozenset({AVISO_INFO_TOPE_ART61_COMPENSADO}))
    assert INV_AVISO_INFORMATIVO in codigos(verificar_invariantes(notificada))


def test_aviso_informativo_que_se_cuela_como_alerta_o_aviso_se_reporta():
    res = SEMANAS["exceso_art61"]()
    como_alerta = replace(res, alertas=res.alertas + (AVISO_INFO_TOPE_ART61_COMPENSADO,))
    como_aviso = replace(res, avisos=res.avisos | {AVISO_INFO_TOPE_ART61_COMPENSADO})
    assert INV_AVISO_INFORMATIVO in codigos(verificar_invariantes(como_alerta))
    assert INV_AVISO_INFORMATIVO in codigos(verificar_invariantes(como_aviso))


# --- Presencia = efectivo + no confirmado --------------------------------------------------------------------------

def test_presencia_es_efectivo_mas_no_confirmado_con_intervalos_completos():
    res = SEMANAS["doble_y_triple"]()
    no_confirmado = sum(s.intervalo.duracion for s in res.no_confirmados)
    presencia = res.confirmado_s + no_confirmado
    assert verificar_invariantes(res, presencia_s=presencia) == ()
    assert INV_PRESENCIA in codigos(verificar_invariantes(res, presencia_s=presencia + M))


def test_si_falta_tiempo_pendiente_no_se_declara_cero_y_se_conserva_en_la_presencia():
    # Entrada sin tolerancia que deja minutos fuera de horario como pendientes: presencia = efectivo + pendiente.
    seg, vers = segmentar_semana(LUN_2027, {0: [(7, 17)]}, tolerancia=0)
    res = repartir_tramos(asignar_extra(seg, vers)[0], vers)
    presencia = sum(s.intervalo.duracion for s in seg.segmentos)
    assert verificar_invariantes(res, presencia_s=presencia) == ()


# --- Independencia del orden (gancho para T7) -------------------------------------------------------------------------

def test_resultados_equivalentes_no_violan_independencia_de_orden():
    a, b = SEMANAS["doble_y_triple"](), SEMANAS["doble_y_triple"]()
    assert verificar_equivalencia([a, b]) == () and verificar_equivalencia([a]) == ()


def test_resultados_distintos_ante_el_mismo_conjunto_se_reportan():
    a, b = SEMANAS["doble_y_triple"](), SEMANAS["art68_superado"]()
    vs = verificar_equivalencia([a, b, a])
    assert codigos(vs) == {INV_ORDEN} and [v.referencia for v in vs] == ["1"]


def test_un_solo_segundo_de_traslape_ya_es_minuto_duplicado():
    res = SEMANAS["doble_y_triple"]()
    primero = res.segmentos[0]
    inicio = primero.segmento.intervalo.fin - 1
    intruso = replace(primero, segmento=replace(primero.segmento, intervalo=Intervalo(inicio, inicio + 5)))
    roto = replace(res, segmentos=(primero, intruso), no_confirmados=())
    assert INV_MINUTO_DUPLICADO in codigos(verificar_invariantes(roto))


def test_un_segmento_contenido_dentro_de_otro_mas_largo_tambien_se_detecta():
    res = SEMANAS["sin_extra"]()
    grande = max(res.segmentos, key=lambda c: c.segmento.intervalo.duracion)
    i = grande.segmento.intervalo
    dentro = replace(grande, segmento=replace(grande.segmento, intervalo=Intervalo(i.inicio + 60, i.inicio + 120)))
    despues = replace(grande, segmento=replace(grande.segmento, intervalo=Intervalo(i.fin - 30, i.fin - 10)))
    # `despues` traslapa al grande pero no a `dentro`: el maximo corriente debe seguir siendo el fin del grande
    roto = replace(res, segmentos=(grande, dentro, despues), no_confirmados=())
    ref = [v.referencia for v in verificar_invariantes(roto) if v.codigo == INV_MINUTO_DUPLICADO]
    assert str(i.inicio + 60) in ref and str(i.fin - 30) in ref


def test_presencia_menor_al_total_tambien_se_reporta():
    res = SEMANAS["doble_y_triple"]()
    total = res.confirmado_s + sum(s.intervalo.duracion for s in res.no_confirmados)
    assert INV_PRESENCIA in codigos(verificar_invariantes(res, presencia_s=total - 1))
