# -*- coding: utf-8 -*-
"""Alertas del motor (plan 4.4, doc. 03 8.2 paso 12): catalogo unico AL01-AL14, tipo comun y
clave de deduplicacion (P-48, parte pura).

- El catalogo es la unica fuente de codigo, nombre, nivel (texto literal del plan), severidades
  posibles y bloqueo de cierre. Los modulos de T1-T5 solo conservan el codigo (`"AL12"`...).
- `Alerta` es el valor comun. Su identidad (clave de deduplicacion) es trabajador + empresa + periodo
  + dia logico + regla + sujeto + version: reimportar o recalcular los mismos datos con las mismas
  versiones da la misma clave y no genera otro aviso. Severidad y detalle NO forman parte de la
  identidad (una alerta que escala conserva su clave; el `sujeto` distingue alcanzado vs superado).
- Nada aqui calcula minutos: solo describe, normaliza y deduplica lo que ya produjeron T2-T5.
- Persistencia, reconocimiento y destinatarios son de E3/E4; aqui no hay E/S.
"""

import json
from dataclasses import dataclass
from datetime import date, timedelta

from Dominio import normatividad as n
from Dominio.checadas import CERCANA_SIN_RESOLVER, DESFASE, FUTURA, POSIBLE_DUPLICADO
from Dominio.horarios import _ERRORES_DE_CONFIGURACION, _motivo_de
from Dominio.modelos import Vigencia
from Dominio.normatividad import resolver_vigente
from Dominio.tramos_extra import (
    ALERTA_DE_AVISO,
    AVISO_ART66_ALCANZADO,
    AVISO_ART66_PREVENTIVO,
    AVISO_ART66_SUPERADO,
    AVISO_ART68_ALCANZADO,
    AVISO_ART68_SUPERADO,
    AVISO_DISTRIBUCION_DIARIA,
    AVISO_DISTRIBUCION_DIAS,
    AVISO_TOTAL_DIARIO_ALCANZADO,
    AVISO_TOTAL_DIARIO_SUPERADO,
)

# Severidades normalizadas a partir de los niveles del plan 4.4 (ordenadas de menor a mayor para
# desempatar duplicadas; el orden no cambia el calculo, solo cual duplicada se conserva).
SEVERIDADES = (
    "informativo", "configuracion", "preventivo", "revision", "calculo_pendiente", "advertencia", "critico",
)
_RANGO = {s: i for i, s in enumerate(SEVERIDADES)}


@dataclass(frozen=True)
class DefinicionAlerta:
    codigo: str
    nombre: str
    nivel: str  # texto literal de la columna "Nivel" del plan 4.4
    severidades: tuple[str, ...]  # severidades que una instancia puede llevar
    bloquea_cierre: bool = False  # solo lo no resuelto bloquea el calculo DEFINITIVO (NL04, RE02)
    nota: str = ""


def _d(codigo, nombre, nivel, severidades, bloquea_cierre=False, nota=""):
    return DefinicionAlerta(codigo, nombre, nivel, tuple(severidades), bloquea_cierre, nota)


_DEFINICIONES = (
    _d("AL01", "Próximo a límite ordinario diario/semanal", "Preventivo", ("preventivo",)),
    _d("AL02", "Tiempo extraordinario detectado", "Informativo/revisión", ("informativo", "revision")),
    _d("AL03", "Próximo a tope art. 66 semanal", "Preventivo", ("preventivo",)),
    _d("AL04", "Tope art. 66 alcanzado / superado", "Advertencia diferenciada", ("advertencia",)),
    _d("AL05", "Distribución art. 66 superior a 4 h/día o 4 días/semana", "Crítico/revisión legal",
       ("critico", "revision")),
    _d("AL06", "Tramo adicional art. 68 próximo a / superior a 4 h semanales", "Preventivo/crítico",
       ("preventivo", "critico")),
    _d("AL07", "Tiempo total diario próximo a / superior a 12 h", "Preventivo/crítico",
       ("preventivo", "critico")),
    _d("AL08", "Descanso semanal no acreditado", "Crítico/revisión", ("critico", "revision")),
    _d("AL09", "Horario futuro incompatible con reforma", "Preventivo", ("preventivo",)),
    _d("AL10", "Checada incompleta, duplicada o inconsistente", "Revisión", ("revision",)),
    _d("AL11", "Exceso de umbral interno patronal", "Advertencia administrativa", ("advertencia",),
       nota="el umbral y la magnitud que compara son configuracion patronal (pregunta abierta Q-K)"),
    _d("AL12", "Horario/norma ausente o transición no resuelta", "Cálculo pendiente", ("calculo_pendiente",),
       bloquea_cierre=True),
    _d("AL13", "Prohibición para menores de 18", "Crítico", ("critico",)),
    _d("AL14", "Tipo de jornada declarado no coincide con el art. 60", "Configuración", ("configuracion",),
       nota="no bloquea (decisión del propietario, 27/11/2026)"),
    # Fuera de AL01-AL14: alerta del plan 5.2 que ya producen T3/T5 y que el plan no clasifica.
    _d("HO03", "Horario incompatible con el tope legal", "Sin nivel en el plan (5.2)", ("revision",),
       nota="plan 5.2: remanente asignado a los ultimos minutos programados; RH debe corregir el horario"),
)

CATALOGO: dict[str, DefinicionAlerta] = {d.codigo: d for d in _DEFINICIONES}
ALERTAS = tuple(c for c in CATALOGO if c.startswith("AL"))

AL01, AL02, AL03, AL04, AL05, AL06, AL07, AL08, AL09, AL10, AL11, AL12, AL13, AL14 = ALERTAS
HO03 = "HO03"


def definicion(codigo: str) -> DefinicionAlerta:
    """Definicion del catalogo; `KeyError` si el codigo no existe (no se inventan alertas)."""
    return CATALOGO[codigo]


@dataclass(frozen=True)
class Alerta:
    """Una alerta concreta. Identidad = `clave_deduplicacion`; `severidad` y `detalle` son informativos."""

    codigo: str
    trabajador: str
    empresa: str
    severidad: str
    periodo: Vigencia | None = None  # semana laboral (o periodo) evaluado
    dia_logico: date | None = None  # None: alerta de la semana completa
    sujeto: str = ""  # a que se refiere dentro de la regla (aviso, tipo de incidencia, comida...)
    version: str = ""  # version de norma/politica con la que se evaluo (plan 4.4: "regla y version")
    detalle: str = ""

    def __post_init__(self):
        try:
            definido = CATALOGO[self.codigo]
        except KeyError:
            raise ValueError(f"alerta fuera del catalogo: {self.codigo!r}") from None
        if self.severidad not in definido.severidades:
            raise ValueError(f"{self.codigo} no admite severidad {self.severidad!r}: {definido.severidades}")

    @property
    def bloquea_cierre(self) -> bool:
        return CATALOGO[self.codigo].bloquea_cierre


def _iso(valor: date | None) -> str | None:
    return None if valor is None else valor.isoformat()


def clave_deduplicacion(alerta: Alerta) -> str:
    """Clave determinista: JSON canonico de (regla, trabajador, empresa, periodo, dia, sujeto, version).

    Sin separadores ambiguos y sin depender de orden de llegada, severidad ni detalle (P-48).
    """
    periodo = None if alerta.periodo is None else [_iso(alerta.periodo.desde), _iso(alerta.periodo.hasta)]
    return json.dumps(
        [alerta.codigo, alerta.trabajador, alerta.empresa, periodo, _iso(alerta.dia_logico), alerta.sujeto,
         alerta.version],
        ensure_ascii=True, separators=(",", ":"),
    )


def _preferida(a: Alerta):
    return (_RANGO[a.severidad], a.detalle, a.severidad)


def consolidar(alertas) -> tuple[Alerta, ...]:
    """Una alerta por clave (la de mayor severidad; empate por detalle), ordenadas por clave. Nunca oculta una clave."""
    elegidas: dict[str, Alerta] = {}
    for a in alertas:
        k = clave_deduplicacion(a)
        if k not in elegidas or _preferida(a) > _preferida(elegidas[k]):
            elegidas[k] = a
    return tuple(elegidas[k] for k in sorted(elegidas))


# --- Normalizacion de lo que ya producen T1-T5 (sin tocar minutos) -----------------------------------

@dataclass(frozen=True)
class ContextoAlerta:
    """Identidad comun de las alertas de una evaluacion: quien, donde, que periodo y con que version."""

    trabajador: str
    empresa: str
    periodo: Vigencia | None = None
    version: str = ""


def _alerta(ctx: ContextoAlerta, codigo, *, severidad=None, dia_logico=None, sujeto="", detalle="", periodo=...):
    if codigo not in CATALOGO:
        raise ValueError(f"alerta fuera del catalogo: {codigo!r}")
    return Alerta(
        codigo, ctx.trabajador, ctx.empresa, severidad or CATALOGO[codigo].severidades[0],
        ctx.periodo if periodo is ... else periodo, dia_logico, sujeto, ctx.version, detalle,
    )


def alertas_de_codigos(codigos, ctx: ContextoAlerta, *, dia_logico: date | None = None, sujeto: str = "") -> tuple[Alerta, ...]:
    """Una alerta por codigo distinto (con la primera severidad del catalogo). Codigo desconocido: `ValueError`."""
    return tuple(_alerta(ctx, c, dia_logico=dia_logico, sujeto=sujeto) for c in sorted(set(codigos)))


def _de_codigos_y_motivos(codigos, motivos, ctx: ContextoAlerta, cubiertas=frozenset()) -> list[Alerta]:
    """Codigos sin detalle propio; AL12 se abre por motivo para saber que dato falta."""
    alertas = []
    for codigo in sorted(set(codigos) - set(cubiertas)):
        if codigo == AL12 and motivos:
            alertas += [_alerta(ctx, codigo, sujeto=m) for m in sorted(set(motivos))]
        else:
            alertas.append(_alerta(ctx, codigo))
    return alertas


_SEVERIDAD_DE_AVISO = {
    AVISO_ART66_PREVENTIVO: "preventivo",
    AVISO_ART66_ALCANZADO: "advertencia",
    AVISO_ART66_SUPERADO: "advertencia",
    AVISO_ART68_ALCANZADO: "preventivo",  # plan 4.4: "proximo a / superior a": alcanzar avisa, superar es critico
    AVISO_ART68_SUPERADO: "critico",
    AVISO_DISTRIBUCION_DIARIA: "critico",
    AVISO_DISTRIBUCION_DIAS: "critico",
    AVISO_TOTAL_DIARIO_ALCANZADO: "preventivo",
    AVISO_TOTAL_DIARIO_SUPERADO: "critico",
}


def alertas_de_extra(resultado, ctx: ContextoAlerta) -> tuple[Alerta, ...]:
    """AL02-AL07 y AL12 (T5): cada aviso por limite es una alerta con su severidad; el resto, por codigo.

    El aviso informativo del art. 61 no es alerta (decision Q-H). No modifica `resultado`.
    """
    alertas = [
        _alerta(ctx, ALERTA_DE_AVISO[a], severidad=_SEVERIDAD_DE_AVISO[a], sujeto=a) for a in sorted(resultado.avisos)
    ]
    cubiertas = {ALERTA_DE_AVISO[a] for a in resultado.avisos}
    return tuple(alertas + _de_codigos_y_motivos(resultado.alertas, resultado.motivos, ctx, cubiertas))


def alertas_de_segmentacion(resultado, ctx: ContextoAlerta) -> tuple[Alerta, ...]:
    """AL14 por dia logico (T4) y el resto (AL12...) de la semana."""
    por_dia = [_alerta(ctx, c, dia_logico=j.dia_logico) for j in resultado.jornadas for c in sorted(set(j.alertas))]
    cubiertas = {c for j in resultado.jornadas for c in j.alertas}
    return tuple(por_dia + _de_codigos_y_motivos(resultado.alertas, resultado.motivos, ctx, cubiertas))


def alertas_de_infracciones(infracciones, ctx: ContextoAlerta, dia_logico: date) -> tuple[Alerta, ...]:
    """AL13 (T1): una alerta critica por prohibicion violada; el sujeto es el codigo de la infraccion."""
    return tuple(
        _alerta(ctx, i.alerta, severidad="critico", dia_logico=dia_logico, sujeto=i.codigo, detalle=i.fundamento)
        for i in infracciones if i.alerta is not None
    )


_MARCAS_AL10 = frozenset({POSIBLE_DUPLICADO, FUTURA, DESFASE, CERCANA_SIN_RESOLVER})


def _origen(c) -> str:
    # Sin el id de la checada: una reimportacion puede asignar otros ids y debe dar la misma clave (P-48).
    return f"{c.reloj}:{c.instante_s}"


def alertas_de_emparejamiento(resultado, ctx: ContextoAlerta, marcadas=()) -> tuple[Alerta, ...]:
    """AL10 (T2): incidencias del emparejamiento y, si se aportan, las marcas de checada (nada se descarta)."""
    alertas = []
    for i in resultado.incidencias:
        primera = min(i.checadas, key=lambda c: (c.instante_s, c.reloj))
        alertas.append(_alerta(ctx, AL10, dia_logico=primera.fecha_local, sujeto=f"{i.tipo}:{_origen(primera)}",
                               detalle=i.detalle))
    for m in marcadas:
        for marca in sorted(m.marcas & _MARCAS_AL10):
            alertas.append(_alerta(ctx, AL10, dia_logico=m.checada.fecha_local, sujeto=f"{marca}:{_origen(m.checada)}"))
    return tuple(alertas)


# --- Evaluadores puros: AL01, AL08 (P-28), AL11 -----------------------------------------------------------------

def _no_negativo(valor, nombre):
    if isinstance(valor, bool) or not isinstance(valor, int) or valor < 0:
        raise ValueError(f"{nombre} debe ser un entero no negativo: {valor!r}")
    return valor


def evaluar_proximidad_limite_ordinario(
    acumulado_s, tope_s, anticipacion_s, ctx: ContextoAlerta, *, ambito: str, dia_logico: date | None = None
) -> Alerta | None:
    """AL01 (preventiva): `acumulado` en [tope - anticipacion, tope]. Por encima ya es extra (AL02).

    Sin tope o sin anticipacion configurados no hay aviso (como el preventivo de T5). `ambito` es
    "diario" o "semanal": quien llama decide cual tope entrega.
    """
    if ambito not in ("diario", "semanal"):
        raise ValueError(f"ambito desconocido: {ambito!r}")
    _no_negativo(acumulado_s, "acumulado_s")
    if tope_s is None or anticipacion_s is None:
        return None
    if tope_s - anticipacion_s <= acumulado_s <= tope_s:
        return _alerta(ctx, AL01, dia_logico=dia_logico, sujeto=ambito)
    return None


def evaluar_descanso_semanal(dias_trabajados, versiones, ctx: ContextoAlerta, *, dias_pendientes=()) -> tuple[Alerta, ...]:
    """AL08 / P-28: racha de dias seguidos sin descanso acreditado que supera el maximo del art. 69.

    Un dia con tiempo solo pendiente NO acredita descanso (cuenta en la racha). Una alerta por racha, en el
    dia que la completa (maximo + 1): crece la racha y la clave no cambia. Cruza semanas, por lo que la
    identidad no lleva periodo. El maximo sale de la norma versionada; sin el, AL12 (sin inventar uno).
    """
    alertas, motivos, racha, previo = [], set(), 0, None
    for dia in sorted(set(dias_trabajados) | set(dias_pendientes)):
        racha = racha + 1 if previo is not None and dia - previo == timedelta(days=1) else 1
        previo = dia
        try:
            limite = resolver_vigente(versiones, n.DESCANSO_DIAS_TRABAJO_MAX, dia).valor
        except _ERRORES_DE_CONFIGURACION as error:
            motivos.add(_motivo_de(error))
            continue
        if racha == limite + 1:
            alertas.append(_alerta(ctx, AL08, dia_logico=dia, sujeto=f"{racha}_dias_seguidos", periodo=None))
    alertas += [_alerta(ctx, AL12, sujeto=m) for m in sorted(motivos)]
    return tuple(alertas)


def evaluar_umbral_interno(valor_s, umbral_s, ctx: ContextoAlerta, *, sujeto: str, dia_logico: date | None = None) -> Alerta | None:
    """AL11: `valor` rebasa el umbral interno patronal (opcional). Sin umbral no hay alerta.

    Que magnitud se compara y de donde sale el umbral es configuracion patronal aun no definida (Q-K):
    `sujeto` nombra la magnitud y quien llama entrega el umbral resuelto.
    """
    _no_negativo(valor_s, "valor_s")
    if umbral_s is None or valor_s <= umbral_s:
        return None
    return _alerta(ctx, AL11, dia_logico=dia_logico, sujeto=sujeto)
