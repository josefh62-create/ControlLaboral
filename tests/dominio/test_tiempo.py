"""Tiempo en segundos enteros, intervalos [inicio, fin) y formato (RE07, P-39)."""
import pytest

from Dominio.tiempo import (
    Intervalo,
    formatear_hhmm,
    formatear_hhmm_abajo,
    formatear_hhmmss,
    horas_a_segundos,
    minutos_a_segundos,
)


def test_minutos_y_horas_a_segundos():
    assert minutos_a_segundos(1) == 60
    assert minutos_a_segundos(460) == 27_600
    assert horas_a_segundos(8) == 28_800


def test_p39_7h40_por_6_dias_son_46h_exactas():
    por_dia = minutos_a_segundos(7 * 60 + 40)
    assert por_dia * 6 == horas_a_segundos(46)
    assert formatear_hhmmss(por_dia * 6) == "46:00:00"
    assert formatear_hhmm(por_dia * 6) == "46:00"


def test_unidades_son_enteras():
    assert isinstance(minutos_a_segundos(5), int)
    with pytest.raises(TypeError):
        minutos_a_segundos(7.5)


def test_formato_hhmmss_y_horas_mayores_a_24():
    assert formatear_hhmmss(0) == "00:00:00"
    assert formatear_hhmmss(3661) == "01:01:01"
    assert formatear_hhmmss(horas_a_segundos(30) + 5) == "30:00:05"


def test_re07_hhmm_nunca_reduce_al_trabajador():
    # 07:10:01 trabajados se muestran 07:11, jamas 07:10 (TO03: distingue 07:10:01)
    s = horas_a_segundos(7) + minutos_a_segundos(10) + 1
    assert formatear_hhmm(s) == "07:11"
    assert formatear_hhmm(s - 1) == "07:10"


def test_hhmm_abajo_para_topes_y_holguras():
    s = horas_a_segundos(7) + minutos_a_segundos(10) + 59
    assert formatear_hhmm_abajo(s) == "07:10"


def test_formato_rechaza_negativos():
    with pytest.raises(ValueError):
        formatear_hhmmss(-1)
    with pytest.raises(ValueError):
        formatear_hhmm(-1)


def test_intervalo_duracion_y_validacion():
    assert Intervalo(100, 460).duracion == 360
    assert Intervalo(100, 100).duracion == 0
    with pytest.raises(ValueError):
        Intervalo(10, 5)


def test_intervalo_semiabierto_contiene():
    i = Intervalo(10, 20)
    assert i.contiene(10)
    assert i.contiene(19)
    assert not i.contiene(20)


def test_intervalos_contiguos_no_se_traslapan():
    a, b = Intervalo(0, 10), Intervalo(10, 20)
    assert not a.se_traslapa(b)
    assert a.interseccion(b) is None


def test_interseccion_y_traslape():
    a, b = Intervalo(0, 15), Intervalo(10, 20)
    assert a.se_traslapa(b) and b.se_traslapa(a)
    assert a.interseccion(b) == Intervalo(10, 15)
    assert Intervalo(0, 100).interseccion(Intervalo(20, 30)) == Intervalo(20, 30)
    assert Intervalo(0, 5).interseccion(Intervalo(7, 9)) is None


def test_intervalo_vacio_no_se_traslapa():
    assert not Intervalo(5, 5).se_traslapa(Intervalo(0, 10))


def test_dividir_en_un_instante_interior():
    izq, der = Intervalo(0, 100).dividir(40)
    assert (izq, der) == (Intervalo(0, 40), Intervalo(40, 100))
    assert izq.duracion + der.duracion == 100


def test_dividir_en_extremos_o_fuera_da_un_solo_tramo():
    i = Intervalo(0, 100)
    assert i.dividir(0) == (i,)
    assert i.dividir(100) == (i,)
    assert i.dividir(150) == (i,)
    assert i.dividir(-5) == (i,)


def test_intervalo_es_inmutable():
    with pytest.raises(AttributeError):
        Intervalo(0, 1).inicio = 5


# --- Conversion instante <-> fecha local (soporte de calendario y horarios) ----------

def test_conversion_epoch_y_fecha_local():
    from datetime import date, datetime
    from zoneinfo import ZoneInfo

    from Dominio.tiempo import a_segundos_epoch, fecha_local, instante_local

    cdmx = ZoneInfo("America/Mexico_City")
    dt = datetime(2027, 1, 4, 23, 30, tzinfo=cdmx)
    s = a_segundos_epoch(dt)
    assert fecha_local(s, cdmx) == date(2027, 1, 4)
    assert fecha_local(s + 31 * 60, cdmx) == date(2027, 1, 5)  # 00:01 del dia siguiente
    assert instante_local(date(2027, 1, 4), 23 * 3600 + 1800, cdmx) == s
    # segundos del dia mayores a 24 h caen en el dia siguiente (turno nocturno)
    assert instante_local(date(2027, 1, 4), 25 * 3600, cdmx) == instante_local(date(2027, 1, 5), 3600, cdmx)
    with pytest.raises(ValueError):
        a_segundos_epoch(datetime(2027, 1, 4, 8, 0))  # sin zona
