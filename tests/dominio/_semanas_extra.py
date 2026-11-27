"""Ayudas de prueba para T5 (criterios y tramos de extra): arman una semana completa de punta a punta
(checadas -> piezas efectivas -> segmentos) para comprobar los ejemplos del plan 5.2 y la matriz P-xx.

Horas como enteros o (h, m); un dia trabajado es una lista de pares (entrada, salida) y una salida
mayor de 24 h cruza la medianoche. Todo es de prueba: ninguna constante legal vive en el codigo."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from Dominio.calendario import CalendarioAnual
from Dominio.checadas import Checada
from Dominio.emparejamiento import NORMAL, IntervaloEmparejado
from Dominio.horarios import DiaHorario, Horario, construir_intervalos_efectivos
from Dominio.modelos import Vigencia
from Dominio.normatividad import SEMILLA_LEGAL, SEMILLA_PATRONAL
from Dominio.segmentacion import segmentar
from Dominio.tiempo import Intervalo, instante_local
from Dominio.tolerancias import CLAVES_TOLERANCIA, version_de_tolerancia

CDMX = ZoneInfo("America/Mexico_City")
H, M = 3600, 60
BASE = tuple(SEMILLA_LEGAL) + tuple(SEMILLA_PATRONAL)
CALENDARIOS = tuple(CalendarioAnual(a, frozenset(), confirmado=True) for a in range(2026, 2032))

# Lunes de semanas limpias (sin cruce de anio ni festivos) de cada anio de la reforma.
LUN_2026 = date(2026, 6, 1)
LUN_2027 = date(2027, 1, 4)
LUN_2028 = date(2028, 1, 3)
LUN_2029 = date(2029, 1, 1)
LUN_2030 = date(2030, 1, 7)

# Horario acordado 5 x 8 + 6 = 46 h (distribucion ilustrativa del plan 4.2 para 2027).
PROGRAMA_46 = {0: [(8, 16)], 1: [(8, 16)], 2: [(8, 16)], 3: [(8, 16)], 4: [(8, 16)], 5: [(8, 14)]}
# Otras distribuciones ilustrativas (plan 4.2): 48 h (2026), 44 h (2028), 42 h (2029) y 40 h (2030).
PROGRAMA_48 = {d: [(8, 16)] for d in range(6)}
PROGRAMA_44 = {**{d: [(8, 16)] for d in range(5)}, 5: [(8, 12)]}
PROGRAMA_42 = {**{d: [(8, 16)] for d in range(5)}, 5: [(8, 10)]}
PROGRAMA_40 = {d: [(8, 16)] for d in range(5)}


def hm(x) -> int:
    h, m = (x, 0) if isinstance(x, int) else x
    return h * H + m * M


def t(fecha, x):
    return instante_local(fecha, hm(x), CDMX)


def par(inicio, fin):
    def ck(id_, s):
        return Checada(id_, datetime.fromtimestamp(s, tz=CDMX), "R-AEI", "AEI")

    return IntervaloEmparejado(Intervalo(inicio, fin), ck(f"e{inicio}", inicio), ck(f"s{fin}", fin), NORMAL)


def horario(programa, regimen="diurna", **kw):
    dias = {d: DiaHorario(tuple(Intervalo(hm(a), hm(b)) for a, b in partes)) for d, partes in programa.items()}
    return Horario("H1", Vigencia(date(2026, 1, 1)), regimen, "America/Mexico_City", dias, empresa="AEI", **kw)


def tolerancias(minutos):
    return tuple(
        version_de_tolerancia(k, minutos, Vigencia(date(2026, 1, 1)), "prueba", "AEI") for k in CLAVES_TOLERANCIA
    )


def pares_de(lunes, trabajado):
    return [
        par(t(lunes + timedelta(days=d), a), t(lunes + timedelta(days=d), b))
        for d, partes in sorted(trabajado.items())
        for a, b in partes
    ]


def segmentar_semana(
    lunes, trabajado, programa=None, *, tolerancia=0, versiones=BASE, confirmaciones=(), regimen="diurna", **kw
):
    """Resultado de `segmentar` para la semana que empieza en `lunes` (tolerancia 0: todo lo trabajado es confirmado)."""
    horarios = [horario(PROGRAMA_46 if programa is None else programa, regimen, **kw)]
    versiones = tuple(versiones) + tolerancias(tolerancia)
    efectivo = construir_intervalos_efectivos(
        pares_de(lunes, trabajado), horarios, CDMX, versiones=versiones, confirmaciones=confirmaciones
    )
    return segmentar(efectivo, CDMX, horarios, CALENDARIOS, versiones, empresa="AEI"), versiones


def dia_de(lunes, d):
    return lunes + timedelta(days=d)
