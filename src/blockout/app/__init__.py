"""Módulo C — interfaz y animación. Puede importar de core, scene y projection (solo sus funciones de §3).

Exporta las funciones públicas de docs/INTERFACES.md §3.3. VictoryAnimation y DemoRunner llegan en E9.
"""
from blockout.app.main import run
from blockout.app.renderer import render_frame

__all__ = ["run", "render_frame"]
