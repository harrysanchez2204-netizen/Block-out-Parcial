"""Dibujo 2D (módulo C). Solo recibe DrawPrimitives2D: no conoce el 3D.

Este archivo NO importa blockout.scene ni blockout.projection, y no guarda coordenadas del mundo.
Todo lo que dibuja ya viene en píxeles (u, v), con u a la derecha y v hacia abajo, que es exactamente
el sistema de pygame: por eso no hace falta invertir ningún eje.

E6: caras y aristas se dibujan en UNA sola lista ordenada de lejos a cerca (algoritmo del pintor).
En E3 se dibujaban todas las caras y después todas las aristas, y con caras rellenas la rejilla de la
pared del fondo, que está DETRÁS de las piezas, quedaba pintada ENCIMA de ellas (ver
docs/img/e6_caras.png contra la nota de E5). Con una sola lista ordenada, lo cercano tapa lo lejano.
"""
from __future__ import annotations

import numpy as np
import pygame

from blockout.core.types import DrawPrimitives2D

BG = (18, 20, 28)
HUD_COLOR = (230, 230, 235)
HUD_WARN_COLOR = (255, 200, 90)
MAX_PIXEL = 1e5      # docs/INTERFACES.md §6: coordenadas absurdas se descartan, no se dibujan
FACE_SHADE = 0.55    # las caras van más oscuras que su borde para que se distingan las aristas

_FACE, _EDGE = 0, 1  # ante igual profundidad, primero la cara y después la arista (queda visible)


def _ok(pts) -> bool:
    pts = np.asarray(pts, dtype=float)
    return bool(np.isfinite(pts).all() and np.abs(pts).max() <= MAX_PIXEL)


def draw_order(prim: DrawPrimitives2D) -> list[tuple[int, int]]:
    """Orden de dibujo: lista de (tipo, índice), de la MAYOR profundidad z_cam a la menor.

    Mezcla caras (prim.polygons) y aristas (prim.segments) en una sola secuencia. El orden es
    estable y determinista: a igual profundidad va primero la cara, y entre dos del mismo tipo se
    respeta el orden en que llegaron.
    """
    items = [(-float(d), _FACE, k) for k, (_, _, d) in enumerate(prim.polygons)]
    items += [(-float(d), _EDGE, k) for k, d in enumerate(prim.seg_depths)]
    items.sort()
    return [(kind, k) for _, kind, k in items]


def draw_primitives(surface: pygame.Surface, prim: DrawPrimitives2D) -> None:
    """Dibuja caras y aristas de lejos a cerca. La pieza activa se dibuja con trazo grueso."""
    for kind, k in draw_order(prim):
        if kind == _FACE:
            pts, color, _ = prim.polygons[k]
            if not _ok(pts):
                continue
            poly = [tuple(p) for p in pts]
            pygame.draw.polygon(surface, tuple(int(c * FACE_SHADE) for c in color), poly)
            pygame.draw.polygon(surface, color, poly, 1)          # borde de la cara
        else:
            seg = prim.segments[k]
            if not _ok(seg):
                continue
            (u0, v0), (u1, v1) = seg
            pygame.draw.line(surface, prim.seg_colors[k], (u0, v0), (u1, v1),
                             3 if prim.seg_active[k] else 1)


def draw_hud(surface: pygame.Surface, font: pygame.font.Font, lines: list[str]) -> None:
    """Texto en la esquina superior izquierda. Las líneas que empiezan con '!' van resaltadas."""
    y = 8
    for text in lines:
        color = HUD_COLOR
        if text.startswith("!"):
            text, color = text[1:].strip(), HUD_WARN_COLOR
        if text:
            surface.blit(font.render(text, True, color), (10, y))
        y += font.get_linesize()


def render_frame(surface: pygame.Surface, font: pygame.font.Font, prim: DrawPrimitives2D,
                 hud_lines: list[str]) -> None:
    """Un fotograma completo: fondo, primitivas proyectadas y HUD encima."""
    surface.fill(BG)
    draw_primitives(surface, prim)
    draw_hud(surface, font, hud_lines)
