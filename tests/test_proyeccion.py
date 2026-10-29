"""Pruebas del módulo B (E3): K, look_at, build_camera, project_points, recorte y project.

Estas pruebas NO importan blockout.scene: la geometría se escribe a mano. Así el PR de B se puede
revisar y fusionar sin esperar al de A (y viceversa).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from blockout.core.types import Geometry3D, Mesh3D
from blockout.projection import (build_camera, clip_segment_near, intrinsics_from_fov, look_at,
                                 project, project_points)
from blockout.projection.projection import perspective_divide, world_to_camera

FIXTURE = Path(__file__).parent / "fixtures" / "shared_example.json"


@pytest.fixture(scope="module")
def ej() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cam(ej):
    c = ej["camara"]
    return build_camera(c["eye"], c["target"], c["width"], c["height"], c["fov_deg"], c["near"])


# ------------------------------------------------------------------- contra el ejemplo

def test_build_camera_da_K_R_t_del_ejemplo(ej, cam):
    c, tol = ej["camara"], ej["tolerancia"]
    assert np.allclose(cam.K, c["K"], atol=tol)
    assert np.allclose(cam.R, c["R"], atol=tol)
    assert np.allclose(cam.t, c["t"], atol=tol)
    assert np.allclose(cam.center, c["centro_en_el_mundo"], atol=tol)


def test_project_points_reproduce_la_tabla_del_ejemplo(ej, cam):
    pts = np.array([p["punto_mundo"] for p in ej["puntos"]], float)
    uv, z, visible = project_points(cam, pts)
    for k, p in enumerate(ej["puntos"]):
        assert np.isclose(z[k], p["z_cam"], atol=ej["tolerancia"]), p["nombre"]
        assert visible[k] == p["visible"], p["nombre"]
        if p["visible"]:
            assert np.allclose(uv[k], p["uv"], atol=ej["tolerancia"]), p["nombre"]
        else:
            assert np.isnan(uv[k]).all(), p["nombre"]


def test_centros_de_la_pieza_del_ejemplo_caen_en_su_pixel(ej, cam):
    filas = ej["pieza"]["centros_de_cubos"]
    uv, _, visible = project_points(cam, np.array([f["centro_mundo"] for f in filas], float))
    assert visible.all()
    assert np.allclose(uv, [f["uv"] for f in filas], atol=ej["tolerancia"])


def test_P_es_la_misma_cadena_que_K_R_t(cam):
    """P · [X, 1] y K · (R·X + t) son el mismo vector: P es solo la forma compacta de la cadena."""
    X = np.array([1.3, 2.1, 0.7])
    a = cam.K @ (cam.R @ X + cam.t)
    b = cam.P @ np.append(X, 1.0)
    assert cam.P.shape == (3, 4)
    assert np.allclose(a, b)
    uv, _, _ = project_points(cam, X)
    assert np.allclose(uv[0], b[:2] / b[2])


# ------------------------------------------------------------------------- intrínsecos

def test_K_desde_el_fov_horizontal():
    K = intrinsics_from_fov(640, 480, 90.0)            # tan(45°) = 1  =>  f = 320
    assert np.allclose(K, [[320, 0, 320], [0, 320, 240], [0, 0, 1]])
    for malo in (0.0, 180.0, -5.0):
        with pytest.raises(ValueError):
            intrinsics_from_fov(640, 480, malo)


def test_cerrar_el_fov_agranda_la_imagen_sin_mover_la_camara():
    eye, target = (3.0, -8.0, 4.0), (0.0, 0.0, 0.0)
    ancho = build_camera(eye, target, 800, 600, 70)
    angosto = build_camera(eye, target, 800, 600, 30)
    assert np.allclose(ancho.center, angosto.center)          # el centro óptico no se mueve
    pts = np.array([[1, 0, 0], [0, 1, 1], [-1, 0.5, 0.2]], float)
    uv_a, _, _ = project_points(ancho, pts)
    uv_n, _, _ = project_points(angosto, pts)
    c = np.array([400, 300])
    assert (np.linalg.norm(uv_n - c, axis=1) > np.linalg.norm(uv_a - c, axis=1)).all()


# ------------------------------------------------------------------------- extrínsecos

def test_look_at_da_una_rotacion_propia_desde_cualquier_lado():
    rng = np.random.default_rng(7)                              # semilla fija: reproducible
    for _ in range(200):
        eye = rng.uniform(-30, 30, 3)
        R, t = look_at(eye, (2.5, 2.5, 4.0))
        assert np.allclose(R @ R.T, np.eye(3)) and np.isclose(np.linalg.det(R), 1.0)
        assert np.allclose(-R.T @ t, eye)                       # C = −Rᵀ t
        Xc = R @ np.array([2.5, 2.5, 4.0]) + t                  # el objetivo cae en el eje óptico
        assert np.allclose(Xc[:2], 0) and Xc[2] > 0


def test_arriba_del_mundo_se_ve_arriba_en_la_imagen():
    """Z del mundo hacia arriba y v de la imagen hacia abajo: subir en el mundo debe bajar v."""
    cam = build_camera((10, -10, 5), (0, 0, 0), 800, 600, 50)
    uv, _, _ = project_points(cam, np.array([[0, 0, 0], [0, 0, 1]], float))
    assert uv[1, 1] < uv[0, 1]


def test_look_at_degenerado_lanza_error():
    with pytest.raises(ValueError):
        look_at((0, 0, 10), (0, 0, 0))                          # mirando justo hacia abajo
    with pytest.raises(ValueError):
        look_at((1, 2, 3), (1, 2, 3))                           # eye == target


# ----------------------------------------------------------------------------- recorte

def test_recorte_de_un_segmento_que_cruza_el_plano_cercano():
    a, b = np.array([0, 0, -1.0]), np.array([0, 0, 3.0])
    a2, b2 = clip_segment_near(a, b, 0.1)
    assert a2[2] == 0.1 and np.allclose(b2, b)
    # el punto de corte está sobre la arista original (interpolación lineal)
    a, b = np.array([2.0, -1.0, -1.0]), np.array([0.0, 1.0, 1.0])
    p, q = clip_segment_near(a, b, 0.5)
    s = (0.5 - a[2]) / (b[2] - a[2])
    assert np.allclose(p, a + s * (b - a)) and np.allclose(q, b)


def test_recorte_descarta_lo_que_esta_detras_y_no_toca_lo_de_adelante():
    assert clip_segment_near(np.array([0, 0, -2.0]), np.array([1, 0, -1.0]), 0.1) is None
    assert clip_segment_near(np.array([0, 0, 0.05]), np.array([1, 0, 0.0]), 0.1) is None
    a, b = np.array([0, 0, 1.0]), np.array([1, 1, 2.0])
    a2, b2 = clip_segment_near(a, b, 0.1)
    assert np.array_equal(a2, a) and np.array_equal(b2, b)


def test_dividir_sin_recortar_refleja_el_punto(cam):
    """Por qué existe el recorte: un punto ARRIBA y DETRÁS de la cámara, dividido a ciegas,
    sale ABAJO del centro de la imagen (z negativo invierte el signo)."""
    Xc = world_to_camera(cam, np.array([[0.0, -12.0, 1.0]]))
    assert Xc[0, 2] < 0
    v_ingenuo = perspective_divide(cam, Xc)[0, 1]
    assert v_ingenuo > cam.height / 2                          # aparecería abajo: falso
    _, _, visible = project_points(cam, np.array([[0.0, -12.0, 1.0]]))
    assert not visible[0]                                      # la versión correcta lo descarta


# ----------------------------------------------------------------------------- project

def _malla(vertices, edges, color=(1, 2, 3), active=False, name="m"):
    return Mesh3D(name, np.asarray(vertices, float), np.asarray(edges, int).reshape(-1, 2),
                  np.zeros((0, 4), int), color=color, active=active)


def test_project_entrega_formas_del_contrato(cam):
    g = Geometry3D([_malla([[0, 0, 0], [1, 0, 0]], [[0, 1]], color=(9, 8, 7), active=True)])
    prim = project(g, cam)
    assert prim.segments.shape == (1, 2, 2)
    assert np.allclose(prim.segments[0], [[320, 240], [375.4256258422041, 240]])
    assert prim.seg_colors == [(9, 8, 7)] and prim.seg_active.tolist() == [True]
    assert np.allclose(prim.seg_depths, [10.0]) and prim.polygons == []


def test_project_recorta_y_descarta(cam):
    g = Geometry3D([
        _malla([[0, 0, 0], [0, -20, 0]], [[0, 1]]),            # cruza el plano cercano
        _malla([[0, -15, 0], [1, -20, 0]], [[0, 1]]),          # totalmente detrás
        _malla(np.zeros((0, 3)), np.zeros((0, 2))),            # malla vacía
    ])
    prim = project(g, cam)
    assert prim.segments.shape == (1, 2, 2)                    # solo sobrevive el primero
    assert np.isfinite(prim.segments).all()
    assert np.isclose(prim.seg_depths[0], 0.5 * (10 + cam.near))


def test_project_con_la_camara_dentro_de_una_caja_es_finito():
    """La cámara dentro del contenedor ve aristas por todos lados, algunas detrás: nada de NaN/inf."""
    W, D, H = 5, 5, 10
    v = [(x, y, z) for x in (0, W) for y in (0, D) for z in (0, H)]
    e = [(i, j) for i in range(8) for j in range(i + 1, 8)
         if sum(a != b for a, b in zip(v[i], v[j])) == 1]
    cam = build_camera((2.5, 2.5, 3.0), (2.5, 5.0, 3.0), 800, 600, 50)
    prim = project(Geometry3D([_malla(v, e)]), cam)
    assert len(e) == 12 and 0 < len(prim.segments) < 12        # algunas se descartan
    assert np.isfinite(prim.segments).all() and np.isfinite(prim.seg_depths).all()


def test_project_de_geometria_vacia():
    cam = build_camera((0, -10, 0), (0, 0, 0), 640, 480, 60)
    prim = project(Geometry3D([]), cam)
    assert prim.segments.shape == (0, 2, 2) and prim.seg_depths.shape == (0,)
    assert math.isclose(cam.near, 0.1)
