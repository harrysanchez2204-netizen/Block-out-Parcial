"""Pruebas del módulo B en E5: recorte de polígonos, caras rellenas (R16) y robustez (R15).

Casi todo usa geometría escrita a mano. La última sección comprueba con la malla REAL de A que la
orientación de sus caras coincide con la que asume el descarte de caras traseras de B.
"""
from __future__ import annotations

import numpy as np
import pytest

from blockout.core.types import Geometry3D, Mesh3D
from blockout.projection import OrbitCamera, build_camera, clip_polygon_near, project
from blockout.projection.projection import is_back_face, world_to_camera

# Cubo unitario en [0,1]³ con caras ANTIHORARIAS vistas desde afuera (convención del contrato).
CUBE_V = np.array([[x, y, z] for z in (0, 1) for y in (0, 1) for x in (0, 1)], float)
CUBE_F = np.array([[0, 2, 3, 1],      # z = 0, normal −Z
                   [4, 5, 7, 6],      # z = 1, normal +Z
                   [0, 1, 5, 4],      # y = 0, normal −Y
                   [2, 6, 7, 3],      # y = 1, normal +Y
                   [0, 4, 6, 2],      # x = 0, normal −X
                   [1, 3, 7, 5]])     # x = 1, normal +X
CUBE_E = np.array([(i, j) for i in range(8) for j in range(i + 1, 8)
                   if np.abs(CUBE_V[i] - CUBE_V[j]).sum() == 1])


def _cubo(offset=(0, 0, 0), color=(200, 0, 0)):
    return Mesh3D("cubo", CUBE_V + offset, CUBE_E, CUBE_F, color=color)


def test_el_cubo_de_prueba_tiene_normales_hacia_afuera():
    centro = np.array([0.5, 0.5, 0.5])
    for f in CUBE_F:
        q = CUBE_V[f]
        n = np.cross(q[1] - q[0], q[2] - q[0])
        assert np.dot(n, q.mean(axis=0) - centro) > 0


# ================================================================ recorte de polígonos

def test_poligono_completamente_delante_no_cambia():
    q = np.array([[0, 0, 2], [1, 0, 2], [1, 1, 3], [0, 1, 3]], float)
    assert np.array_equal(clip_polygon_near(q, 0.1), q)


def test_poligono_completamente_detras_desaparece():
    q = np.array([[0, 0, -2], [1, 0, -2], [1, 1, 0.05], [0, 1, 0]], float)
    assert clip_polygon_near(q, 0.1).shape == (0, 3)


@pytest.mark.parametrize("zs,n_esperado", [((-1, 1, 1, 1), 5),   # un vértice detrás -> pentágono
                                           ((-1, -1, 1, 1), 4),  # dos detrás -> cuadrilátero
                                           ((-1, -1, -1, 1), 3)])  # tres detrás -> triángulo
def test_cuantos_vertices_quedan_al_recortar(zs, n_esperado):
    q = np.array([[0, 0, zs[0]], [1, 0, zs[1]], [1, 1, zs[2]], [0, 1, zs[3]]], float)
    r = clip_polygon_near(q, 0.1)
    assert len(r) == n_esperado
    assert (r[:, 2] >= 0.1).all()
    assert np.isclose(r[:, 2].min(), 0.1) or (q[:, 2] >= 0.1).all()


def test_los_puntos_de_corte_estan_sobre_el_borde_original():
    q = np.array([[0, 0, -1], [2, 0, 1], [2, 2, 1], [0, 2, -1]], float)
    r = clip_polygon_near(q, 0.5)
    for p in r[np.isclose(r[:, 2], 0.5)]:
        assert np.isclose(p[0], 1.5)                         # x = 0 + (0.5+1)/(1+1)·2 = 1.5


# ================================================================ caras traseras

def test_desde_afuera_se_ven_1_2_o_3_caras_de_un_cubo():
    casos = {(5, 0.5, 0.5): 1,            # de frente a la cara x = 1
             (5, 5, 0.5): 2,              # por una arista vertical
             (5, 6, 7): 3}                # por una esquina
    for eye, n in casos.items():
        cam = build_camera(eye, (0.5, 0.5, 0.5), 800, 600, 50)
        prim = project(Geometry3D([_cubo()]), cam, fill_faces=True)
        assert len(prim.polygons) == n, eye


def test_la_cara_visible_es_la_correcta():
    cam = build_camera((5, 0.5, 0.5), (0.5, 0.5, 0.5), 800, 600, 50)
    pc = world_to_camera(cam, CUBE_V)
    visibles = [k for k, f in enumerate(CUBE_F) if not is_back_face(pc[f])]
    assert visibles == [5]                                   # la cara x = 1 (normal +X)


def test_el_resultado_no_depende_del_punto_de_la_cara():
    """n·p es igual en todos los puntos de una cara plana (es la ecuación de su plano): por eso
    da lo mismo usar el centroide, un vértice o la cara parcialmente recortada."""
    cam = build_camera((3, -4, 2), (0.5, 0.5, 0.5), 800, 600, 50)
    pc = world_to_camera(cam, CUBE_V)
    for f in CUBE_F:
        q = pc[f]
        n = np.cross(q[1] - q[0], q[2] - q[0])
        assert np.allclose(q @ n, q.mean(axis=0) @ n)


def test_sin_fill_faces_no_hay_poligonos():
    cam = build_camera((5, 6, 7), (0.5, 0.5, 0.5), 800, 600, 50)
    prim = project(Geometry3D([_cubo()]), cam)
    assert prim.polygons == [] and len(prim.segments) == 12


# ================================================================ algoritmo del pintor

def test_poligonos_ordenados_de_lejos_a_cerca():
    cam = build_camera((10, -10, 8), (2, 2, 0), 800, 600, 60)
    g = Geometry3D([_cubo((0, 0, 0), (255, 0, 0)), _cubo((3, 3, 0), (0, 0, 255)),
                    _cubo((1.5, 1.5, 2), (0, 255, 0))])
    prim = project(g, cam, fill_faces=True)
    prof = [d for _, _, d in prim.polygons]
    assert prof == sorted(prof, reverse=True) and len(prof) >= 6


def test_el_cubo_cercano_se_pinta_despues():
    """Dos cubos alineados con la cámara: todas las caras del cercano van al final."""
    cam = build_camera((0.5, -10, 0.5), (0.5, 5, 0.5), 800, 600, 50)
    g = Geometry3D([_cubo((0, 4, 0), (0, 0, 255)), _cubo((0, 0, 0), (255, 0, 0))])
    colores = [c for _, c, _ in project(g, cam, fill_faces=True).polygons]
    assert colores[-1] == (255, 0, 0) and colores[0] == (0, 0, 255)


# ================================================================ robustez (R15)

def test_cara_que_atraviesa_el_plano_de_la_camara():
    cam = build_camera((0.5, 0.5, 0.5), (0.5, 3, 0.5), 800, 600, 50)   # cámara DENTRO del cubo
    prim = project(Geometry3D([_cubo()]), cam, fill_faces=True)
    for pts, _, d in prim.polygons:
        assert np.isfinite(pts).all() and d >= cam.near
    assert np.isfinite(prim.segments).all()


def _escena_de_prueba():
    """Contenedor de alambre 5×5×10 y varios cubos con caras, todo escrito a mano."""
    W, D, H = 5, 5, 10
    v = [(x, y, z) for x in (0, W) for y in (0, D) for z in (0, H)]
    e = [(i, j) for i in range(8) for j in range(i + 1, 8)
         if sum(a != b for a, b in zip(v[i], v[j])) == 1]
    caja = Mesh3D("container", np.array(v, float), np.array(e), np.zeros((0, 4), int))
    cubos = [_cubo(o) for o in [(0, 0, 0), (2, 1, 3), (4, 4, 9), (1, 3, 5), (2, 2, 7)]]
    return Geometry3D([caja] + cubos)


def test_mil_camaras_al_azar_sin_nan_ni_excepciones():
    """Semilla fija (reproducible). Incluye cámaras dentro del contenedor y dentro de los cubos,
    cerca de la elevación límite y con todo el rango de distancia y FOV."""
    rng = np.random.default_rng(1234)
    g = _escena_de_prueba()
    for k in range(1000):
        cam = OrbitCamera(target=rng.uniform([-1, -1, -1], [6, 6, 11]),
                          azimuth=rng.uniform(0, 360), elevation=rng.uniform(-95, 95),
                          distance=rng.uniform(0, 90), fov=rng.uniform(10, 130))
        c = cam.build(640, 480)
        prim = project(g, c, fill_faces=True)
        assert np.isfinite(prim.segments).all(), k
        assert np.isfinite(prim.seg_depths).all() and (prim.seg_depths >= c.near).all(), k
        for pts, _, d in prim.polygons:
            assert np.isfinite(pts).all() and np.isfinite(d), k
        prof = [d for _, _, d in prim.polygons]
        assert prof == sorted(prof, reverse=True), k


# ================================================================ acuerdo con el módulo A

def test_las_caras_de_a_tienen_la_orientacion_que_b_espera():
    """Integración A↔B: un cubo hecho con local_mesh de A, visto de frente, muestra UNA cara y es
    la que mira a la cámara. Si A orientara mal sus caras, aquí se verían 5 (las de atrás)."""
    from blockout.scene.pieces import local_mesh
    v, e, f = local_mesh([(0, 0, 0)])
    m = Mesh3D("a", v, e, f)
    # (desde arriba no se usa (0.5, 0.5, 6): mirar recto hacia abajo es el caso degenerado de look_at)
    for eye, normal in [((5, 0.5, 0.5), 0), ((0.5, -5, 0.5), 1), ((0.6, 0.4, 6), 2)]:
        cam = build_camera(eye, (0.5, 0.5, 0.5), 800, 600, 50)
        pc = world_to_camera(cam, v)
        visibles = [q for q in f if not is_back_face(pc[q])]
        assert len(visibles) == 1
        centro = v[visibles[0]].mean(axis=0)
        direccion = np.sign(np.array(eye) - 0.5)
        assert np.isclose(centro[normal], 0.5 + 0.5 * direccion[normal])
