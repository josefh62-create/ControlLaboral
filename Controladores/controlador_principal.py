# -*- coding: utf-8 -*-
# Controladores/controlador_principal.py
"""Controlador de la ventana principal: modulos, tema y salida."""

from ClasesComunes.temas import alternar_tema, aplicar_tema, tema_del_sistema
from Controladores.controlador_base import ControladorBase


class ControladorPrincipal(ControladorBase):
    """Coordina VistaPrincipal. Los modulos de E2 se registran en `modulos_disponibles`.

    Estructura de cada entrada: clave -> {"titulo": str, "crear": callable() -> controlador}.
    Esta entrega no registra ninguno.
    """

    def __init__(self, vista, app):
        super().__init__(vista=vista)
        self.app = app
        self.modulos_disponibles: dict[str, dict] = {}
        self.tema_actual = aplicar_tema(app, tema_del_sistema(app))
        vista.tema_solicitado.connect(self.alternar_tema)
        vista.salir_solicitado.connect(self.salir)
        for clave, datos in self.modulos_disponibles.items():
            vista.agregar_modulo(clave, datos["titulo"])

    def alternar_tema(self) -> None:
        self.tema_actual = alternar_tema(self.app, self.tema_actual)

    def salir(self) -> None:
        self.vista.close()
