"""Módulo C — interfaz y animación. Puede importar de core, scene y projection (solo sus funciones de §3).

Exporta las funciones y clases públicas de docs/INTERFACES.md §3.3.
"""
from blockout.app.animation import VictoryAnimation
from blockout.app.demo import DemoRunner
from blockout.app.main import run
from blockout.app.renderer import render_frame

__all__ = ["run", "render_frame", "VictoryAnimation", "DemoRunner"]
