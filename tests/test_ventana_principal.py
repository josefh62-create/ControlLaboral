import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QFrame,
    QPushButton,
    QStackedWidget,
)

from Controladores.controlador_principal import ControladorPrincipal  # noqa: E402
from Vistas.vista_principal import VistaPrincipal  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ventana(app):
    vista = VistaPrincipal()
    controlador = ControladorPrincipal(vista, app)
    yield vista, controlador
    vista.close()


def test_estructura_de_la_vista(ventana):
    vista, _ = ventana
    assert isinstance(vista.ui.qfrmSidebar, QFrame)
    assert isinstance(vista.ui.qstwPaginas, QStackedWidget)
    assert vista.ui.qstwPaginas.count() == 1


def test_modulos_disponibles_vacio(ventana):
    vista, controlador = ventana
    assert controlador.modulos_disponibles == {}


def test_boton_tema_alterna(ventana, app):
    vista, controlador = ventana
    inicial = controlador.tema_actual
    hoja = app.styleSheet()
    vista.ui.qbtnTema.click()
    assert controlador.tema_actual != inicial
    assert app.styleSheet() != hoja
    vista.ui.qbtnTema.click()
    assert controlador.tema_actual == inicial


def test_boton_salir_cierra(ventana):
    vista, _ = ventana
    vista.show()
    vista.ui.qbtnSalir.click()
    assert not vista.isVisible()


def test_sidebar_vacio_y_sin_botones_creados_en_codigo(ventana):
    vista, controlador = ventana
    assert vista._sidebar_botones == {}
    assert controlador.modulos_disponibles == {}
    esperados = {"qbtnTema", "qbtnSalir"}
    nombres = {b.objectName() for b in vista.findChildren(QPushButton)}
    assert nombres == esperados


def test_sidebar_mapeado_emite_y_marca_activo(ventana):
    vista, controlador = ventana
    boton = QPushButton(vista)  # stub solo de prueba
    boton.setCheckable(True)
    vista._sidebar_botones = {boton: "demo"}
    vista.conectar_sidebar()
    controlador.modulos_disponibles["demo"] = {"titulo": "Demo", "crear": None}
    recibidas = []
    vista.modulo_solicitado.connect(recibidas.append)
    boton.click()
    assert recibidas == ["demo"]
    assert boton.isChecked()
    vista.actualizar_sidebar(None)
    assert not boton.isChecked()
