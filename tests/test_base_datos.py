import sqlite3

import pytest

from Config.config import VERSION_ESQUEMA_SOPORTADA
from Database.conexion_sqlite import abrir_conexion
from Database.crear_bd import ErrorEsquema, _aplicar_migraciones, crear_o_actualizar_bd
from Database.unidad_trabajo import UnidadTrabajo


def _esquema(ruta):
    cn = sqlite3.connect(ruta)
    try:
        return (
            cn.execute("SELECT type, name, sql FROM sqlite_master ORDER BY name").fetchall(),
            cn.execute("PRAGMA user_version").fetchone()[0],
        )
    finally:
        cn.close()


def test_migracion_idempotente(tmp_path):
    ruta = tmp_path / "t.db"
    assert crear_o_actualizar_bd(ruta) == ["0001_esquema_base"]
    antes = _esquema(ruta)
    assert crear_o_actualizar_bd(ruta) == []
    assert _esquema(ruta) == antes
    assert antes[1] == VERSION_ESQUEMA_SOPORTADA


def test_no_sobrescribe_bd_existente(tmp_path):
    ruta = tmp_path / "t.db"
    crear_o_actualizar_bd(ruta)
    cn = abrir_conexion(ruta)
    cn.execute("CREATE TABLE dato (x)")
    cn.execute("INSERT INTO dato VALUES (1)")
    cn.close()
    crear_o_actualizar_bd(ruta)
    cn = abrir_conexion(ruta)
    assert cn.execute("SELECT x FROM dato").fetchone()[0] == 1
    cn.close()


def test_pragmas_activos(tmp_path):
    cn = abrir_conexion(tmp_path / "t.db")
    try:
        assert cn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert cn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert cn.execute("PRAGMA synchronous").fetchone()[0] == 2
        assert cn.execute("PRAGMA busy_timeout").fetchone()[0] > 0
    finally:
        cn.close()


def test_unidad_trabajo_confirma(tmp_path):
    cn = abrir_conexion(tmp_path / "t.db")
    cn.execute("CREATE TABLE t (x)")
    with UnidadTrabajo(cn) as u:
        u.execute("INSERT INTO t VALUES (1)")
    assert cn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1
    cn.close()


def test_unidad_trabajo_rollback_sin_escrituras_parciales(tmp_path):
    cn = abrir_conexion(tmp_path / "t.db")
    cn.execute("CREATE TABLE t (x)")
    with pytest.raises(RuntimeError):
        with UnidadTrabajo(cn) as u:
            u.execute("INSERT INTO t VALUES (1)")
            u.execute("INSERT INTO t VALUES (2)")
            raise RuntimeError("falla")
    assert cn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 0
    assert not cn.in_transaction
    cn.close()


def test_rechaza_bd_con_esquema_mas_nuevo(tmp_path):
    ruta = tmp_path / "t.db"
    crear_o_actualizar_bd(ruta)
    cn = sqlite3.connect(ruta)
    cn.execute(f"PRAGMA user_version = {VERSION_ESQUEMA_SOPORTADA + 1}")
    cn.close()
    with pytest.raises(ErrorEsquema):
        crear_o_actualizar_bd(ruta)
    assert _esquema(ruta)[1] == VERSION_ESQUEMA_SOPORTADA + 1


def test_migracion_fallida_no_deja_cambios_de_esa_migracion(tmp_path):
    carpeta = tmp_path / "mig"
    carpeta.mkdir()
    (carpeta / "0001_ok.sql").write_text("CREATE TABLE esquema_migracion (id INTEGER PRIMARY KEY, nombre TEXT, checksum TEXT); CREATE TABLE a (x);", encoding="utf-8")
    (carpeta / "0002_mala.sql").write_text(
        "CREATE TABLE b (x); INSERT INTO no_existe VALUES (1);", encoding="utf-8"
    )
    cn = abrir_conexion(tmp_path / "t.db")
    with pytest.raises(sqlite3.Error):
        _aplicar_migraciones(cn, carpeta)
    tablas = {f[0] for f in cn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "a" in tablas and "b" not in tablas
    cn.close()
