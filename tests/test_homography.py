"""Pruebas del experimento de homografía (E7): R18 derivar, R19 verificar con ≥4 puntos, R20 fuera del plano.

Las cámaras se construyen con build_camera; no se importa blockout.scene (salvo en la prueba que
vuelve a correr el experimento completo, que usa los vértices de las piezas de A).
"""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pytest

from blockout.projection import build_camera, project_points
from blockout.projection.homography import (FLOOR_PLANE, apply_homography, collinearity_margin,
                                            estimate_homography_dlt, has_three_collinear,
                                            homography_between_views, homography_from_plane_normal,
                                            plane_to_image_homography, pure_rotation_homography,
                                            reprojection_errors)

ROOT = Path(__file__).parents[1]
FLOOR = np.array([[0, 0, 0], [5, 0, 0], [5, 5, 0], [0, 5, 0], [1, 3, 0], [4, 2.5, 0]], float)


def _cams():
    c1 = build_camera((12.0, -14.0, 14.0), (2.5, 2.5, 3.0), 1000, 700, 50)
    c2 = build_camera((-5.0, 16.0, 18.0), (2.5, 2.5, 1.0), 1000, 700, 55)
    return c1, c2


def _random_cams(rng):
    """Dos cámaras al azar por encima del piso, mirando al pozo (semilla fija = reproducible)."""
    def one():
        eye = rng.uniform([-15, -15, 4], [20, 20, 25])
        return build_camera(eye, rng.uniform([0, 0, 0], [5, 5, 3]), 800, 600, rng.uniform(30, 90))
    return one(), one()


def _lift(z):
    P = FLOOR.copy()
    P[:, 2] = z
    return P


# ===================================================================== R18 · derivación

def test_para_el_piso_H_es_P_sin_su_tercera_columna():
    """H = K[r1 | r2 | t]: con Z = 0 la columna r3 de P se multiplica por cero."""
    c1, _ = _cams()
    H = plane_to_image_homography(c1, **FLOOR_PLANE)
    assert np.allclose(H, c1.P[:, [0, 1, 3]])


def test_H_lleva_coordenadas_del_plano_a_los_pixeles_de_project_points():
    c1, _ = _cams()
    H = plane_to_image_homography(c1, **FLOOR_PLANE)
    uv, _, _ = project_points(c1, FLOOR)
    assert np.allclose(apply_homography(H, FLOOR[:, :2]), uv, atol=1e-9)


def test_dos_derivaciones_dan_la_misma_H21():
    """H2·H1⁻¹ (columnas del plano) y K2(R + t nᵀ/d)K1⁻¹ (normal del plano) son la misma matriz."""
    rng = np.random.default_rng(7)
    for _ in range(50):
        c1, c2 = _random_cams(rng)
        a = homography_between_views(c1, c2, **FLOOR_PLANE)
        b = homography_from_plane_normal(c1, c2, (0, 0, 1), 0.0)
        assert np.allclose(a, b, rtol=1e-8, atol=1e-8)


def test_tambien_vale_para_la_pared_del_fondo():
    """El enunciado sugiere "el fondo del contenedor": la misma función sirve para la pared Y = 5."""
    c1, c2 = _cams()
    wall = dict(origin=(0, 5, 0), e1=(1, 0, 0), e2=(0, 0, 1))
    H = homography_between_views(c1, c2, **wall)
    assert np.allclose(H, homography_from_plane_normal(c1, c2, (0, 1, 0), 5.0), atol=1e-8)
    pts = np.array([[0, 5, 0], [5, 5, 0], [5, 5, 10], [0, 5, 10], [1, 5, 7], [4, 5, 3]], float)
    x1, _, _ = project_points(c1, pts)
    x2, _, _ = project_points(c2, pts)
    assert reprojection_errors(H, x1, x2).max() < 1e-8


def test_tres_matrices_distintas():
    """M es 4×4 invertible, P es 3×4 de rango 3 (no se invierte) y H es 3×3 invertible."""
    from blockout.scene import create_scene, model_matrix
    c1, c2 = _cams()
    M = model_matrix(create_scene().pieces[0])
    assert M.shape == (4, 4) and abs(np.linalg.det(M)) > 0.5
    assert c1.P.shape == (3, 4) and np.linalg.matrix_rank(c1.P) == 3
    H = homography_between_views(c1, c2, **FLOOR_PLANE)
    assert H.shape == (3, 3) and np.linalg.matrix_rank(H) == 3
    assert np.isclose(H[2, 2], 1.0)                                       # normalizada


def test_camara_sobre_el_plano_se_rechaza():
    """La cámara del ejemplo compartido está en Z = 0: ve el piso de canto y H1 es singular."""
    on_plane = build_camera((0, -10, 0), (0, 0, 0), 640, 480, 60)
    _, c2 = _cams()
    with pytest.raises(ValueError):
        homography_between_views(on_plane, c2, **FLOOR_PLANE)
    with pytest.raises(ValueError):
        homography_between_views(c2, on_plane, **FLOOR_PLANE)


# ===================================================================== R19 · verificación en el plano

def test_los_6_puntos_estan_en_posicion_general_en_las_dos_imagenes():
    c1, c2 = _cams()
    for c in (c1, c2):
        uv, _, ok = project_points(c, FLOOR)
        assert ok.all() and not has_three_collinear(uv, tol=10.0)


def test_H21_lleva_el_piso_de_una_vista_a_la_otra():
    rng = np.random.default_rng(11)
    for _ in range(50):
        c1, c2 = _random_cams(rng)
        x1, _, v1 = project_points(c1, FLOOR)
        x2, _, v2 = project_points(c2, FLOOR)
        assert v1.all() and v2.all()
        H = homography_between_views(c1, c2, **FLOOR_PLANE)
        assert reprojection_errors(H, x1, x2).max() < 1e-7


def test_dlt_sin_ruido_recupera_la_H_analitica():
    c1, c2 = _cams()
    x1, _, _ = project_points(c1, FLOOR)
    x2, _, _ = project_points(c2, FLOOR)
    H = homography_between_views(c1, c2, **FLOOR_PLANE)
    assert np.allclose(estimate_homography_dlt(x1, x2), H, rtol=1e-7, atol=1e-7)
    assert np.allclose(estimate_homography_dlt(x1[:4], x2[:4]), H, rtol=1e-7, atol=1e-7)  # mínimo


def test_dlt_con_ruido_da_errores_del_orden_del_ruido():
    c1, c2 = _cams()
    x1, _, _ = project_points(c1, FLOOR)
    x2, _, _ = project_points(c2, FLOOR)
    rng = np.random.default_rng(3)
    errs = []
    for _ in range(100):
        Hn = estimate_homography_dlt(x1 + rng.normal(0, 0.5, x1.shape), x2 + rng.normal(0, 0.5, x2.shape))
        errs.append(reprojection_errors(Hn, x1, x2).mean())
    assert 0.2 < np.mean(errs) < 1.5                                      # ~σ, no 0 ni cientos


def test_dlt_rechaza_datos_insuficientes_o_degenerados():
    c1, c2 = _cams()
    x1, _, _ = project_points(c1, FLOOR)
    x2, _, _ = project_points(c2, FLOOR)
    with pytest.raises(ValueError):
        estimate_homography_dlt(x1[:3], x2[:3])
    linea = np.array([[0, 0], [1, 1], [2, 2], [3, 0], [0, 3]], float) * 100
    with pytest.raises(ValueError):
        estimate_homography_dlt(linea, linea + 5)


def test_margen_de_colinealidad():
    tri = np.array([[0, 0], [10, 0], [0, 10]], float)
    assert np.isclose(collinearity_margin(tri), 10 / math.sqrt(2))       # altura menor del triángulo
    assert collinearity_margin(np.array([[0, 0], [1, 1], [2, 2]], float)) == 0.0
    assert collinearity_margin(np.array([[0, 0], [0, 0], [3, 1]], float)) == 0.0


# ===================================================================== R20 · fuera del plano

def test_la_misma_H_falla_fuera_del_plano_y_el_error_crece_con_la_altura():
    c1, c2 = _cams()
    H = homography_between_views(c1, c2, **FLOOR_PLANE)
    medias = []
    for z in (0.0, 0.25, 0.5, 1.0, 2.0):
        a, _, _ = project_points(c1, _lift(z))
        b, _, _ = project_points(c2, _lift(z))
        medias.append(reprojection_errors(H, a, b).mean())
    assert medias[0] < 1e-8 and medias[1] > 1.0                          # cero solo en el plano
    assert all(x < y for x, y in zip(medias, medias[1:]))                 # crece con Z


def test_la_formula_del_paralaje_predice_el_punto_equivocado():
    """λ1 x1 = H1 p + Z·K1 r3¹: H21 lleva eso a H2 p + Z·H21 K1 r3¹, que no es la imagen real."""
    c1, c2 = _cams()
    H1 = plane_to_image_homography(c1, **FLOOR_PLANE)
    H2 = plane_to_image_homography(c2, **FLOOR_PLANE)
    H = homography_between_views(c1, c2, **FLOOR_PLANE)
    z = 1.5
    a, _, _ = project_points(c1, _lift(z))
    ph = np.hstack([FLOOR[:, :2], np.ones((6, 1))])
    pred = (ph @ H1.T + z * (c1.K @ c1.R[:, 2])) @ (H2 @ np.linalg.inv(H1)).T
    assert np.allclose(pred[:, :2] / pred[:, 2:3], apply_homography(H, a), atol=1e-8)


def test_si_no_cambia_el_centro_la_homografia_sirve_para_todo():
    """Enunciado §3 paso 4: el problema es el CAMBIO DE CENTRO. Si la cámara solo gira (y cambia
    su FOV), H21 = K2 R K1⁻¹ no depende del plano y acierta también los puntos elevados."""
    c1, _ = _cams()
    c3 = build_camera(c1.center, (4.0, 1.0, 1.0), 1000, 700, 65)
    Hp = homography_between_views(c1, c3, **FLOOR_PLANE)
    Hr = pure_rotation_homography(c1, c3)
    assert np.allclose(Hp, Hr, atol=1e-8)
    for z in (0.0, 1.0, 3.0, 7.0):
        a, _, va = project_points(c1, _lift(z))
        b, _, vb = project_points(c3, _lift(z))
        assert (va & vb).all()
        assert reprojection_errors(Hp, a, b).max() < 1e-7
    with pytest.raises(ValueError):
        pure_rotation_homography(c1, _cams()[1])


# ===================================================================== el informe está al día

def _load_experiment():
    path = ROOT / "experiments" / "homography_experiment.py"
    spec = importlib.util.spec_from_file_location("homography_experiment", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _compare(fresh, saved, path="r"):
    if isinstance(fresh, dict):
        assert set(fresh) == set(saved), path
        for k in fresh:
            _compare(fresh[k], saved[k], f"{path}.{k}")
    elif isinstance(fresh, list):
        assert len(fresh) == len(saved), path
        for i, (a, b) in enumerate(zip(fresh, saved)):
            _compare(a, b, f"{path}[{i}]")
    elif isinstance(fresh, float):
        if abs(fresh) < 1e-9 or abs(saved) < 1e-9:                       # ruido numérico de la plataforma
            assert abs(fresh) < 1e-9 and abs(saved) < 1e-9, path
        else:
            assert math.isclose(fresh, saved, rel_tol=1e-6, abs_tol=1e-9), path
    else:
        assert fresh == saved, path


def test_los_resultados_guardados_son_los_que_produce_el_experimento():
    """Si alguien cambia las cámaras o los puntos, esta prueba obliga a volver a correr el script."""
    exp = _load_experiment()
    fresh = exp.run()
    saved = json.loads((ROOT / "results" / "homografia.json").read_text(encoding="utf-8"))
    _compare(fresh, saved)
    assert (ROOT / "results" / "homografia.md").read_text(encoding="utf-8") == exp.to_markdown(fresh)


def test_el_experimento_no_falla_con_la_consola_de_windows(tmp_path, monkeypatch):
    """La consola de Windows en español usa cp1252, sin `σ` ni `⁻¹`. El script no debe fallar."""
    import io
    import sys
    exp = _load_experiment()
    consola = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", consola)
    exp.main(out_dir=tmp_path)
    consola.flush()
    assert "H21" in consola.buffer.getvalue().decode("cp1252")
    assert {p.name for p in tmp_path.iterdir()} == {"homografia.json", "homografia.md",
                                                    "homografia.png"}


def test_el_informe_tiene_las_tablas_actuales():
    exp = _load_experiment()
    informe = (ROOT / "docs" / "INFORME.md").read_text(encoding="utf-8")
    for linea in exp.to_markdown(exp.run()).splitlines():
        if linea.startswith("|"):
            assert linea in informe, linea
