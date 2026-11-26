import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

import main  # noqa: E402


def test_arranque_construye_ventana_sin_exec(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTROLLABORAL_DATA", str(tmp_path / "datos"))
    app = QApplication.instance() or QApplication([])
    vista, controlador = main.construir_ventana(app)
    assert (tmp_path / "datos" / "controllaboral.db").is_file()
    assert controlador.modulos_disponibles == {}
    vista.close()
