"""Dibujo 2D (módulo C). Solo recibe DrawPrimitives2D: no conoce el 3D.

Este archivo NO importa blockout.scene ni blockout.projection, y no guarda coordenadas del mundo.
Todo lo que dibuja son segmentos que ya vienen en píxeles (u, v), con u a la derecha y v hacia
abajo, que es exactamente el sistema de pygame: por eso no hace falta invertir ningún eje.
"""
from __future__ import annotations

import numpy as np
import pygame

from blockout.core.types import DrawPrimitives2D

BG = (18, 20, 28)
HUD_COLOR = (230, 230, 235)
MAX_PIXEL = 1e5      # docs/INTERFACES.md §6: coordenadas absurdas se descartan, no se dibujan


def draw_primitives(surface: pygame.Surface, prim: DrawPrimitives2D) -> None:
    """Dibuja los segmentos de lejos a cerca (mayor z_cam primero).

    Con solo aristas el orden casi no se nota, pero así lo cercano (la pieza activa, más gruesa)
    queda encima de la rejilla del fondo, y ya queda listo para cuando haya caras rellenas (E5).
    """
    for pts, color, _depth in prim.polygons:                      # vacío en E3
        if np.all(np.abs(pts) < MAX_PIXEL):
            pygame.draw.polygon(surface, color, [tuple(p) for p in pts])
    if len(prim.seg_depths) == 0:
        return
    for k in np.argsort(-prim.seg_depths, kind="stable"):
        (u0, v0), (u1, v1) = prim.segments[k]
        if not np.isfinite(prim.segments[k]).all():
            continue
        if max(abs(u0), abs(v0), abs(u1), abs(v1)) > MAX_PIXEL:
            continue
        pygame.draw.line(surface, prim.seg_colors[k], (u0, v0), (u1, v1),
                         3 if prim.seg_active[k] else 1)


def draw_hud(surface: pygame.Surface, font: pygame.font.Font, lines: list[str]) -> None:
    """Texto en la esquina superior izquierda, una línea debajo de otra."""
    y = 8
    for text in lines:
        surface.blit(font.render(text, True, HUD_COLOR), (10, y))
        y += font.get_linesize()


def render_frame(surface: pygame.Surface, font: pygame.font.Font, prim: DrawPrimitives2D,
                 hud_lines: list[str]) -> None:
    """Un fotograma completo: fondo, primitivas proyectadas y HUD encima."""
    surface.fill(BG)
    draw_primitives(surface, prim)
    draw_hud(surface, font, hud_lines)
