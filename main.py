# -*- coding: utf-8 -*-
# main.py
"""Punto de entrada. Compone la aplicacion; ninguna capa importa este modulo."""

import os
import sys

# El runtime portatil embeddable no agrega el directorio del script a sys.path.
_DIR_APP = os.path.dirname(os.path.abspath(__file__))
if _DIR_APP not in sys.path:
    sys.path.insert(0, _DIR_APP)

from PySide6.QtWidgets import QApplication  # noqa: E402

import controllaboral_rc  # noqa: F401,E402  (registra los recursos del QRC)
from Config.config import NOMBRE_APP, ruta_bd  # noqa: E402
from Controladores.controlador_principal import ControladorPrincipal  # noqa: E402
from Database.crear_bd import crear_o_actualizar_bd  # noqa: E402
from Vistas.vista_principal import VistaPrincipal  # noqa: E402


def construir_ventana(app):
    """Prepara la BD y arma vista y controlador (sin mostrar ni ejecutar)."""
    bd = ruta_bd()
    bd.parent.mkdir(parents=True, exist_ok=True)
    crear_o_actualizar_bd(bd)
    vista = VistaPrincipal()
    controlador = ControladorPrincipal(vista, app)
    return vista, controlador


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(NOMBRE_APP)
    vista, _controlador = construir_ventana(app)
    vista.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
