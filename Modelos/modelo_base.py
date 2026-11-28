# -*- coding: utf-8 -*-
# Modelos/modelo_base.py
"""Base comun de los modelos: respuesta estandar y CRUD parametrizado sobre SQLite.

Lecturas: una conexion por operacion. Escrituras: siempre dentro de UnidadTrabajo
(todo o nada). Todo valor viaja como parametro; los nombres de tabla/columna se
validan contra una lista blanca de identificadores.
"""

import re
from pathlib import Path

from Database.conexion_sqlite import abrir_conexion
from Database.unidad_trabajo import UnidadTrabajo

_IDENTIFICADOR = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class OperacionNoPermitida(Exception):
    """El modelo no admite esta operacion (p. ej. actualizar una tabla solo-insercion)."""


def _identificador(nombre: str) -> str:
    if not isinstance(nombre, str) or not _IDENTIFICADOR.match(nombre):
        raise ValueError(f"Identificador SQL invalido: {nombre!r}")
    return nombre


class ModeloBase:
    """Todo modelo de modulo hereda de esta clase.

    Subclases CRUD declaran `tabla`. Las tablas solo-insercion (checadas,
    bitacora, archivos originales, actas) ponen `solo_insercion = True`:
    `actualizar` y `eliminar` se rechazan con OperacionNoPermitida (DV3).
    """

    tabla = ""
    solo_insercion = False

    def __init__(self, ruta_bd: str | Path):
        self.ruta_bd = Path(ruta_bd)

    # --- respuesta estandar {exito, resultado, mensaje, campo} ---
    @staticmethod
    def _resultado_ok(resultado=None) -> dict:
        return {"exito": True, "resultado": resultado, "mensaje": "", "campo": ""}

    @staticmethod
    def _resultado_error(mensaje: str, campo: str = "") -> dict:
        return {"exito": False, "resultado": None, "mensaje": mensaje, "campo": campo}

    def _requerido(self, valor, nombre_campo: str) -> dict | None:
        """Devuelve un error si el valor esta vacio; None si es valido."""
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            etiqueta = nombre_campo.replace("_", " ")
            return self._resultado_error(
                f"El campo '{etiqueta}' es obligatorio.", nombre_campo
            )
        return None

    # --- acceso a datos ---
    def consultar(self, sql: str, parametros: tuple = ()) -> list[dict]:
        """SELECT parametrizado; devuelve una lista de dicts."""
        cn = abrir_conexion(self.ruta_bd)
        try:
            return [dict(f) for f in cn.execute(sql, parametros).fetchall()]
        finally:
            cn.close()

    def ejecutar(self, sql: str, parametros: tuple = ()) -> int:
        """Escritura parametrizada en una unidad de trabajo; devuelve rowcount."""
        cn = abrir_conexion(self.ruta_bd)
        try:
            with UnidadTrabajo(cn) as tx:
                return tx.execute(sql, parametros).rowcount
        finally:
            cn.close()

    def _tabla(self) -> str:
        if not self.tabla:
            raise NotImplementedError("El modelo no declara 'tabla'.")
        return _identificador(self.tabla)

    def obtener(self, id_registro) -> dict | None:
        filas = self.consultar(
            f"SELECT * FROM {self._tabla()} WHERE id = ?", (id_registro,)
        )
        return filas[0] if filas else None

    def listar(self, orden: str = "id") -> list[dict]:
        return self.consultar(
            f"SELECT * FROM {self._tabla()} ORDER BY {_identificador(orden)}"
        )

    def insertar(self, datos: dict) -> int:
        """INSERT; devuelve el id generado."""
        if not datos:
            raise ValueError("insertar requiere al menos un campo.")
        columnas = [_identificador(c) for c in datos]
        marcas = ", ".join("?" for _ in columnas)
        sql = f"INSERT INTO {self._tabla()} ({', '.join(columnas)}) VALUES ({marcas})"
        cn = abrir_conexion(self.ruta_bd)
        try:
            with UnidadTrabajo(cn) as tx:
                return tx.execute(sql, tuple(datos.values())).lastrowid
        finally:
            cn.close()

    def actualizar(self, id_registro, datos: dict) -> int:
        self._exigir_modificable("actualizar")
        if not datos:
            raise ValueError("actualizar requiere al menos un campo.")
        asignaciones = ", ".join(f"{_identificador(c)} = ?" for c in datos)
        return self.ejecutar(
            f"UPDATE {self._tabla()} SET {asignaciones} WHERE id = ?",
            (*datos.values(), id_registro),
        )

    def eliminar(self, id_registro) -> int:
        self._exigir_modificable("eliminar")
        return self.ejecutar(
            f"DELETE FROM {self._tabla()} WHERE id = ?", (id_registro,)
        )

    def _exigir_modificable(self, operacion: str) -> None:
        if self.solo_insercion:
            raise OperacionNoPermitida(
                f"'{self.tabla}' es solo-insercion: no admite {operacion}."
            )
