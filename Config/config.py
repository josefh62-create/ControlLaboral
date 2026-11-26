# -*- coding: utf-8 -*-
# Config/config.py
"""Configuracion de la aplicacion: nombre, version y rutas.

No contiene valores laborales (topes, tolerancias, etc.): esos viven en la BD.
Las funciones son puras (reciben entorno y rutas) para poder probarlas.
"""

import os
from pathlib import Path

NOMBRE_APP = "ControlLaboral"
VERSION_APP = "0.1.0"

# Ultima migracion que esta version de la app conoce (PRAGMA user_version).
VERSION_ESQUEMA_SOPORTADA = 1

VARIABLE_DATOS = "CONTROLLABORAL_DATA"
NOMBRE_BD = "controllaboral.db"

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent


def _es_subruta(ruta: Path, base: Path) -> bool:
    try:
        ruta.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def resolver_carpeta_datos(
    entorno: dict | None = None, raiz: Path | None = None
) -> Path:
    """Devuelve la carpeta de datos segun el entorno.

    1. CONTROLLABORAL_DATA, si esta definida.
    2. Copia instalada bajo %LOCALAPPDATA%\Programs\MisApps\:
       %LOCALAPPDATA%\MisApps\ControlLaboral\data\.
    3. Desarrollo: <repositorio>/data/.
    """
    entorno = os.environ if entorno is None else entorno
    raiz = RAIZ_PROYECTO if raiz is None else Path(raiz)

    explicita = entorno.get(VARIABLE_DATOS)
    if explicita:
        return Path(explicita)

    local = entorno.get("LOCALAPPDATA")
    if local:
        local = Path(local)
        if _es_subruta(raiz, local / "Programs" / "MisApps"):
            return local / "MisApps" / NOMBRE_APP / "data"

    return raiz / "data"


def ruta_bd(entorno: dict | None = None, raiz: Path | None = None) -> Path:
    """Ruta completa del archivo de base de datos."""
    return resolver_carpeta_datos(entorno, raiz) / NOMBRE_BD
