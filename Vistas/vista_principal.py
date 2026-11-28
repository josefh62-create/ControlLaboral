# -*- coding: utf-8 -*-
# Vistas/vista_principal.py
"""Ventana principal: sidebar de modulos y area central con paginas apiladas."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMainWindow, QPushButton

from Vistas.frm_principal import Ui_frmPrincipal


class VistaPrincipal(QMainWindow):
    """Solo presentacion: emite senales, no conoce datos ni modelos."""

    tema_solicitado = Signal()
    salir_solicitado = Signal()
    modulo_solicitado = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_frmPrincipal()
        self.ui.setupUi(self)
        # boton del .ui -> clave del modulo. Para cada modulo nuevo: definir su boton
        # en frm_principal.ui dentro de qfrmModulos (checkable) y agregar aqui una
        # entrada, p. ej. {self.ui.qbtnEmpleados: "empleados"}. Nada se crea en codigo.
        self._sidebar_botones: dict[QPushButton, str] = {}
        self.ui.qbtnTema.clicked.connect(self.tema_solicitado)
        self.ui.qbtnSalir.clicked.connect(self.salir_solicitado)
        self.conectar_sidebar()

    def conectar_sidebar(self) -> None:
        """Conecta cada boton de `_sidebar_botones` con su modulo (senal `modulo_solicitado`)."""
        for boton, clave in self._sidebar_botones.items():
            boton.clicked.connect(lambda _=False, c=clave: self.modulo_solicitado.emit(c))

    def actualizar_sidebar(self, clave: str | None) -> None:
        """Marca como activo el boton del modulo `clave` (ninguno si es None)."""
        for boton, clave_boton in self._sidebar_botones.items():
            boton.setChecked(clave_boton == clave)

    def mostrar_inicio(self) -> None:
        self.ui.qstwPaginas.setCurrentWidget(self.ui.qwdInicio)
