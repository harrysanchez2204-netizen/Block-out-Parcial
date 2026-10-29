"""Prueba de integración del Hito 2: los tres módulos juntos reproducen el ejemplo compartido.

Se sigue un punto de la pieza "de los dedos a la pantalla", que es lo que pide la defensa en vivo:

    X_local --A: M--> X_world --B: [R|t]--> X_cam --B: K y división--> (u, v) --C: dibujo--> píxel

y se compara con la fórmula del enunciado escrita con las matrices del JSON, sin pasar por el
código de ningún módulo:   λ [u v 1]ᵀ = K [R|t] M [X Y Z 1]ᵀ.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import json
from pathlib import Path

import numpy as np
import pygame
import pytest

from blockout.app.renderer import BG, render_frame
from blockout.core.types import Container, Piece, Pose, Scene
from blockout.projection import build_camera, project
from blockout.scene import get_geometry
from blockout.scene.pieces import local_mesh

FIXTURE = Path(__file__).parent / "fixtures" / "shared_example.json"


@pytest.fixture(scope="module")
def ej() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _escena_y_camara(ej):
    pz, c = ej["pieza"], ej["camara"]
    pose = Pose(np.array(pz["pose"]["rotation"], float), np.array(pz["pose"]["position"], float))
    piece = Piece(0, pz["nombre"], tuple(tuple(x) for x in pz["cells"]), pz["pivot_cell"], pose)
    scene = Scene(container=Container(), pieces=(piece,))
    cam = build_camera(c["eye"], c["target"], c["width"], c["height"], c["fov_deg"], c["near"])
    return scene, cam


def _formula_del_enunciado(ej, X_local):
    """λ [u v 1]ᵀ = K [R|t] M X, con K, R, t, M copiadas del JSON. Devuelve (u, v)."""
    c = ej["camara"]
    P = np.array(c["K"]) @ np.hstack([np.array(c["R"]), np.array(c["t"]).reshape(3, 1)])
    x = P @ np.array(ej["pieza"]["M"]) @ np.append(X_local, 1.0)
    return x[:2] / x[2]


def test_cada_arista_de_la_pieza_cae_donde_dice_la_formula(ej):
    scene, cam = _escena_y_camara(ej)
    prim = project(get_geometry(scene), cam)
    v_local, edges, _ = local_mesh(ej["pieza"]["cells"])
    esperados = np.array([[_formula_del_enunciado(ej, v_local[i]),
                           _formula_del_enunciado(ej, v_local[j])] for i, j in edges])
    # la pieza es la activa (scene.active = 0) y está toda delante de la cámara: ninguna arista
    # se recorta y salen en el mismo orden que `edges`
    obtenidos = prim.segments[prim.seg_active]
    assert obtenidos.shape == esperados.shape
    assert np.allclose(obtenidos, esperados, atol=ej["tolerancia"])


def test_mover_la_camara_no_cambia_el_mundo(ej):
    """R11: proyectar desde dos cámaras distintas deja idénticos los vértices del mundo."""
    scene, cam = _escena_y_camara(ej)
    antes = [m.vertices.copy() for m in get_geometry(scene).meshes]
    otra = build_camera((12, -9, 7), (2.5, 2.5, 4), 800, 600, 40)
    project(get_geometry(scene), cam)
    project(get_geometry(scene), otra)
    despues = [m.vertices for m in get_geometry(scene).meshes]
    assert all(np.array_equal(a, b) for a, b in zip(antes, despues))


def test_el_pixel_del_pivote_queda_pintado_en_la_pantalla(ej):
    """C dibuja lo que salió de la cadena: la esquina del cubo pivote no queda en color de fondo."""
    scene, cam = _escena_y_camara(ej)
    pygame.init()
    try:
        surf = pygame.Surface((cam.width, cam.height))
        render_frame(surf, pygame.font.Font(None, 20), project(get_geometry(scene), cam), [])
        esquina = np.array(ej["pieza"]["cells"][ej["pieza"]["pivot_cell"]], float)  # (0,0,0) local
        u, v = np.round(_formula_del_enunciado(ej, esquina)).astype(int)
        assert surf.get_at((int(u), int(v)))[:3] != BG
    finally:
        pygame.quit()
