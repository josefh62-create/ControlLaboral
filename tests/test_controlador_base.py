import Controladores.controlador_base as modulo
from Controladores.controlador_base import ControladorBase

HOOKS = ("inicializar_modulo", "nuevo", "guardar", "buscar", "cancelar", "refrescar_datos")


def test_hooks_de_barra_global_son_invocables():
    c = ControladorBase(vista="v", modelo="m")
    assert (c.vista, c.modelo, c.main) == ("v", "m", None)
    for hook in HOOKS:
        assert getattr(c, hook)() is None


def test_hooks_sobrescribibles():
    class Mio(ControladorBase):
        def guardar(self):
            return "guardado"

    assert Mio().guardar() == "guardado"
    assert Mio().nuevo() is None


def test_modulo_no_depende_de_qt():
    assert not hasattr(modulo, "QObject")
