# -*- coding: utf-8 -*-
"""Dominio PURO: reglas legales, calendario y motor de jornada.

Regla de pureza (doc. 03 secciones 3 y 5, verificada por tests/arquitectura):
solo biblioteca estandar; sin PySide6, sqlite3, Database, Modelos, Vistas,
Controladores, Servicios ni Repositorios; sin leer el reloj del sistema
(la fecha entra por un puerto ProveedorFecha).
"""
