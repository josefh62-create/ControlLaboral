from pathlib import Path

from Config import config


def test_variable_de_entorno_tiene_prioridad(tmp_path):
    entorno = {"CONTROLLABORAL_DATA": str(tmp_path / "x"), "LOCALAPPDATA": str(tmp_path)}
    assert config.resolver_carpeta_datos(entorno, tmp_path / "repo") == tmp_path / "x"


def test_copia_instalada_usa_localappdata(tmp_path):
    raiz = tmp_path / "Programs" / "MisApps" / "ControlLaboral"
    raiz.mkdir(parents=True)
    esperado = tmp_path / "MisApps" / "ControlLaboral" / "data"
    assert config.resolver_carpeta_datos({"LOCALAPPDATA": str(tmp_path)}, raiz) == esperado


def test_desarrollo_usa_data_del_repo(tmp_path):
    raiz = tmp_path / "otro" / "ControlLaboral"
    raiz.mkdir(parents=True)
    assert config.resolver_carpeta_datos({"LOCALAPPDATA": str(tmp_path)}, raiz) == raiz / "data"
    assert config.resolver_carpeta_datos({}, raiz) == raiz / "data"


def test_ruta_bd_agrega_nombre_de_archivo(tmp_path):
    ruta = config.ruta_bd({"CONTROLLABORAL_DATA": str(tmp_path)})
    assert ruta == Path(tmp_path) / config.NOMBRE_BD


def test_variable_relativa_se_vuelve_absoluta():
    ruta = config.resolver_carpeta_datos({"CONTROLLABORAL_DATA": "datos_rel"})
    assert ruta.is_absolute()
