"""Pruebas del módulo C en E6: entrada, órdenes, HUD y dibujo con caras (R04, R07–R10, R16, R21).

Todo corre sin ventana: los eventos se fabrican a mano con pygame.event.Event y las órdenes se
aplican a un AppState. No hace falta pulsar nada para comprobar qué hace cada tecla.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pathlib import Path

import numpy as np
import pygame
import pytest

from blockout.app.hud import build_hud_lines
from blockout.app.input_map import (APP_KEYS, CAMERA_KEYS, HELP_LINES, PIECE_KEYS, Command,
                                    translate_event)
from blockout.app.main import BLOCKED_MSG, AppState, apply_command, frame_primitives
from blockout.app.renderer import BG, FACE_SHADE, draw_order, draw_primitives
from blockout.core.types import Action, DrawPrimitives2D
from blockout.scene import get_geometry

README = Path(__file__).parents[1] / "README.md"


def _key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0)


def _run(state, *events):
    for ev in events:
        for cmd in translate_event(ev):
            apply_command(state, cmd)
    return state


# =========================================================================== mapa de entrada

@pytest.mark.parametrize("k,kind,campo,valor", [
    (pygame.K_d, "translate", "delta", (1, 0, 0)), (pygame.K_a, "translate", "delta", (-1, 0, 0)),
    (pygame.K_w, "translate", "delta", (0, 1, 0)), (pygame.K_s, "translate", "delta", (0, -1, 0)),
    (pygame.K_r, "translate", "delta", (0, 0, 1)), (pygame.K_f, "translate", "delta", (0, 0, -1)),
    (pygame.K_i, "rotate", "axis", 0), (pygame.K_j, "rotate", "axis", 1), (pygame.K_u, "rotate", "axis", 2),
    (pygame.K_TAB, "select_next", "piece", None), (pygame.K_3, "select", "piece", 2)])
def test_teclas_de_pieza_producen_la_accion_correcta(k, kind, campo, valor):
    (cmd,) = translate_event(_key(k))
    assert cmd.kind == "action" and cmd.action.kind == kind
    assert getattr(cmd.action, campo) == valor


def test_cada_rotacion_tiene_su_inversa():
    for a, b in [(pygame.K_i, pygame.K_k), (pygame.K_j, pygame.K_l), (pygame.K_u, pygame.K_o)]:
        ra, rb = PIECE_KEYS[a], PIECE_KEYS[b]
        assert ra.axis == rb.axis and ra.steps == -rb.steps


def test_las_acciones_de_teclado_actuan_sobre_la_pieza_activa():
    assert all(a.piece is None for k, a in PIECE_KEYS.items() if a.kind in ("translate", "rotate"))


def test_ninguna_tecla_esta_en_dos_tablas():
    tablas = [set(PIECE_KEYS), set(CAMERA_KEYS), set(APP_KEYS)]
    assert all(not (tablas[i] & tablas[j]) for i in range(3) for j in range(i + 1, 3))


def test_raton_arrastrar_orbita_y_rueda_acerca():
    drag = pygame.event.Event(pygame.MOUSEMOTION, rel=(10, -5), buttons=(1, 0, 0), pos=(0, 0))
    (cmd,) = translate_event(drag)
    assert cmd.kind == "orbit" and cmd.args == (-4.0, -2.0)
    mover = pygame.event.Event(pygame.MOUSEMOTION, rel=(10, -5), buttons=(0, 0, 0), pos=(0, 0))
    assert translate_event(mover) == []                          # sin botón no orbita
    arriba = pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=1)
    abajo = pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-1)
    assert translate_event(arriba)[0].args[0] < 1 < translate_event(abajo)[0].args[0]


def test_eventos_sin_significado_no_hacen_nada():
    assert translate_event(_key(pygame.K_F12)) == []
    assert translate_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(0, 0))) == []
    assert translate_event(pygame.event.Event(pygame.QUIT)) == [Command("quit")]


# =========================================================================== README = HUD

def test_el_readme_contiene_la_ayuda_del_hud_literal():
    texto = README.read_text(encoding="utf-8")
    for linea in HELP_LINES:
        assert linea in texto, linea


def test_cada_tecla_mapeada_aparece_en_la_ayuda():
    ayuda = " ".join(HELP_LINES).upper()
    letras = [k for k in list(PIECE_KEYS) + list(CAMERA_KEYS) + list(APP_KEYS)
              if pygame.K_a <= k <= pygame.K_z]
    for k in letras:
        assert pygame.key.name(k).upper() in ayuda, pygame.key.name(k)
    for nombre in ("TAB", "1-6", "FLECHAS", "RUEDA", "REPAG", "AVPAG", "ESC"):
        assert nombre in ayuda, nombre


# =========================================================================== órdenes -> estado

def test_mover_la_pieza_cambia_la_escena_y_no_la_camara():
    st = AppState()
    cam0 = (st.camera.azimuth, st.camera.elevation, st.camera.distance, st.camera.fov)
    antes = st.scene.pieces[0].pose.position.copy()
    _run(st, _key(pygame.K_f))
    assert np.allclose(st.scene.pieces[0].pose.position, antes + [0, 0, -1])
    assert (st.camera.azimuth, st.camera.elevation, st.camera.distance, st.camera.fov) == cam0


def test_mover_la_camara_no_cambia_la_escena():
    """R11 desde la interfaz: orbitar, acercar, cambiar FOV y reset dejan la MISMA escena."""
    st = AppState()
    escena = st.scene
    v0 = [m.vertices.copy() for m in get_geometry(escena).meshes]
    drag = pygame.event.Event(pygame.MOUSEMOTION, rel=(50, 20), buttons=(1, 0, 0), pos=(0, 0))
    _run(st, drag, _key(pygame.K_LEFT), _key(pygame.K_PAGEUP), _key(pygame.K_z), _key(pygame.K_c),
         pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=1))
    assert st.scene is escena
    assert all(np.array_equal(a, m.vertices) for a, m in zip(v0, get_geometry(st.scene).meshes))


def test_cada_control_de_camara_hace_lo_suyo():
    st = AppState()
    az, el, d, fov = st.camera.azimuth, st.camera.elevation, st.camera.distance, st.camera.fov
    _run(st, _key(pygame.K_RIGHT))
    assert st.camera.azimuth == pytest.approx((az + 5) % 360)
    _run(st, _key(pygame.K_UP))
    assert st.camera.elevation == pytest.approx(el + 5)
    _run(st, _key(pygame.K_PAGEUP))
    assert st.camera.distance == pytest.approx(d * 0.9)
    _run(st, _key(pygame.K_x))
    assert st.camera.fov == pytest.approx(fov + 5)
    _run(st, _key(pygame.K_c))                                     # R10
    assert (st.camera.azimuth, st.camera.elevation, st.camera.distance, st.camera.fov) == (az, el, d, fov)


def test_movimiento_rechazado_avisa_en_el_hud():
    st = AppState()
    for _ in range(12):                                            # empujar contra el techo
        _run(st, _key(pygame.K_r))
    assert st.message == BLOCKED_MSG
    lineas = build_hud_lines(st.scene, st.camera, st.fill_faces, st.message)
    assert BLOCKED_MSG in lineas
    _run(st, _key(pygame.K_f))                                     # un movimiento válido lo borra
    assert st.message == ""


def test_seleccion_por_tab_y_por_numero():
    st = AppState()
    _run(st, _key(pygame.K_TAB))
    assert st.scene.active == 1
    _run(st, _key(pygame.K_5))
    assert st.scene.active == 4
    _run(st, _key(pygame.K_9))                                     # no existe la pieza 9
    assert st.scene.active == 4 and st.message == ""


def test_g_alterna_las_caras_y_esc_sale():
    st = AppState()
    assert frame_primitives(st, 640, 480).polygons == []
    _run(st, _key(pygame.K_g))
    assert st.fill_faces and len(frame_primitives(st, 640, 480).polygons) > 0
    _run(st, _key(pygame.K_g), _key(pygame.K_ESCAPE))
    assert not st.fill_faces and not st.running


def test_h_oculta_y_muestra_la_ayuda():
    st = AppState()
    _run(st, _key(pygame.K_h))
    assert not st.show_help
    assert not set(HELP_LINES) & set(build_hud_lines(st.scene, st.camera, False, "", False, st.show_help))
    _run(st, _key(pygame.K_h))
    assert st.show_help


def test_la_ayuda_cabe_en_la_columna_izquierda():
    """Cada línea mide < 290 px con la fuente real: no llega al contenedor (empieza en x ≈ 310)."""
    pygame.init()
    try:
        font = pygame.font.Font(None, 22)
        for linea in HELP_LINES:
            assert 10 + font.size(linea)[0] < 290, (linea, font.size(linea)[0])
    finally:
        pygame.quit()


def test_el_hud_muestra_pieza_estado_y_camara():
    st = AppState()
    _run(st, _key(pygame.K_TAB))
    l = build_hud_lines(st.scene, st.camera, True, "", demo=True)
    assert "2/6" in l[0] and st.scene.pieces[1].name in l[0] and "en juego" in l[0] and "[DEMO]" in l[0]
    assert "fov= 50.0" in l[1] and "Caras: si" in l[1]
    assert l[-len(HELP_LINES):] == HELP_LINES


# =========================================================================== dibujo (R16)

def _prims(polys=(), segs=(), seg_depths=(), colors=None, active=None):
    segs = np.asarray(segs, float).reshape(-1, 2, 2)
    n = len(segs)
    return DrawPrimitives2D(segments=segs, seg_colors=colors or [(255, 255, 255)] * n,
                            seg_depths=np.asarray(seg_depths, float),
                            seg_active=np.asarray(active or [False] * n, bool),
                            polygons=list(polys))


@pytest.fixture()
def superficie():
    pygame.init()
    s = pygame.Surface((100, 100))
    s.fill(BG)
    yield s
    pygame.quit()


def test_arista_lejana_queda_tapada_por_una_cara_cercana(superficie):
    """El error de E3: dibujar todas las caras y luego todas las aristas pintaba lo de atrás encima."""
    cuadro = np.array([[20, 20], [80, 20], [80, 80], [20, 80]], float)
    prim = _prims(polys=[(cuadro, (200, 0, 0), 5.0)],
                  segs=[[[0, 50], [100, 50]]], seg_depths=[9.0], colors=[(0, 255, 0)])
    draw_primitives(superficie, prim)
    assert superficie.get_at((50, 50))[:3] == tuple(int(c * FACE_SHADE) for c in (200, 0, 0))
    assert superficie.get_at((10, 50))[:3] == (0, 255, 0)          # fuera de la cara sí se ve


def test_arista_cercana_queda_encima_de_una_cara_lejana(superficie):
    cuadro = np.array([[20, 20], [80, 20], [80, 80], [20, 80]], float)
    prim = _prims(polys=[(cuadro, (200, 0, 0), 9.0)],
                  segs=[[[0, 50], [100, 50]]], seg_depths=[2.0], colors=[(0, 255, 0)])
    draw_primitives(superficie, prim)
    assert superficie.get_at((50, 50))[:3] == (0, 255, 0)


def test_la_cara_lleva_borde_de_su_color(superficie):
    cuadro = np.array([[20, 20], [80, 20], [80, 80], [20, 80]], float)
    draw_primitives(superficie, _prims(polys=[(cuadro, (200, 100, 0), 3.0)]))
    assert superficie.get_at((50, 20))[:3] == (200, 100, 0)        # borde
    assert superficie.get_at((50, 50))[:3] == (110, 55, 0)         # relleno oscurecido


def test_orden_de_dibujo_mezcla_caras_y_aristas_de_lejos_a_cerca():
    cuadro = np.zeros((4, 2))
    prim = _prims(polys=[(cuadro, (1, 1, 1), 4.0), (cuadro, (1, 1, 1), 8.0)],
                  segs=[[[0, 0], [1, 1]]] * 3, seg_depths=[9.0, 4.0, 1.0])
    assert draw_order(prim) == [(1, 0), (0, 1), (0, 0), (1, 1), (1, 2)]   # empate: cara primero


def test_caras_con_coordenadas_absurdas_se_descartan(superficie):
    malo = np.array([[0, 0], [1e7, 0], [0, 1e7]], float)
    nan = np.array([[0, 0], [np.nan, 0], [0, 50]], float)
    draw_primitives(superficie, _prims(polys=[(malo, (255, 0, 0), 1.0), (nan, (255, 0, 0), 1.0)]))
    assert superficie.get_at((5, 5))[:3] == BG


def test_aplicacion_completa_con_caras_y_camara_dentro_del_contenedor():
    """Cámara metida en el pozo, caras activadas: el fotograma se dibuja sin errores."""
    pygame.init()
    try:
        st = AppState(fill_faces=True)
        for _ in range(40):
            _run(st, _key(pygame.K_PAGEUP))                        # distancia mínima: 2
        _run(st, *[_key(pygame.K_DOWN)] * 10)
        s = pygame.Surface((640, 480))
        prim = frame_primitives(st, 640, 480)
        draw_primitives(s, prim)
        assert np.isfinite(prim.segments).all()
        assert all(np.isfinite(p).all() for p, _, _ in prim.polygons)
    finally:
        pygame.quit()
