# -*- coding: utf-8 -*-
# ClasesComunes/temas.py
"""Carga y aplicacion de los temas claro y oscuro.

Los colores viven solo en los .qss; ningun control define su propio color.
La eleccion del tema es en memoria (recordarla por usuario queda para despues).
"""

from pathlib import Path

from PySide6.QtCore import Qt

TEMAS = ("claro", "oscuro")
TEMA_POR_DEFECTO = "claro"

CARPETA_ESTILOS = Path(__file__).resolve().parents[1] / "Recursos" / "Estilos"

_ARCHIVO_POR_TEMA = {"claro": "light.qss", "oscuro": "dark.qss"}


def cargar_qss(tema: str) -> str:
    """Devuelve base.qss concatenado con la hoja de colores del tema."""
    if tema not in TEMAS:
        tema = TEMA_POR_DEFECTO
    base = (CARPETA_ESTILOS / "base.qss").read_text(encoding="utf-8")
    colores = (CARPETA_ESTILOS / _ARCHIVO_POR_TEMA[tema]).read_text(encoding="utf-8")
    return f"{base}\n{colores}"


def tema_del_sistema(app) -> str:
    """Tema que usa el sistema operativo; 'claro' si no se puede determinar."""
    try:
        esquema = app.styleHints().colorScheme()
    except AttributeError:
        return TEMA_POR_DEFECTO
    return "oscuro" if esquema == Qt.ColorScheme.Dark else TEMA_POR_DEFECTO


def aplicar_tema(app, tema: str) -> str:
    """Aplica el tema a la aplicacion y devuelve el tema realmente aplicado."""
    elegido = tema if tema in TEMAS else TEMA_POR_DEFECTO
    app.setStyleSheet(cargar_qss(elegido))
    return elegido


def alternar_tema(app, actual: str) -> str:
    """Cambia entre claro y oscuro y devuelve el tema aplicado."""
    return aplicar_tema(app, "oscuro" if actual == "claro" else "claro")
