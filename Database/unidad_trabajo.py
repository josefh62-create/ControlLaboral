# -*- coding: utf-8 -*-
# Database/unidad_trabajo.py
"""Unidad de trabajo: una transaccion explicita, todo o nada."""

import sqlite3


class UnidadTrabajo:
    """Context manager: BEGIN IMMEDIATE; COMMIT al salir bien, ROLLBACK si hay excepcion.

    Uso:
        with UnidadTrabajo(conexion) as cn:
            cn.execute(...)
    """

    def __init__(self, conexion: sqlite3.Connection):
        self._conexion = conexion

    def __enter__(self) -> sqlite3.Connection:
        self._conexion.execute("BEGIN IMMEDIATE")
        return self._conexion

    def __exit__(self, tipo, valor, traza) -> bool:
        if tipo is None:
            try:
                self._conexion.execute("COMMIT")
            except Exception:
                self._revertir()
                raise
        else:
            self._revertir()  # la excepcion original sigue propagandose
        return False

    def _revertir(self) -> None:
        # SQLite puede haber revertido solo; no enmascarar el error original.
        if self._conexion.in_transaction:
            try:
                self._conexion.execute("ROLLBACK")
            except sqlite3.Error:
                pass
