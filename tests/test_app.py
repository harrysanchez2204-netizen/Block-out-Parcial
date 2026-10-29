"""Pruebas del módulo C (E3): dibujo de primitivas, HUD y bucle sin ventana.

Las primitivas se escriben a mano: el renderizador no debe necesitar ni la escena ni la cámara.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import ast
from pathlib import Path

import numpy as np
import pygame
import pytest

from blockout.app.renderer import BG, draw_primitives, render_frame
from blockout.core.types import DrawPrimitives2D

APP = Path(__file__).parents[1] / "src" / "blockout" / "app"


@pytest.fixture()
def superficie():
    pygame.init()
    s = pygame.Surface((100, 100))
    s.fill(BG)
    yield s
    pygame.quit()


def _prims(segs, colores, activos=None, profundidades=None):
    segs = np.asarray(segs, float).reshape(-1, 2, 2)
    n = len(segs)
    return DrawPrimitives2D(segments=segs, seg_colors=colores,
                            seg_depths=np.asarray(profundidades if profundidades else [1.0] * n),
                            seg_active=np.asarray(activos if activos else [False] * n, bool))


def test_dibuja_un_segmento_en_los_pixeles_que_dice(superficie):
    draw_primitives(superficie, _prims([[[10, 50], [90, 50]]], [(255, 0, 0)]))
    assert superficie.get_at((50, 50))[:3] == (255, 0, 0)
    assert superficie.get_at((50, 20))[:3] == BG                # el resto queda intacto


def test_la_pieza_activa_se_dibuja_mas_gruesa(superficie):
    draw_primitives(superficie, _prims([[[10, 30], [90, 30]], [[10, 70], [90, 70]]],
                                       [(0, 255, 0), (0, 0, 255)], activos=[True, False]))
    assert superficie.get_at((50, 31))[:3] == (0, 255, 0)       # grosor 3
    assert superficie.get_at((50, 71))[:3] == BG                # grosor 1


def test_lo_cercano_queda_encima(superficie):
    """Dos segmentos en el mismo lugar: gana el de menor z_cam (se dibuja de último)."""
    draw_primitives(superficie, _prims([[[10, 50], [90, 50]], [[10, 50], [90, 50]]],
                                       [(255, 0, 0), (0, 0, 255)], profundidades=[2.0, 9.0]))
    assert superficie.get_at((50, 50))[:3] == (255, 0, 0)


def test_coordenadas_absurdas_y_listas_vacias_no_fallan(superficie):
    draw_primitives(superficie, _prims([[[1e7, 0], [50, 50]], [[np.nan, 1], [2, 3]]],
                                       [(255, 0, 0), (255, 0, 0)]))
    assert superficie.get_at((50, 50))[:3] == BG               # descartados, no dibujados
    draw_primitives(superficie, _prims(np.zeros((0, 2, 2)), []))


def test_render_frame_pinta_el_hud(superficie):
    font = pygame.font.Font(None, 24)
    render_frame(superficie, font, _prims(np.zeros((0, 2, 2)), []), ["Pieza activa: L"])
    zona = pygame.surfarray.array3d(superficie)[5:95, 5:30]
    assert (zona != np.array(BG)).any()


def test_la_app_corre_sin_ventana():
    from blockout.app.main import run
    run(max_frames=5)
    run(demo=True, max_frames=2)


def test_el_renderizador_no_importa_la_escena_ni_la_proyeccion():
    """R12: la interfaz solo recibe primitivas 2D. Se revisa el código fuente, no la ejecución."""
    arbol = ast.parse((APP / "renderer.py").read_text(encoding="utf-8"))
    modulos = {n.module for n in ast.walk(arbol) if isinstance(n, ast.ImportFrom)}
    modulos |= {a.name for n in ast.walk(arbol) if isinstance(n, ast.Import) for a in n.names}
    assert not any(m and (m.startswith("blockout.scene") or m.startswith("blockout.projection"))
                   for m in modulos)
