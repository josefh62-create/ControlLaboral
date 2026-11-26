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
        self._botones_modulo: dict[str, QPushButton] = {}
        self.ui.qbtnTema.clicked.connect(self.tema_solicitado)
        self.ui.qbtnSalir.clicked.connect(self.salir_solicitado)

    def agregar_modulo(self, clave: str, texto: str, pagina=None) -> None:
        """Agrega un boton al sidebar y, si se da, su pagina al area central."""
        boton = QPushButton(texto, self.ui.qfrmModulos)
        boton.setObjectName(f"qbtnModulo_{clave}")
        boton.clicked.connect(lambda _=False, c=clave: self.modulo_solicitado.emit(c))
        self.ui.layoutModulos.addWidget(boton)
        self._botones_modulo[clave] = boton
        if pagina is not None:
            self.ui.qstwPaginas.addWidget(pagina)

    def mostrar_inicio(self) -> None:
        self.ui.qstwPaginas.setCurrentWidget(self.ui.qwdInicio)

    @property
    def claves_modulo(self) -> list[str]:
        return list(self._botones_modulo)
