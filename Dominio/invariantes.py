# -*- coding: utf-8 -*-
"""Invariantes de calculo (plan 5.4, doc. 03 8.2 paso 14) como verificaciones puras sobre un resultado.

Devuelven las violaciones COMO DATOS (`Violacion`), sin lanzar en la operacion normal: quien compone el
motor (T7) decide si una violacion es un error de programacion visible. Nada aqui corrige ni recalcula.

Sobre `ResultadoExtra` (T5):
- ningun total negativo (por dia ni por categoria);
- ningun minuto duplicado: ni entre segmentos confirmados ni entre confirmado y no confirmado;
- categorias excluyentes: ordinario, doble, triple, pendiente art. 66 y la neutra
  `tiempo_pendiente_de_clasificar`; su suma por dia coincide con los segmentos y por tanto con el tiempo
  efectivo confirmado. Las etiquetas (exceso legal, domingo...) no se suman otra vez;
- todo pendiente lleva su motivo (no se declara cero lo desconocido) y motivos implican provisional;
- el aviso informativo del art. 61 existe si y solo si algun dia excede su tope, y nunca es alerta ni aviso
  con codigo: no cambia minutos;
- presencia = efectivo confirmado + no confirmado, cuando quien llama aporta la presencia reconstruida.

`verificar_equivalencia` es el gancho de independencia del orden y de reproducibilidad (mismos datos y
versiones -> mismo resultado); T7 lo aplica a permutaciones de la entrada.
"""

from dataclasses import dataclass

from Dominio.tramos_extra import (
    AVISO_INFO_TOPE_ART61_COMPENSADO,
    CAT_DOBLE,
    CAT_ORDINARIO,
    CAT_PENDIENTE,
    CAT_POR_CLASIFICAR,
    CAT_TRIPLE,
)

INV_TOTAL_NEGATIVO = "total_negativo"
INV_MINUTO_DUPLICADO = "minuto_duplicado"
INV_CATEGORIA_DESCONOCIDA = "categoria_desconocida"
INV_SUMA_DE_CATEGORIAS = "suma_de_categorias"
INV_PENDIENTE_SIN_MOTIVO = "pendiente_sin_motivo"
INV_PROVISIONAL = "provisional_inconsistente"
INV_AVISO_INFORMATIVO = "aviso_informativo"
INV_PRESENCIA = "presencia"
INV_ORDEN = "independencia_de_orden"

_CATEGORIAS = (CAT_ORDINARIO, CAT_DOBLE, CAT_TRIPLE, CAT_PENDIENTE, CAT_POR_CLASIFICAR)
_CAMPO_DE_DIA = {
    CAT_ORDINARIO: "ordinario_s", CAT_DOBLE: "doble_s", CAT_TRIPLE: "triple_s",
    CAT_PENDIENTE: "pendiente_s", CAT_POR_CLASIFICAR: "por_clasificar_s",
}


@dataclass(frozen=True)
class Violacion:
    codigo: str
    mensaje: str
    referencia: str = ""  # dia, categoria o indice al que se refiere


def _negativos(resultado) -> list[Violacion]:
    vs = []
    for d in resultado.dias:
        for campo in (*_CAMPO_DE_DIA.values(), "exceso_legal_s"):
            if getattr(d, campo) < 0:
                vs.append(Violacion(INV_TOTAL_NEGATIVO, f"{campo} negativo", d.dia_logico.isoformat()))
    return vs


def _duplicados(resultado) -> list[Violacion]:
    tramos = [(c.segmento.intervalo, "confirmado") for c in resultado.segmentos]
    tramos += [(s.intervalo, "no_confirmado") for s in resultado.no_confirmados]
    vs, fin_maximo = [], None
    for intervalo, origen in sorted(tramos, key=lambda t: (t[0].inicio, t[0].fin)):
        if intervalo.duracion and fin_maximo is not None and intervalo.inicio < fin_maximo:
            vs.append(Violacion(INV_MINUTO_DUPLICADO, f"{origen} traslapa tiempo ya contado", str(intervalo.inicio)))
        if intervalo.duracion:
            fin_maximo = intervalo.fin if fin_maximo is None else max(fin_maximo, intervalo.fin)
    return vs


def _categorias(resultado) -> list[Violacion]:
    vs, por_dia = [], {}
    for c in resultado.segmentos:
        if c.categoria not in _CATEGORIAS:
            vs.append(Violacion(INV_CATEGORIA_DESCONOCIDA, "categoria fuera de las excluyentes", c.categoria))
            continue
        acum = por_dia.setdefault(c.segmento.dia_logico, dict.fromkeys(_CATEGORIAS, 0))
        acum[c.categoria] += c.segmento.intervalo.duracion
    dias = {d.dia_logico: d for d in resultado.dias}
    for dia in sorted(set(por_dia) | set(dias)):
        esperado = por_dia.get(dia, dict.fromkeys(_CATEGORIAS, 0))
        resumen = dias.get(dia)
        if resumen is None or any(getattr(resumen, _CAMPO_DE_DIA[c]) != esperado[c] for c in _CATEGORIAS):
            vs.append(Violacion(INV_SUMA_DE_CATEGORIAS, "el resumen del dia no coincide con sus segmentos", dia.isoformat()))
        elif resumen.exceso_legal_s > resumen.total_s:
            vs.append(Violacion(INV_SUMA_DE_CATEGORIAS, "el exceso legal (etiqueta) supera el tiempo del dia", dia.isoformat()))
    return vs


def _pendientes(resultado) -> list[Violacion]:
    vs = [
        Violacion(INV_PENDIENTE_SIN_MOTIVO, "tiempo pendiente sin motivo explicito", str(c.segmento.intervalo.inicio))
        for c in resultado.segmentos if c.categoria in (CAT_PENDIENTE, CAT_POR_CLASIFICAR) and not c.motivo
    ]
    if resultado.motivos and not resultado.provisional:
        vs.append(Violacion(INV_PROVISIONAL, "hay motivos de cálculo pendiente pero el resultado no es provisional"))
    return vs


def _aviso_informativo(resultado) -> list[Violacion]:
    hay_exceso = any(d.excede_tope_art61 for d in resultado.dias)
    hay_aviso = AVISO_INFO_TOPE_ART61_COMPENSADO in resultado.avisos_informativos
    vs = []
    if hay_exceso != hay_aviso:
        vs.append(Violacion(INV_AVISO_INFORMATIVO, "el aviso art. 61 debe existir si y solo si algun dia excede su tope"))
    if AVISO_INFO_TOPE_ART61_COMPENSADO in resultado.avisos or AVISO_INFO_TOPE_ART61_COMPENSADO in resultado.alertas:
        vs.append(Violacion(INV_AVISO_INFORMATIVO, "el aviso informativo art. 61 no puede ser alerta ni aviso con codigo"))
    return vs


def verificar_invariantes(resultado, *, presencia_s: int | None = None) -> tuple[Violacion, ...]:
    """Violaciones de los invariantes del plan 5.4 en un `ResultadoExtra`; vacio si cumple todos.

    `presencia_s` (opcional) es la presencia reconstruida por los intervalos efectivos completos: debe
    ser igual al tiempo confirmado mas el no confirmado.
    """
    vs = _negativos(resultado) + _duplicados(resultado) + _categorias(resultado)
    vs += _pendientes(resultado) + _aviso_informativo(resultado)
    if presencia_s is not None:
        total = resultado.confirmado_s + sum(s.intervalo.duracion for s in resultado.no_confirmados)
        if total != presencia_s:
            vs.append(Violacion(INV_PRESENCIA, f"presencia {presencia_s} s != confirmado + no confirmado {total} s"))
    return tuple(vs)


def verificar_equivalencia(resultados) -> tuple[Violacion, ...]:
    """Cada resultado debe ser igual al primero (mismos datos y versiones, cualquier orden de llegada)."""
    resultados = list(resultados)
    return tuple(
        Violacion(INV_ORDEN, "el resultado difiere del primero", str(i))
        for i, r in enumerate(resultados[1:], start=1) if r != resultados[0]
    )
