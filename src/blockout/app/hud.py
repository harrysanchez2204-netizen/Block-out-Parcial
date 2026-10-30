"""Textos del HUD (módulo C): pieza activa, estado, cámara y ayuda de teclas (R21).

Función pura: recibe el estado y devuelve líneas de texto. No dibuja (eso es renderer.draw_hud) y no
modifica nada. La aplicación LEE la escena y la cámara para mostrarlas (docs/INTERFACES.md §4).
"""
from __future__ import annotations

from blockout.app.input_map import HELP_LINES
from blockout.core.types import Scene


def build_hud_lines(scene: Scene, camera, fill_faces: bool, message: str = "",
                    demo: bool = False, show_help: bool = True, banner: str = "") -> list[str]:
    """(escena, OrbitCamera, caras sí/no, último aviso, …) -> líneas del HUD, de arriba hacia abajo.

    Arriba van el estado (cortas, para no llegar al borde superior del contenedor) y debajo la ayuda
    en columna angosta. Con show_help=False solo queda el estado. `banner` es una línea opcional
    (resaltada si empieza con "!") para el avance de la demo o la animación de victoria.
    """
    if scene.pieces:
        p = scene.pieces[scene.active]
        pieza = f"Pieza activa: {scene.active + 1}/{len(scene.pieces)} {p.name}"
    else:
        pieza = "Pieza activa: -"
    estado = {"playing": "en juego", "victory": "VICTORIA"}.get(scene.status, scene.status)
    lines = [
        f"{pieza}   Estado: {estado}" + ("   [DEMO]" if demo else ""),
        (f"Camara: az={camera.azimuth:5.1f}  el={camera.elevation:5.1f}  "
         f"dist={camera.distance:4.1f}  fov={camera.fov:5.1f}   "
         f"Caras: {'si' if fill_faces else 'no'}"),
        message,                       # vacío si no hay aviso: deja la línea en blanco, sin saltos
        banner,
        "",
    ]
    return lines + (HELP_LINES if show_help else [])
