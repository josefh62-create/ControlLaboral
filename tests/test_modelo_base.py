import pytest

from Database.crear_bd import crear_o_actualizar_bd
from Modelos.modelo_base import ModeloBase, OperacionNoPermitida


class ModeloPrueba(ModeloBase):
    tabla = "prueba"


class ModeloSoloInsercion(ModeloBase):
    tabla = "prueba"
    solo_insercion = True


@pytest.fixture
def ruta(tmp_path):
    ruta = tmp_path / "t.db"
    crear_o_actualizar_bd(ruta)
    ModeloPrueba(ruta).ejecutar(
        "CREATE TABLE prueba (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE)"
    )
    return ruta


def test_crud_ida_y_vuelta(ruta):
    m = ModeloPrueba(ruta)
    id_ = m.insertar({"nombre": "Ana"})
    assert m.obtener(id_) == {"id": id_, "nombre": "Ana"}
    assert m.actualizar(id_, {"nombre": "Beto"}) == 1
    assert m.listar() == [{"id": id_, "nombre": "Beto"}]
    assert m.eliminar(id_) == 1
    assert m.obtener(id_) is None


def test_valor_con_comilla_va_parametrizado(ruta):
    m = ModeloPrueba(ruta)
    raro = "O'Brien'); DROP TABLE prueba;--"
    id_ = m.insertar({"nombre": raro})
    assert m.obtener(id_)["nombre"] == raro
    assert m.consultar("SELECT * FROM prueba WHERE nombre = ?", (raro,))
    assert len(m.listar()) == 1  # la tabla sigue existiendo


def test_identificador_invalido_rechazado(ruta):
    with pytest.raises(ValueError):
        ModeloPrueba(ruta).insertar({"nombre; DROP TABLE prueba": "x"})


def test_solo_insercion_rechaza_actualizar_y_eliminar(ruta):
    m = ModeloSoloInsercion(ruta)
    id_ = m.insertar({"nombre": "Ana"})
    with pytest.raises(OperacionNoPermitida):
        m.actualizar(id_, {"nombre": "X"})
    with pytest.raises(OperacionNoPermitida):
        m.eliminar(id_)
    assert m.obtener(id_)["nombre"] == "Ana"


def test_error_de_escritura_hace_rollback(ruta):
    m = ModeloPrueba(ruta)
    m.insertar({"nombre": "Ana"})
    with pytest.raises(Exception):
        m.insertar({"nombre": "Ana"})  # viola UNIQUE
    assert len(m.listar()) == 1


def test_ejecutar_multifila_con_error_no_deja_filas(ruta):
    m = ModeloPrueba(ruta)
    with pytest.raises(Exception):
        # la segunda fila viola NOT NULL: la primera debe revertirse
        m.ejecutar("INSERT INTO prueba (nombre) VALUES (?), (NULL)", ("Ana",))
    assert m.listar() == []


def test_resultado_estandar_y_requerido():
    ok = ModeloBase._resultado_ok(5)
    assert ok == {"exito": True, "resultado": 5, "mensaje": "", "campo": ""}
    err = ModeloBase._resultado_error("mal", "nombre")
    assert err["exito"] is False and err["campo"] == "nombre"
    m = ModeloBase("x.db")
    assert m._requerido("  ", "centro_trabajo")["campo"] == "centro_trabajo"
    assert m._requerido("a", "n") is None
