"""Pruebas del módulo C en E9: animación de victoria (R22) y modo demostración (R23).

Todo corre sin ventana: la demo se avanza con `advance_frame`, que es lo mismo que hace el bucle real en
cada fotograma, y las teclas se simulan con eventos de pygame fabricados a mano.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import ast
import hashlib
from pathlib import Path

import numpy as np
import pygame
import pytest

from blockout.app.animation import DURATION, VictoryAnimation
from blockout.app.demo import FPS, VICTORY_START, DemoRunner, at, build_script
from blockout.app.input_map import translate_event
from blockout.app.main import (ANIMATING_MSG, AppState, advance_frame, apply_command,
                               frame_primitives, new_state)
from blockout.core.types import Action
from blockout.projection import OrbitCamera
from blockout.scene import apply_action, create_scene, get_geometry

APP = Path(__file__).parents[1] / "src" / "blockout" / "app"
VICTORY_FRAMES = at(DURATION)


def _key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0)


def _press(state, *keys):
    for k in keys:
        for cmd in translate_event(_key(k)):
            apply_command(state, cmd)


def _fingerprint(state) -> str:
    """Huella del estado visible: poses de todas las piezas, pieza activa, estado y cámara."""
    h = hashlib.sha256()
    for p in state.scene.pieces:
        h.update(np.round(p.pose.position, 12).tobytes())
        h.update(np.round(p.pose.rotation, 12).tobytes())
    c = state.camera
    h.update(repr((state.scene.active, state.scene.status, state.fill_faces,
                   round(c.azimuth, 9), round(c.elevation, 9), round(c.distance, 9),
                   round(c.fov, 9))).encode())
    return h.hexdigest()


def _run_demo():
    """Corre la demo completa sin ventana. Devuelve (estado final, huella de cada fotograma)."""
    st = new_state(demo=True)
    prints = []
    while not st.demo.finished:
        advance_frame(st)
        prints.append(_fingerprint(st))
    return st, prints


# =========================================================================== R23 · demo determinista

def test_la_demo_es_determinista():
    """Dos corridas completas: el mismo estado en CADA fotograma, no solo al final."""
    st1, f1 = _run_demo()
    st2, f2 = _run_demo()
    assert len(f1) == len(f2) == DemoRunner().total_frames
    assert f1 == f2
    for a, b in zip(st1.scene.pieces, st2.scene.pieces):
        assert np.array_equal(a.pose.position, b.pose.position)
        assert np.array_equal(a.pose.rotation, b.pose.rotation)


def test_la_demo_muestra_todo_lo_que_pide_el_enunciado():
    """Escena, transformaciones de piezas (también de las no planarias), cámara y victoria."""
    kinds = {k for _, k, _ in build_script()}
    assert {"action", "camera", "victory"} <= kinds
    acciones = [d for _, k, d in build_script() if k == "action"]
    assert {"translate", "rotate", "select"} <= {a.kind for a in acciones}
    assert {a.axis for a in acciones if a.kind == "rotate"} == {0, 1, 2}           # tres ejes
    elegidas = {a.piece for a in acciones if a.kind == "select"}
    assert {4, 5} <= elegidas                                                        # Trípode y Tornillo
    camara = {d.kind for _, k, d in build_script() if k == "camera"}
    assert {"orbit", "zoom", "fov", "reset"} <= camara
    assert build_script()[0][0] >= at(1.0)                                           # arranca quieta


def test_ninguna_accion_del_guion_es_rechazada():
    """Si un movimiento del guion se saliera del contenedor, la demo no mostraría nada en ese momento."""
    sc = create_scene()
    for _, kind, data in build_script():
        if kind == "action" and data.kind in ("translate", "rotate"):
            nuevo = apply_action(sc, data)
            assert nuevo is not sc, data
            sc = nuevo
        elif kind == "action":
            sc = apply_action(sc, data)


def test_la_demo_pasa_por_la_victoria_y_termina_jugando():
    st = new_state(demo=True)
    estados = set()
    while not st.demo.finished:
        advance_frame(st)
        estados.add(st.scene.status)
    assert estados == {"playing", "victory"}
    assert st.scene.status == "playing" and st.victory is None


def test_la_camara_orbita_durante_la_victoria_de_la_demo():
    st = new_state(demo=True)
    for _ in range(at(VICTORY_START) + at(DURATION / 2)):
        advance_frame(st)
    assert st.animating
    az = st.camera.azimuth
    advance_frame(st)
    assert st.camera.azimuth != az


# =========================================================================== R22 · victoria

def test_v_lanza_la_victoria_y_al_terminar_todo_vuelve():
    st = AppState()
    poses = [(p.pose.position.copy(), p.pose.rotation.copy()) for p in st.scene.pieces]
    _press(st, pygame.K_v)
    assert st.animating
    for _ in range(VICTORY_FRAMES):
        advance_frame(st)
    assert st.victory is None and st.scene.status == "playing"
    for (pos, R), p in zip(poses, st.scene.pieces):
        assert np.array_equal(p.pose.position, pos) and np.array_equal(p.pose.rotation, R)


def test_la_victoria_dura_lo_que_dice():
    st = AppState()
    _press(st, pygame.K_v)
    n = 0
    while st.victory is not None:
        advance_frame(st)
        n += 1
    assert n == VICTORY_FRAMES == DURATION * FPS


def test_la_victoria_cambia_poses_del_mundo_y_no_la_pantalla():
    """El enunciado (§4): la animación modifica poses 3D por la escena, no coordenadas de pantalla.
    A mitad de la animación cambian los VÉRTICES DEL MUNDO; con la misma cámara, las primitivas
    proyectadas cambian solo porque cambió el mundo."""
    st = AppState()
    v0 = [m.vertices.copy() for m in get_geometry(st.scene).meshes]
    p0 = frame_primitives(st, 640, 480).segments.copy()
    _press(st, pygame.K_v)
    for _ in range(VICTORY_FRAMES // 2):
        advance_frame(st)
    v1 = [m.vertices for m in get_geometry(st.scene).meshes]
    assert np.array_equal(v0[0], v1[0])                                   # el contenedor no se mueve
    assert all(not np.allclose(a, b) for a, b in zip(v0[1:], v1[1:]))     # todas las piezas sí
    assert st.scene.status == "victory"
    p1 = frame_primitives(st, 640, 480).segments
    assert p0.shape != p1.shape or not np.allclose(p0, p1)


def test_la_animacion_no_toca_pantalla_ni_camara():
    """animation.py no importa la proyección, ni pygame, ni el renderizador: solo produce Actions."""
    arbol = ast.parse((APP / "animation.py").read_text(encoding="utf-8"))
    mods = {n.module for n in ast.walk(arbol) if isinstance(n, ast.ImportFrom)}
    mods |= {a.name for n in ast.walk(arbol) if isinstance(n, ast.Import) for a in n.names}
    assert not any(m and (m.startswith("pygame") or m.startswith("blockout.projection")
                          or m.startswith("blockout.app")) for m in mods), mods
    acts = VictoryAnimation(create_scene()).step(0.5)
    assert {a.kind for a in acts} == {"set_status", "set_pose"}


def test_la_camara_responde_durante_la_victoria_y_no_altera_la_animacion():
    """Mover la cámara durante la victoria cambia la cámara, pero las poses en cada fotograma son
    exactamente las mismas que sin moverla (la animación es función solo del tiempo)."""
    quieta, movida = AppState(), AppState()
    for st in (quieta, movida):
        _press(st, pygame.K_v)
    for k in range(VICTORY_FRAMES // 3):
        if k % 5 == 0:
            _press(movida, pygame.K_LEFT, pygame.K_UP, pygame.K_PAGEUP, pygame.K_z)
        advance_frame(quieta)
        advance_frame(movida)
        for a, b in zip(quieta.scene.pieces, movida.scene.pieces):
            assert np.array_equal(a.pose.position, b.pose.position)
    assert movida.camera.azimuth != quieta.camera.azimuth
    assert movida.camera.fov < quieta.camera.fov


def test_las_piezas_no_responden_durante_la_victoria():
    st = AppState()
    _press(st, pygame.K_v)
    advance_frame(st)
    antes = [p.pose.position.copy() for p in st.scene.pieces]
    _press(st, pygame.K_f, pygame.K_i, pygame.K_TAB)
    assert st.message == ANIMATING_MSG
    assert all(np.array_equal(a, p.pose.position) for a, p in zip(antes, st.scene.pieces))
    _press(st, pygame.K_v)                                                # V otra vez no la reinicia
    assert st.victory.t > 0


def test_la_victoria_parte_de_la_escena_actual():
    """Si el usuario movió piezas antes de V, la animación sale de ahí y vuelve ahí."""
    st = AppState()
    _press(st, pygame.K_f, pygame.K_f, pygame.K_u)
    movida = [p.pose.position.copy() for p in st.scene.pieces]
    _press(st, pygame.K_v)
    for _ in range(VICTORY_FRAMES):
        advance_frame(st)
    assert all(np.array_equal(a, p.pose.position) for a, p in zip(movida, st.scene.pieces))


def test_el_hud_muestra_victoria_y_demo():
    from blockout.app.main import banner_text
    st = new_state(demo=True)
    advance_frame(st)
    assert "DEMO" in banner_text(st)
    while not st.animating:
        advance_frame(st)
    assert "VICTORIA" in banner_text(st)
    while not st.demo.finished:
        advance_frame(st)
    assert "Enter" in banner_text(st)


# =========================================================================== sin reloj ni azar

FORBIDDEN = {("time", "time"), ("time", "perf_counter"), ("time", "monotonic"), ("datetime", "now")}


@pytest.mark.parametrize("archivo", ["animation.py", "demo.py", "main.py"])
def test_no_se_usa_el_reloj_ni_el_azar(archivo):
    """R23: el resultado no puede depender del reloj real ni de números al azar."""
    arbol = ast.parse((APP / archivo).read_text(encoding="utf-8"))
    for n in ast.walk(arbol):
        if isinstance(n, ast.Import):
            assert not any(a.name in ("random", "time", "datetime") for a in n.names), archivo
        if isinstance(n, ast.ImportFrom):
            assert n.module not in ("random", "time", "datetime"), archivo
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
            assert (n.value.id, n.attr) not in FORBIDDEN, (archivo, n.value.id, n.attr)


# =========================================================================== la aplicación corre

def test_la_aplicacion_corre_con_y_sin_demo():
    from blockout.app.main import run
    run(max_frames=5)
    run(demo=True, max_frames=30)
    # La victoria se dibuja con frame_primitives (sin el reloj de 60 fps, que haría lenta la prueba)
    st = new_state(demo=True)
    for _ in range(at(VICTORY_START) + at(DURATION / 2)):
        advance_frame(st)
    assert st.fill_faces                                  # la demo las activó con G a los 7 s
    pygame.init()
    try:
        from blockout.app.renderer import render_frame
        s = pygame.Surface((640, 480))
        prim = frame_primitives(st, 640, 480)
        render_frame(s, pygame.font.Font(None, 20), prim, ["VICTORIA"])
        assert st.animating and len(prim.polygons) > 0
        assert np.isfinite(prim.segments).all()
    finally:
        pygame.quit()


def test_en_la_demo_se_ignora_la_entrada_salvo_lo_permitido():
    from blockout.app.main import DEMO_ALLOWED
    st = new_state(demo=True)
    drag = pygame.event.Event(pygame.MOUSEMOTION, rel=(80, 0), buttons=(1, 0, 0), pos=(0, 0))
    for ev in (drag, _key(pygame.K_f), _key(pygame.K_LEFT)):
        for cmd in translate_event(ev):
            assert cmd.kind not in DEMO_ALLOWED                            # el bucle las descarta
    assert {"quit", "help", "faces"} == set(DEMO_ALLOWED)
    assert isinstance(OrbitCamera().azimuth, float) and st.demo.frame == 0
