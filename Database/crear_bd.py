# -*- coding: utf-8 -*-
# Database/crear_bd.py
"""Crea o actualiza la BD aplicando migraciones SQL versionadas.

Cada Database/migraciones/NNNN_descripcion.sql se aplica una sola vez, en orden,
dentro de su propia transaccion. Nunca borra ni sobrescribe una BD existente.
"""

import hashlib
import re
import sqlite3
from pathlib import Path

from Config.config import VERSION_ESQUEMA_SOPORTADA
from Database.conexion_sqlite import abrir_conexion
from Database.unidad_trabajo import UnidadTrabajo

CARPETA_MIGRACIONES = Path(__file__).resolve().parent / "migraciones"
_PATRON = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")


class ErrorEsquema(Exception):
    """La BD no es compatible con esta version de la aplicacion."""


def _migraciones(carpeta: Path) -> list[tuple[int, str, Path]]:
    encontradas = []
    for archivo in sorted(carpeta.glob("*.sql")):
        m = _PATRON.match(archivo.name)
        if not m:
            raise ErrorEsquema(f"Nombre de migracion invalido: {archivo.name}")
        encontradas.append((int(m.group(1)), archivo.stem, archivo))
    numeros = [n for n, _, _ in encontradas]
    if numeros != list(range(1, len(numeros) + 1)):
        raise ErrorEsquema("Las migraciones deben ser consecutivas desde 0001.")
    return encontradas


def _sentencias(sql: str) -> list[str]:
    """Divide un script en sentencias completas (respeta triggers, cadenas y comentarios)."""
    partes, actual = [], ""
    for trozo in sql.split(";"):
        actual += trozo + ";"
        if sqlite3.complete_statement(actual):
            if actual.replace(";", "").strip():
                partes.append(actual.strip())
            actual = ""
    resto = actual.rstrip(";").strip()
    if resto:
        partes.append(resto)
    return partes


def _checksums_aplicados(conexion: sqlite3.Connection) -> dict[str, str]:
    """Migraciones ya registradas: {nombre: checksum}."""
    existe = conexion.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='esquema_migracion'"
    ).fetchone()
    if not existe:
        return {}
    filas = conexion.execute("SELECT nombre, checksum FROM esquema_migracion")
    return {f["nombre"]: f["checksum"] for f in filas}


def _checksum(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


def _aplicar_migraciones(
    conexion: sqlite3.Connection, carpeta: Path = CARPETA_MIGRACIONES
) -> list[str]:
    """Aplica las pendientes; devuelve los nombres aplicados en esta llamada."""
    version_bd = conexion.execute("PRAGMA user_version").fetchone()[0]
    if version_bd > VERSION_ESQUEMA_SOPORTADA:
        raise ErrorEsquema(
            f"La base de datos tiene version de esquema {version_bd}, mayor a la "
            f"soportada por esta aplicacion ({VERSION_ESQUEMA_SOPORTADA}). "
            "Actualice la aplicacion; la base no se modifico."
        )

    aplicadas = _checksums_aplicados(conexion)
    nuevas = []
    for numero, nombre, archivo in _migraciones(carpeta):
        sql = archivo.read_text(encoding="utf-8")
        checksum = _checksum(sql)
        if nombre in aplicadas:
            if aplicadas[nombre] != checksum:
                raise ErrorEsquema(
                    f"La migracion {archivo.name} ya aplicada fue modificada "
                    "(el checksum no coincide). No se modifico la base."
                )
            continue
        with UnidadTrabajo(conexion) as cn:
            # Relectura dentro de la transaccion: otro proceso pudo aplicarla antes.
            if nombre in _checksums_aplicados(cn):
                continue
            for sentencia in _sentencias(sql):
                cn.execute(sentencia)
            cn.execute(
                "INSERT INTO esquema_migracion (id, nombre, checksum) VALUES (?, ?, ?)",
                (numero, nombre, checksum),
            )
            cn.execute(f"PRAGMA user_version = {numero}")
        nuevas.append(nombre)
    return nuevas


def crear_o_actualizar_bd(ruta: str | Path) -> list[str]:
    """Crea la BD si no existe y aplica migraciones pendientes (idempotente)."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conexion = abrir_conexion(ruta)
    try:
        return _aplicar_migraciones(conexion)
    finally:
        conexion.close()
