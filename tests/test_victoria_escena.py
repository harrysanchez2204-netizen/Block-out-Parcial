"""Pruebas del módulo A en E9: la escena durante la animación de victoria.

La animación es de C, pero las poses que produce entran a la escena de A por `set_pose`. Aquí se comprueba,
fotograma por fotograma, que la geometría del mundo sigue siendo válida: las piezas no se deforman, giran
alrededor de su pivote y no dan saltos, y al terminar todo queda exactamente como estaba.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np
import pytest

from blockout.app.animation import DURATION, VictoryAnimation
from blockout.app.demo import FPS
from blockout.core.types import Action
from blockout.scene import apply_action, create_scene, get_geometry, model_matrix

FRAMES = int(round(DURATION * FPS))


def _frames(scene):
    """Recorre la animación entera aplicando sus acciones a la escena: (escena, t) por fotograma."""
    anim = VictoryAnimation(scene)
    out = []
    while not anim.finished:
        for a in anim.step(1.0 / FPS):
            scene = apply_action(scene, a)
        out.append((scene, anim.t))
    return out


@pytest.fixture(scope="module")
def recorrido():
    base = create_scene()
    return base, _frames(base)


def _dist(v):
    return np.linalg.norm(v[:, None] - v[None], axis=-1)


def test_cada_pieza_sigue_rigida_en_todos_los_fotogramas(recorrido):
    """Las distancias entre los vértices de cada pieza no cambian: la pieza se mueve, no se deforma."""
    base, frames = recorrido
    d0 = [_dist(m.vertices) for m in get_geometry(base).meshes[1:]]
    for k, (sc, _) in enumerate(frames):
        for i, m in enumerate(get_geometry(sc).meshes[1:]):
            assert np.allclose(_dist(m.vertices), d0[i], atol=1e-9), (k, i)


def test_las_rotaciones_son_propias_en_todos_los_fotogramas(recorrido):
    _, frames = recorrido
    for k, (sc, _) in enumerate(frames):
        for p in sc.pieces:
            R = p.pose.rotation
            assert np.allclose(R @ R.T, np.eye(3), atol=1e-12) and np.isclose(np.linalg.det(R), 1.0), k


def test_el_pivote_es_el_centro_de_giro(recorrido):
    """M lleva el pivote local a Pose.position también en mitad de la animación."""
    _, frames = recorrido
    sc, _ = frames[FRAMES // 3]
    for p in sc.pieces:
        assert np.allclose((model_matrix(p) @ np.append(p.pivot_local, 1.0))[:3], p.pose.position)


def test_no_hay_saltos_ni_al_empezar_ni_durante(recorrido):
    """Entre dos fotogramas seguidos ningún vértice se mueve más de 0.3 cubos, tampoco en el primero."""
    base, frames = recorrido
    prev = [m.vertices for m in get_geometry(base).meshes[1:]]
    peor = 0.0
    for sc, _ in frames:
        cur = [m.vertices for m in get_geometry(sc).meshes[1:]]
        peor = max(peor, max(np.linalg.norm(a - b, axis=1).max() for a, b in zip(prev, cur)))
        prev = cur
    assert peor < 0.3, peor


def test_las_piezas_si_se_mueven_en_3d(recorrido):
    """A mitad de la animación todas las piezas están lejos de su lugar, por fuera de las paredes del
    pozo, y más cerca de su altura media (las de arriba bajan y las de abajo suben)."""
    base, frames = recorrido
    sc, _ = frames[FRAMES // 2]
    W, D, H = base.container.size
    for p0, p in zip(base.pieces, sc.pieces):
        assert np.linalg.norm(p.pose.position - p0.pose.position) > 1.0
        x, y, z = p.pose.position
        assert not (0 <= x <= W and 0 <= y <= D), "a mitad de la animación la pieza sale del pozo"
        assert abs(z - H / 2) < abs(p0.pose.position[2] - H / 2) + 1e-9


def test_al_terminar_la_escena_es_exactamente_la_de_antes(recorrido):
    base, frames = recorrido
    final, t = frames[-1]
    assert len(frames) == FRAMES and np.isclose(t, DURATION)
    assert final.status == "playing" and final.active == base.active
    for a, b in zip(final.pieces, base.pieces):
        assert np.array_equal(a.pose.position, b.pose.position)
        assert np.array_equal(a.pose.rotation, b.pose.rotation)
    for a, b in zip(get_geometry(final).meshes, get_geometry(base).meshes):
        assert np.array_equal(a.vertices, b.vertices)


def test_durante_la_victoria_el_estado_es_victory(recorrido):
    _, frames = recorrido
    assert all(sc.status == "victory" for sc, _ in frames[:-1])


def test_la_escena_de_partida_no_se_modifica():
    """La animación guarda la escena inicial y nunca la cambia (las escenas son inmutables)."""
    base = create_scene()
    pos = [p.pose.position.copy() for p in base.pieces]
    _frames(base)
    assert all(np.array_equal(a, p.pose.position) for a, p in zip(pos, base.pieces))


def test_funciona_con_piezas_en_cualquier_lugar():
    """Una pieza con el pivote justo sobre el eje del pozo no tiene "dirección hacia afuera": no falla."""
    sc = create_scene()
    p = sc.pieces[0]
    eje = np.array([2.5, 2.5, p.pose.position[2]])
    sc = apply_action(sc, Action("set_pose", piece=0, pose=type(p.pose)(p.pose.rotation, eje)))
    frames = _frames(sc)
    assert all(np.isfinite(f.pieces[0].pose.position).all() for f, _ in frames)


def test_la_malla_local_se_reutiliza_y_no_se_puede_danar():
    """E9: la malla de cada forma se construye una vez. Es de solo lectura para que nadie la dañe."""
    from blockout.scene.pieces import local_mesh
    cells = [(0, 0, 0), (1, 0, 0), (2, 0, 0), (0, 1, 0)]
    a = local_mesh(cells)
    b = local_mesh(tuple(tuple(c) for c in cells))
    assert all(x is y for x, y in zip(a, b))                              # misma malla, no una copia
    with pytest.raises(ValueError):
        a[0][0, 0] = 99.0
    sc = create_scene()
    g1, g2 = get_geometry(sc), get_geometry(sc)
    assert all(np.array_equal(m1.vertices, m2.vertices) for m1, m2 in zip(g1.meshes, g2.meshes))
