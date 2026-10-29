"""Pruebas del módulo B en E5: cámara orbital (R07 orbitar, R08 distancia, R09 FOV, R10 reset).

No importan blockout.scene ni blockout.app: la cámara se prueba sola.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from blockout.projection import OrbitCamera, build_camera, project_points


def test_vista_inicial_es_la_de_e3():
    """El objetivo es el centro del contenedor 5×5×10 y el ojo es el de app/main.py de E3."""
    cam = OrbitCamera()
    assert np.allclose(cam.target, [2.5, 2.5, 5.0])
    assert np.allclose(cam.eye, [12.469, -14.767, 14.298], atol=1e-3)
    c = cam.build(1000, 700)
    assert np.allclose(c.center, cam.eye)
    assert np.isclose(c.K[0, 0], 500 / math.tan(math.radians(25)))      # f para FOV 50°


def test_el_ojo_sale_de_las_coordenadas_esfericas():
    cam = OrbitCamera(target=np.zeros(3), azimuth=0, elevation=0, distance=10)
    assert np.allclose(cam.eye, [10, 0, 0])                               # sobre +X
    cam.orbit(90, 0)
    assert np.allclose(cam.eye, [0, 10, 0])                               # azimut 90° -> +Y
    cam.orbit(0, 89)
    assert np.isclose(np.linalg.norm(cam.eye), 10)                        # la distancia se mantiene


def test_el_objetivo_siempre_cae_en_el_centro_de_la_imagen():
    cam = OrbitCamera()
    for d_az, d_el in [(0, 0), (37, 10), (200, -60), (-15, 80)]:
        cam.orbit(d_az, d_el)
        uv, _, ok = project_points(cam.build(800, 600), cam.target)
        assert ok[0] and np.allclose(uv[0], [400, 300])


def test_orbitar_360_grados_vuelve_al_mismo_ojo():
    cam = OrbitCamera()
    ojo = cam.eye.copy()
    for _ in range(36):
        cam.orbit(10, 0)
    assert np.allclose(cam.eye, ojo)


def test_la_elevacion_se_limita_a_89_grados():
    cam = OrbitCamera()
    cam.orbit(0, 500)
    assert cam.elevation == 89.0
    cam.build(640, 480)                                                   # look_at no falla
    cam.orbit(0, -1000)
    assert cam.elevation == -89.0
    cam.build(640, 480)


def test_zoom_cambia_la_distancia_y_no_el_objetivo():
    cam = OrbitCamera()
    d0, t0 = cam.distance, cam.target.copy()
    cam.zoom(0.5)
    assert np.isclose(cam.distance, d0 * 0.5) and np.array_equal(cam.target, t0)
    for _ in range(100):
        cam.zoom(0.5)
    assert cam.distance == 2.0                                            # límite inferior
    for _ in range(100):
        cam.zoom(3.0)
    assert cam.distance == 80.0                                           # límite superior


def test_cambiar_el_fov_cambia_K_y_no_la_posicion():
    """R09: "zoom de lente". Cerrar el FOV agranda la imagen; el centro óptico no se mueve."""
    cam = OrbitCamera()
    c1 = cam.build(800, 600)
    cam.set_fov(30)
    c2 = cam.build(800, 600)
    assert np.allclose(c1.center, c2.center) and np.allclose(c1.R, c2.R)
    assert c2.K[0, 0] > c1.K[0, 0]
    esquina = np.array([[0.0, 0.0, 10.0]])
    d1 = np.linalg.norm(project_points(c1, esquina)[0] - [400, 300])
    d2 = np.linalg.norm(project_points(c2, esquina)[0] - [400, 300])
    assert d2 > d1
    cam.set_fov(1)
    assert cam.fov == 15.0
    cam.set_fov(179)
    assert cam.fov == 120.0


def test_zoom_y_fov_no_son_lo_mismo():
    """Acercarse cambia la perspectiva (paralaje); cerrar el FOV solo escala la imagen."""
    pts = np.array([[2.5, 2.5, 5.0], [2.5, 2.5, 0.0], [0, 0, 0], [5, 5, 10]], float)
    a = OrbitCamera()
    b = OrbitCamera()
    a.zoom(0.6)
    uv_a = project_points(a.build(800, 600), pts)[0]
    f0 = 400 / math.tan(math.radians(25))
    b.set_fov(2 * math.degrees(math.atan(400 / (f0 / 0.6))))              # misma escala en el objetivo
    uv_b = project_points(b.build(800, 600), pts)[0]
    assert not np.allclose(uv_a, uv_b, atol=1.0)


def test_reset_restaura_todo():
    cam = OrbitCamera()
    inicial = cam.build(640, 480)
    cam.orbit(123, -40)
    cam.zoom(0.3)
    cam.set_fov(100)
    cam.target[0] += 3                                                    # incluso si alguien movió el objetivo
    cam.reset()
    otra = cam.build(640, 480)
    for x, y in [(inicial.K, otra.K), (inicial.R, otra.R), (inicial.t, otra.t)]:
        assert np.allclose(x, y)
    cam.target[1] += 1                                                    # reset entrega una copia:
    cam.reset()                                                           # el estado guardado no cambió
    assert np.allclose(cam.target, [2.5, 2.5, 5.0])


def test_valores_iniciales_fuera_de_rango_se_ajustan():
    cam = OrbitCamera(elevation=95, distance=500, fov=5, azimuth=-90)
    assert (cam.elevation, cam.distance, cam.fov, cam.azimuth) == (89.0, 80.0, 15.0, 270.0)


@pytest.mark.parametrize("metodo,args", [("orbit", (math.nan, 0)), ("orbit", (0, math.inf)),
                                         ("zoom", (0.0,)), ("zoom", (-2.0,)), ("zoom", (math.nan,)),
                                         ("set_fov", (math.nan,))])
def test_entradas_invalidas_se_ignoran(metodo, args):
    cam = OrbitCamera()
    antes = (cam.azimuth, cam.elevation, cam.distance, cam.fov)
    getattr(cam, metodo)(*args)
    assert (cam.azimuth, cam.elevation, cam.distance, cam.fov) == antes


def test_build_devuelve_camaras_independientes():
    """Camera es inmutable: mover la órbita después no cambia una cámara ya construida."""
    cam = OrbitCamera()
    c1 = cam.build(640, 480)
    R1 = c1.R.copy()
    cam.orbit(45, 0)
    assert np.array_equal(c1.R, R1)
    assert not np.allclose(cam.build(640, 480).R, R1)


def test_coincide_con_build_camera():
    cam = OrbitCamera(azimuth=33, elevation=-12, distance=17, fov=70)
    a = cam.build(1024, 768)
    b = build_camera(cam.eye, cam.target, 1024, 768, 70)
    assert np.allclose(a.P, b.P)
