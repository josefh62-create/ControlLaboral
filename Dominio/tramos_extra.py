# -*- coding: utf-8 -*-
"""Tramos de extra: doble / triple, limites art. 66 y 68, exceso legal y pendiente de clasificacion
(doc. 03 8.2 paso 11; plan 5.3 y 4.4).

Entrada: la `AsignacionSemana` de un criterio (que ya dijo CUANTO y DONDE es extra). Aqui se reparte la
extra, en orden cronologico:
- doble hasta el tope art. 66 semanal vigente; el resto, triple. Un segmento que cruza el umbral se
  divide exactamente. Mas alla del tramo adicional art. 68 (4 h/semana) el tiempo SIGUE siendo triple, con
  la etiqueta `exceso_legal`: no hay una cuarta categoria de pago ni se recorta el computo;
- distribucion art. 66: 4 h por dia y maximo 4 dias por semana. Lo que cae fuera NO se declara legal ni se
  oculta: queda `extra_pendiente_clasificacion` (propuesta del doc. 03 8.2-11, por validar con el asesor
  laboral; el plan 5.3 pide revision juridica sin fijar la categoria). Esos minutos no consumen el tope
  doble: no se sabe si la ley los trata como art. 66 o como excedente;
- total por dia art. 68: ordinario + extra por jornada logica; lo que pasa del limite lleva
  `exceso_legal` (tiempo integro, alerta independiente);
- cada limite se evalua por separado y produce su propio aviso/alerta (NL06).

Todo valor sale de `resolver_vigente` en la fecha trabajada del segmento (P-36, P-40): nada legal vive
aqui. Un parametro faltante o ambiguo nunca lanza: la parte afectada queda pendiente o sin evaluar y el
resultado `provisional` con AL12 (los avisos de limites cuyo valor falta simplemente no se emiten).

La autorizacion de la extra (RE03, P-38) es un atributo independiente: se etiqueta y jamas quita tiempo.
El tope art. 61 DIARIO se lee del tipo declarado por el horario (`JornadaClasificada.tipo_efectivo`),
nunca del tiempo trabajado (decision Q-B, 27/11/2026); solo se informa por dia, no reclasifica.
"""

from dataclasses import dataclass, replace
from datetime import date

from Dominio import normatividad as n
from Dominio.calendario import AL12
from Dominio.criterios_extra import EXTRA, ORDINARIO, PENDIENTE, AsignacionSemana
from Dominio.horarios import _ERRORES_DE_CONFIGURACION, _motivo_de
from Dominio.modelos import ORIGEN_PATRONAL, Vigencia
from Dominio.normatividad import ALERTA_POR_LIMITE, FaltaParametro, resolver_vigente
from Dominio.regimenes import REGIMENES, tope_diario_s
from Dominio.segmentacion import Segmento
from Dominio.tiempo import Intervalo

# Categorias excluyentes del tiempo confirmado (plan 5.4).
CAT_ORDINARIO = "ordinario"
CAT_DOBLE = "extra_doble"
CAT_TRIPLE = "extra_triple"
CAT_PENDIENTE = "extra_pendiente_clasificacion"

# Etiquetas adicionales (no se suman otra vez, plan 5.4).
ETQ_EXCESO_LEGAL = "exceso_legal"
ETQ_FUERA_DISTRIBUCION = "fuera_distribucion_art66"

MOTIVO_FUERA_DIAS = "fuera_distribucion_art66:dias"
MOTIVO_FUERA_DIARIO = "fuera_distribucion_art66:diario"

# Autorizacion de la extra (RE03): atributo independiente del tiempo.
AUT_AUTORIZADA = "autorizada"
AUT_NO_AUTORIZADA = "no_autorizada"
AUT_SIN_REGISTRO = "sin_registro"

# Avisos por limite (una cosa es alcanzar y otra superar) y su alerta del plan 4.4.
AVISO_ART66_PREVENTIVO = "art66_preventivo"
AVISO_ART66_ALCANZADO = "art66_alcanzado"
AVISO_ART66_SUPERADO = "art66_superado"
AVISO_ART68_ALCANZADO = "art68_alcanzado"
AVISO_ART68_SUPERADO = "art68_superado"
AVISO_DISTRIBUCION_DIARIA = "distribucion_art66_diaria"
AVISO_DISTRIBUCION_DIAS = "distribucion_art66_dias"
AVISO_TOTAL_DIARIO_ALCANZADO = "total_diario_alcanzado"
AVISO_TOTAL_DIARIO_SUPERADO = "total_diario_superado"

AL02 = "AL02"  # tiempo extraordinario detectado (informativo/revision)
AL03 = "AL03"  # proximo al tope art. 66 semanal (preventivo)


@dataclass(frozen=True)
class Autorizacion:
    """Autorizacion (o negativa) de RH/direccion para trabajar un intervalo extra. Nunca quita tiempo."""

    intervalo: Intervalo  # segundos de epoch
    autorizada: bool


@dataclass(frozen=True)
class SegmentoClasificado:
    segmento: Segmento
    categoria: str
    etiquetas: frozenset[str] = frozenset()
    autorizacion: str | None = None  # solo la extra lleva etiqueta de autorizacion
    motivo: str | None = None  # por que quedo pendiente de clasificacion


@dataclass(frozen=True)
class DiaExtra:
    """Resumen de una jornada logica. `tope_art61_s` sale del tipo declarado (None: sin tipo o sin tope propio)."""

    dia_logico: date
    tipo_efectivo: str | None
    tope_art61_s: int | None
    ordinario_s: int
    doble_s: int
    triple_s: int
    pendiente_s: int
    exceso_legal_s: int
    excede_tope_art61: bool

    @property
    def total_s(self) -> int:
        return self.ordinario_s + self.doble_s + self.triple_s + self.pendiente_s


@dataclass(frozen=True)
class ResultadoExtra:
    semana: Vigencia | None
    criterio: str
    segmentos: tuple[SegmentoClasificado, ...]  # solo tiempo confirmado, cronologico
    no_confirmados: tuple[Segmento, ...]
    dias: tuple[DiaExtra, ...]
    provisional: bool = False
    alertas: tuple[str, ...] = ()
    avisos: frozenset[str] = frozenset()
    motivos: tuple[str, ...] = ()

    def total_s(self, categoria: str) -> int:
        return sum(c.segmento.intervalo.duracion for c in self.segmentos if c.categoria == categoria)

    @property
    def confirmado_s(self) -> int:
        return sum(c.segmento.intervalo.duracion for c in self.segmentos)

    @property
    def extra_s(self) -> int:
        return self.total_s(CAT_DOBLE) + self.total_s(CAT_TRIPLE) + self.total_s(CAT_PENDIENTE)


@dataclass(frozen=True)
class _Trozo:
    segmento: Segmento
    base: str  # ORDINARIO | EXTRA | PENDIENTE (lo que dijo el criterio)
    motivo: str | None = None
    autorizacion: str | None = None
    etiquetas: frozenset[str] = frozenset()


class _Topes:
    """Versiones vigentes por fecha trabajada; lo que falta o es ambiguo se vuelve motivo, nunca excepcion."""

    def __init__(self, versiones, motivos: set[str]):
        self._versiones, self._motivos, self._cache = versiones, motivos, {}

    def _resolver(self, clave: str, fecha):
        if (clave, fecha) not in self._cache:
            try:
                self._cache[(clave, fecha)] = (resolver_vigente(self._versiones, clave, fecha).valor, None)
            except _ERRORES_DE_CONFIGURACION as error:
                self._cache[(clave, fecha)] = (None, _motivo_de(error))
        valor, motivo = self._cache[(clave, fecha)]
        if motivo:
            self._motivos.add(motivo)
        return valor, motivo

    def valor(self, clave: str, fecha) -> int | None:
        return self._resolver(clave, fecha)[0]

    def motivo(self, clave: str, fecha) -> str | None:
        return self._resolver(clave, fecha)[1]


def _orden(trozo: _Trozo):
    return (trozo.segmento.intervalo.inicio, trozo.segmento.intervalo.fin)


def _cortar(trozo: _Trozo, instantes) -> list[_Trozo]:
    """Divide exactamente el trozo en cada instante interior; ningun segundo se pierde ni se repite."""
    seg = trozo.segmento
    puntos = [seg.intervalo.inicio, *sorted({x for x in instantes if seg.intervalo.inicio < x < seg.intervalo.fin}), seg.intervalo.fin]
    return [replace(trozo, segmento=replace(seg, intervalo=Intervalo(a, b))) for a, b in zip(puntos, puntos[1:])]


def _etiquetar_autorizacion(trozos: list[_Trozo], autorizaciones) -> list[_Trozo]:
    cortes = sorted({x for a in autorizaciones for x in (a.intervalo.inicio, a.intervalo.fin)})
    resultado = []
    for trozo in trozos:
        if trozo.base != EXTRA:
            resultado.append(trozo)
            continue
        for parte in _cortar(trozo, cortes):
            inicio = parte.segmento.intervalo.inicio
            cubren = [a for a in autorizaciones if a.intervalo.contiene(inicio)]
            if not cubren:
                etiqueta = AUT_SIN_REGISTRO
            else:
                etiqueta = AUT_NO_AUTORIZADA if any(not a.autorizada for a in cubren) else AUT_AUTORIZADA
            resultado.append(replace(parte, autorizacion=etiqueta))
    return resultado


def _limite_total_diario(trozos: list[_Trozo], topes: _Topes, avisos: set[str]) -> list[_Trozo]:
    """Marca `exceso_legal` en lo que rebasa 12 h (art. 68) dentro de la jornada logica; sin perder tiempo."""
    por_dia: dict = {}
    for trozo in trozos:
        por_dia.setdefault(trozo.segmento.dia_logico, []).append(trozo)
    salida = []
    for dia in sorted(por_dia):
        acumulado, limite_final = 0, None
        for trozo in sorted(por_dia[dia], key=_orden):
            duracion = trozo.segmento.intervalo.duracion
            limite = topes.valor(n.TOTAL_DIARIO_MAX_S, trozo.segmento.fecha_real)
            if limite is None or acumulado + duracion <= limite:
                salida.append(trozo)
            else:
                corte = trozo.segmento.intervalo.inicio + limite - acumulado  # <= inicio: todo el trozo ya pasa del limite
                for parte in _cortar(trozo, [corte]):
                    pasado = parte.segmento.intervalo.inicio >= corte
                    salida.append(replace(parte, etiquetas=parte.etiquetas | {ETQ_EXCESO_LEGAL}) if pasado else parte)
            if limite is not None:
                limite_final = limite
            acumulado += duracion
        if limite_final is not None and acumulado >= limite_final:
            avisos.add(AVISO_TOTAL_DIARIO_ALCANZADO if acumulado == limite_final else AVISO_TOTAL_DIARIO_SUPERADO)
    return salida


def _clasificado(trozo: _Trozo, inicio: int, fin: int, categoria: str, motivo=None, etiquetas=()) -> SegmentoClasificado:
    return SegmentoClasificado(
        replace(trozo.segmento, intervalo=Intervalo(inicio, fin)), categoria,
        trozo.etiquetas | frozenset(etiquetas), trozo.autorizacion, motivo,
    )


def _repartir(trozos: list[_Trozo], topes: _Topes, avisos: set[str]) -> list[SegmentoClasificado]:
    uso_dia: dict = {}  # dia logico -> segundos art. 66 validos; sus claves son los dias con extra art. 66
    acumulado_doble = acumulado_triple = 0
    salida: list[SegmentoClasificado] = []
    for trozo in sorted(trozos, key=_orden):
        seg = trozo.segmento
        inicio, fin = seg.intervalo.inicio, seg.intervalo.fin
        if trozo.base != EXTRA:
            categoria = CAT_ORDINARIO if trozo.base == ORDINARIO else CAT_PENDIENTE
            salida.append(_clasificado(trozo, inicio, fin, categoria, trozo.motivo))
            continue
        fecha, dia = seg.fecha_real, seg.dia_logico
        while inicio < fin:
            claves = (n.ART66_DIARIO_S, n.ART66_DIAS_SEMANA, n.ART66_SEMANAL_S)
            valores = [topes.valor(c, fecha) for c in claves]
            if None in valores:  # sin distribucion o sin tope no se inventa el corte: pendiente
                faltante = claves[valores.index(None)]
                salida.append(_clasificado(trozo, inicio, fin, CAT_PENDIENTE, topes.motivo(faltante, fecha)))
                break
            limite_dia, limite_dias, tope_66 = valores
            if dia not in uso_dia and len(uso_dia) >= limite_dias:
                avisos.add(AVISO_DISTRIBUCION_DIAS)
                salida.append(_clasificado(trozo, inicio, fin, CAT_PENDIENTE, MOTIVO_FUERA_DIAS, (ETQ_FUERA_DISTRIBUCION,)))
                break
            cupo = limite_dia - uso_dia.get(dia, 0)
            if cupo <= 0:
                avisos.add(AVISO_DISTRIBUCION_DIARIA)
                salida.append(_clasificado(trozo, inicio, fin, CAT_PENDIENTE, MOTIVO_FUERA_DIARIO, (ETQ_FUERA_DISTRIBUCION,)))
                break
            toma = min(fin - inicio, cupo)
            uso_dia[dia] = uso_dia.get(dia, 0) + toma
            doble = max(0, min(toma, tope_66 - acumulado_doble))
            triple = toma - doble
            acumulado_doble += doble  # el triple solo empieza cuando el doble ya llego al tope
            if doble:
                salida.append(_clasificado(trozo, inicio, inicio + doble, CAT_DOBLE))
            if triple:
                tope_68 = topes.valor(n.ART68_SEMANAL_S, fecha)
                legal = triple if tope_68 is None else max(0, min(triple, tope_68 - acumulado_triple))
                if legal:
                    salida.append(_clasificado(trozo, inicio + doble, inicio + doble + legal, CAT_TRIPLE))
                if triple > legal:
                    salida.append(_clasificado(trozo, inicio + doble + legal, inicio + toma, CAT_TRIPLE, None, (ETQ_EXCESO_LEGAL,)))
                acumulado_triple += triple
            inicio += toma
    return salida


def _anticipacion_s(versiones, fecha, empresa, motivos: set[str]) -> int | None:
    """Anticipacion preventiva patronal (opcional): sin ella simplemente no hay aviso preventivo."""
    try:
        return resolver_vigente(versiones, n.ANTICIPACION_PREVENTIVA_S, fecha, ORIGEN_PATRONAL, empresa).valor
    except FaltaParametro:
        return None
    except _ERRORES_DE_CONFIGURACION as error:
        motivos.add(_motivo_de(error))
        return None


def _avisos_semanales(trozos, clasificados, topes, versiones, empresa, avisos: set[str], alertas: set[str], motivos):
    extras = [t for t in sorted(trozos, key=_orden) if t.base == EXTRA]
    if not extras:
        return
    alertas.add(AL02)
    fecha = extras[-1].segmento.fecha_real  # los topes semanales se leen en la fecha de la ultima extra de la semana
    total_extra = sum(t.segmento.intervalo.duracion for t in extras)
    tope_66 = topes.valor(n.ART66_SEMANAL_S, fecha)
    if tope_66 is not None:
        anticipacion = _anticipacion_s(versiones, fecha, empresa, motivos)
        if total_extra > tope_66:
            avisos.add(AVISO_ART66_SUPERADO)
        elif total_extra == tope_66:
            avisos.add(AVISO_ART66_ALCANZADO)
        elif anticipacion is not None and total_extra >= tope_66 - anticipacion:
            avisos.add(AVISO_ART66_PREVENTIVO)
    tope_68 = topes.valor(n.ART68_SEMANAL_S, fecha)
    triple = sum(c.segmento.intervalo.duracion for c in clasificados if c.categoria == CAT_TRIPLE)
    if tope_68 is not None and triple >= tope_68 > 0:
        avisos.add(AVISO_ART68_SUPERADO if triple > tope_68 else AVISO_ART68_ALCANZADO)


_ALERTA_DE_AVISO = {
    AVISO_ART66_PREVENTIVO: AL03,
    AVISO_ART66_ALCANZADO: ALERTA_POR_LIMITE[n.ART66_SEMANAL_S],
    AVISO_ART66_SUPERADO: ALERTA_POR_LIMITE[n.ART66_SEMANAL_S],
    AVISO_ART68_ALCANZADO: ALERTA_POR_LIMITE[n.ART68_SEMANAL_S],
    AVISO_ART68_SUPERADO: ALERTA_POR_LIMITE[n.ART68_SEMANAL_S],
    AVISO_DISTRIBUCION_DIARIA: ALERTA_POR_LIMITE[n.ART66_DIARIO_S],
    AVISO_DISTRIBUCION_DIAS: ALERTA_POR_LIMITE[n.ART66_DIAS_SEMANA],
    AVISO_TOTAL_DIARIO_ALCANZADO: ALERTA_POR_LIMITE[n.TOTAL_DIARIO_MAX_S],
    AVISO_TOTAL_DIARIO_SUPERADO: ALERTA_POR_LIMITE[n.TOTAL_DIARIO_MAX_S],
}


def _resumen_por_dia(clasificados, jornadas, versiones, motivos: set[str]) -> tuple[DiaExtra, ...]:
    por_dia: dict = {}
    for c in clasificados:
        por_dia.setdefault(c.segmento.dia_logico, []).append(c)
    tipos = {j.dia_logico: j.tipo_efectivo for j in jornadas}
    dias = []
    for dia in sorted(por_dia):
        def suma(categoria):
            return sum(c.segmento.intervalo.duracion for c in por_dia[dia] if c.categoria == categoria)

        tipo = tipos.get(dia)
        tope = None
        if tipo in REGIMENES:  # sin tipo declarado no se infiere nada del tiempo trabajado
            try:
                tope = tope_diario_s(REGIMENES[tipo], versiones, dia)
            except _ERRORES_DE_CONFIGURACION as error:
                motivos.add(_motivo_de(error))
        ordinario = suma(CAT_ORDINARIO)
        legal = sum(c.segmento.intervalo.duracion for c in por_dia[dia] if ETQ_EXCESO_LEGAL in c.etiquetas)
        dias.append(DiaExtra(
            dia, tipo, tope, ordinario, suma(CAT_DOBLE), suma(CAT_TRIPLE), suma(CAT_PENDIENTE), legal,
            tope is not None and ordinario > tope,
        ))
    return tuple(dias)


def repartir_tramos(
    asignacion: AsignacionSemana, versiones, autorizaciones=(), *, empresa: str | None = None
) -> ResultadoExtra:
    """Reparte la extra de una semana en doble / triple / pendiente y evalua los limites legales por separado."""
    motivos = set(asignacion.motivos)
    topes = _Topes(versiones, motivos)
    avisos: set[str] = set()
    trozos = [_Trozo(p.segmento, p.tipo, p.motivo) for p in asignacion.piezas]
    trozos = _etiquetar_autorizacion(trozos, tuple(autorizaciones))
    trozos = _limite_total_diario(trozos, topes, avisos)
    clasificados = _repartir(trozos, topes, avisos)
    alertas = set(asignacion.alertas)
    _avisos_semanales(trozos, clasificados, topes, versiones, empresa, avisos, alertas, motivos)
    dias = _resumen_por_dia(clasificados, asignacion.jornadas, versiones, motivos)
    alertas |= {_ALERTA_DE_AVISO[a] for a in avisos}
    if motivos:
        alertas.add(AL12)
    return ResultadoExtra(
        asignacion.semana, asignacion.criterio, tuple(clasificados), asignacion.no_confirmados, dias,
        asignacion.provisional or bool(motivos), tuple(sorted(alertas)), frozenset(avisos), tuple(sorted(motivos)),
    )
