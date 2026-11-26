# -*- coding: utf-8 -*-
# Database/conexion_sqlite.py
"""Apertura de conexiones SQLite con los PRAGMAs obligatorios verificados."""

import sqlite3
from pathlib import Path

BUSY_TIMEOUT_MS = 5000


class ErrorConexion(Exception):
    """La conexion no quedo con la configuracion de seguridad requerida."""


def _pragma(conexion: sqlite3.Connection, nombre: str):
    return conexion.execute(f"PRAGMA {nombre}").fetchone()[0]


def abrir_conexion(ruta: str | Path) -> sqlite3.Connection:
    """Abre la BD (la crea si no existe) con FK, WAL, synchronous=FULL y busy_timeout.

    Modo autocommit (isolation_level=None): las transacciones son explicitas
    y las maneja UnidadTrabajo.
    """
    conexion = sqlite3.connect(str(ruta), isolation_level=None)
    conexion.row_factory = sqlite3.Row
    try:
        conexion.execute("PRAGMA foreign_keys = ON")
        conexion.execute("PRAGMA journal_mode = WAL")
        conexion.execute("PRAGMA synchronous = FULL")
        conexion.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")

        esperado = {
            "foreign_keys": 1,
            "journal_mode": "wal",
            "synchronous": 2,  # FULL
            "busy_timeout": BUSY_TIMEOUT_MS,
        }
        for nombre, valor in esperado.items():
            real = _pragma(conexion, nombre)
            if isinstance(real, str):
                real = real.lower()
            if real != valor:
                raise ErrorConexion(
                    f"PRAGMA {nombre} no quedo activo: esperado {valor!r}, "
                    f"obtenido {real!r}."
                )
    except Exception:
        conexion.close()
        raise
    return conexion
