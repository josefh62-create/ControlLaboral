import _analisis as an

PROHIBIDOS = {
    "PySide6", "sqlite3", "Database", "Modelos", "Vistas",
    "Controladores", "Servicios", "Repositorios",
}


def revisar_pureza(carpeta) -> list[str]:
    """Todas las violaciones de pureza bajo `carpeta`."""
    fallos = an.violaciones_importacion(carpeta, PROHIBIDOS)
    for ruta in an.archivos_py(carpeta):
        fallos += [
            f"{ruta.name}:{linea} llama {nombre}"
            for nombre, linea in an.llamadas_reloj(ruta)
        ]
    return fallos


def test_dominio_es_puro():
    assert revisar_pureza(an.RAIZ / "Dominio") == []


def test_detecta_importaciones_prohibidas(tmp_path):
    (tmp_path / "malo.py").write_text(
        "import sqlite3\nfrom PySide6.QtCore import QObject\n"
        "from Database.crear_bd import crear_o_actualizar_bd\n",
        encoding="utf-8",
    )
    fallos = revisar_pureza(tmp_path)
    assert len(fallos) == 3


def test_detecta_lectura_del_reloj(tmp_path):
    (tmp_path / "malo.py").write_text(
        "import datetime, time\nfrom datetime import date\n"
        "from time import time as ahora\n"
        "a = datetime.datetime.now()\nb = datetime.datetime.today()\n"
        "c = date.today()\nd = time.time()\ne = ahora()\n",
        encoding="utf-8",
    )
    assert len(revisar_pureza(tmp_path)) == 5


def test_codigo_puro_no_se_marca(tmp_path):
    (tmp_path / "bueno.py").write_text(
        "from datetime import date, timedelta\nimport zoneinfo\n"
        "def f(d: date): return d + timedelta(days=1)\n",
        encoding="utf-8",
    )
    assert revisar_pureza(tmp_path) == []
