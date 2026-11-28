# -*- coding: utf-8 -*-
# Controladores/controlador_base.py
"""Base comun de los controladores (contrato de la barra global, doc. maestro 3.4).

Sin dependencia de PySide6: un controlador que necesite senales puede mezclar
QObject en su propia clase. Todos los hooks son no-op sobrescribibles.
"""


class ControladorBase:
    """Coordina una vista y un modelo. No contiene SQL."""

    def __init__(self, vista=None, modelo=None):
        self.vista = vista
        self.modelo = modelo
        self.main = None

    def inicializar_modulo(self):
        """Primer acceso al modulo."""

    def nuevo(self):
        """Barra global: iniciar un registro nuevo."""

    def guardar(self):
        """Barra global: guardar el registro actual."""

    def buscar(self):
        """Barra global: buscar o filtrar."""

    def cancelar(self):
        """Barra global: descartar la operacion en curso (no navega)."""

    def refrescar_datos(self):
        """Regreso al modulo desde otra pantalla."""
