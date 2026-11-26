import _analisis as an
import pytest

APP = {
    "Config", "Database", "Dominio", "Modelos", "Vistas", "Controladores",
    "Servicios", "Repositorios", "ClasesComunes", "Validadores", "main",
}

# Doc. 03 seccion 5: lo que cada capa NO puede importar. Nadie importa main.
PROHIBIDO_POR_CAPA = {
    "Vistas": {"Modelos", "Servicios", "Repositorios", "Database", "sqlite3", "main"},
    "Controladores": {"Repositorios", "Database", "sqlite3", "main"},
    "Modelos": {"PySide6", "Vistas", "Controladores", "main"},
    "Servicios": {"PySide6", "Vistas", "Controladores", "main"},
    "Repositorios": {"PySide6", "Modelos", "Servicios", "Vistas", "Controladores", "main"},
    "Database": {
        "PySide6", "Modelos", "Servicios", "Repositorios", "Vistas", "Controladores", "main",
    },
    "Dominio": APP | {"PySide6", "sqlite3"},
}


def revisar_capa(capa: str, carpeta) -> list[str]:
    return an.violaciones_importacion(carpeta, PROHIBIDO_POR_CAPA[capa])


@pytest.mark.parametrize("capa", sorted(PROHIBIDO_POR_CAPA))
def test_capa_respeta_direccion(capa):
    carpeta = an.RAIZ / capa
    if not carpeta.is_dir():
        pytest.skip(f"{capa} aun no existe")
    assert revisar_capa(capa, carpeta) == []


@pytest.mark.parametrize(
    "capa,codigo",
    [
        ("Modelos", "from Vistas.vista_x import VistaX\n"),
        ("Modelos", "from PySide6.QtWidgets import QWidget\n"),
        ("Database", "import Modelos.modelo_base\n"),
        ("Controladores", "import sqlite3\n"),
        ("Vistas", "from Database.conexion_sqlite import abrir_conexion\n"),
        ("Dominio", "from Config.config import NOMBRE_APP\n"),
    ],
)
def test_detecta_violacion(tmp_path, capa, codigo):
    (tmp_path / "malo.py").write_text(codigo, encoding="utf-8")
    assert len(revisar_capa(capa, tmp_path)) == 1


def test_importacion_permitida_no_se_marca(tmp_path):
    (tmp_path / "bueno.py").write_text(
        "from Database.unidad_trabajo import UnidadTrabajo\nimport re\n", encoding="utf-8"
    )
    assert revisar_capa("Modelos", tmp_path) == []
