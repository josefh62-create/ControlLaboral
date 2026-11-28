# -*- coding: utf-8 -*-
"""Utilidades AST para las pruebas de arquitectura (sin importar el codigo analizado)."""

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

# Llamadas al reloj del sistema (sufijo de nombre punteado).
RELOJ_PROHIBIDO = {
    ("datetime", "now"),
    ("datetime", "today"),
    ("date", "today"),
    ("time", "time"),
}


def archivos_py(carpeta: Path):
    return sorted(p for p in Path(carpeta).rglob("*.py") if "__pycache__" not in p.parts)


def importaciones(ruta: Path) -> list[tuple[str, int]]:
    """Modulos de nivel superior importados (absolutos) como (nombre, linea)."""
    arbol = ast.parse(Path(ruta).read_text(encoding="utf-8"), filename=str(ruta))
    salida = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            salida += [(a.name.split(".")[0], nodo.lineno) for a in nodo.names]
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
            salida.append((nodo.module.split(".")[0], nodo.lineno))
    return salida


def _nombre_punteado(nodo) -> tuple[str, ...]:
    partes = []
    while isinstance(nodo, ast.Attribute):
        partes.append(nodo.attr)
        nodo = nodo.value
    if isinstance(nodo, ast.Name):
        partes.append(nodo.id)
    return tuple(reversed(partes))


def llamadas_reloj(ruta: Path) -> list[tuple[str, int]]:
    """Llamadas que leen el reloj del sistema, como (nombre, linea)."""
    arbol = ast.parse(Path(ruta).read_text(encoding="utf-8"), filename=str(ruta))
    # `from time import time as t` -> t() tambien cuenta.
    alias = {}
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
            for a in nodo.names:
                alias[a.asname or a.name] = (nodo.module.split(".")[-1], a.name)
    salida = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        nombre = _nombre_punteado(nodo.func)
        if len(nombre) == 1 and nombre[0] in alias:
            nombre = alias[nombre[0]]
        if len(nombre) >= 2 and nombre[-2:] in RELOJ_PROHIBIDO:
            salida.append((".".join(nombre), nodo.lineno))
    return salida


def violaciones_importacion(carpeta: Path, prohibidos: set[str]) -> list[str]:
    """Importaciones prohibidas bajo `carpeta`, como 'archivo:linea importa X'."""
    salida = []
    for ruta in archivos_py(carpeta):
        for modulo, linea in importaciones(ruta):
            if modulo in prohibidos:
                salida.append(f"{ruta.name}:{linea} importa {modulo}")
    return salida
