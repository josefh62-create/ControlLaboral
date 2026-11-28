import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from ClasesComunes import temas  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_archivos_qss_existen():
    for nombre in ("base.qss", "light.qss", "dark.qss"):
        assert (temas.CARPETA_ESTILOS / nombre).is_file()


@pytest.mark.parametrize("tema", temas.TEMAS)
def test_cargar_qss_incluye_base_y_tema(tema):
    qss = temas.cargar_qss(tema)
    assert "QPushButton" in qss and "background-color" in qss


def test_temas_difieren():
    assert temas.cargar_qss("claro") != temas.cargar_qss("oscuro")


def test_tema_desconocido_usa_defecto(app):
    assert temas.aplicar_tema(app, "inexistente") == temas.TEMA_POR_DEFECTO


def test_alternar_cambia_hoja_aplicada(app):
    temas.aplicar_tema(app, "claro")
    claro = app.styleSheet()
    assert temas.alternar_tema(app, "claro") == "oscuro"
    assert app.styleSheet() != claro
    assert temas.alternar_tema(app, "oscuro") == "claro"
    assert app.styleSheet() == claro


def test_tema_del_sistema_es_valido(app):
    assert temas.tema_del_sistema(app) in temas.TEMAS
