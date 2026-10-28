"""Pruebas del contrato (E2).

Dos cosas se verifican aquí:

1. Que las estructuras de `core.types` son las acordadas en `docs/INTERFACES.md`.
2. Que los números de `tests/fixtures/shared_example.json` son correctos, recalculándolos
   con numpy puro **a partir de las fórmulas del documento**, sin usar `scene/` ni
   `projection/` (que todavía no están implementados en esta etapa).

Desde E3, cada módulo añade su propia prueba comparando su salida con este mismo archivo.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from blockout.core.types import (Action, Camera, Container, DrawPrimitives2D, Geometry3D,
                                 Mesh3D, Piece, Pose, Scene)

FIXTURE = Path(__file__).parent / "fixtures" / "shared_example.json"


@pytest.fixture(scope="module")
def ej() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- estructuras

def test_pose_por_defecto_es_identidad():
    p = Pose()
    assert np.allclose(p.rotation, np.eye(3))
    assert np.allclose(p.position, np.zeros(3))


def test_pose_y_scene_son_inmutables():
    pose = Pose()
    with pytest.raises(Exception):                 # frozen=True
        pose.position = np.ones(3)                 # type: ignore[misc]
    sc = Scene(container=Container(), pieces=(), active=0)
    with pytest.raises(Exception):
        sc.active = 1                              # type: ignore[misc]


def test_pivot_local_es_el_centro_del_cubo_pivote():
    pz = Piece(id=0, name="L", cells=((0, 0, 0), (1, 0, 0), (2, 0, 0), (0, 1, 0)),
               pivot_cell=2, pose=Pose())
    assert np.allclose(pz.pivot_local, [2.5, 0.5, 0.5])


def test_action_tiene_los_campos_del_contrato():
    a = Action("rotate", piece=1, axis=2, steps=-1)
    assert (a.kind, a.piece, a.axis, a.steps) == ("rotate", 1, 2, -1)
    b = Action("translate", delta=(0, 0, -1))
    assert b.piece is None and b.delta == (0, 0, -1)   # piece=None => pieza activa
    assert Action("select_next").steps == 1            # valores por defecto presentes


def test_container_y_scene_por_defecto():
    assert Container().size == (5, 5, 10)
    sc = Scene(container=Container(), pieces=())
    assert sc.active == 0 and sc.status == "playing" and sc.time == 0.0


def test_estructuras_de_intercambio_existen_con_sus_campos():
    m = Mesh3D("x", np.zeros((2, 3)), np.array([[0, 1]]), np.zeros((0, 4), int))
    assert m.vertices.shape[1] == 3 and m.active is False
    g = Geometry3D([m])
    assert len(g.meshes) == 1
    d = DrawPrimitives2D(segments=np.zeros((1, 2, 2)), seg_colors=[(1, 2, 3)],
                         seg_depths=np.array([1.0]), seg_active=np.array([False]))
    assert d.segments.shape == (1, 2, 2) and d.polygons == []


def test_camera_expone_centro_y_P(ej):
    cam = Camera(K=np.array(ej["camara"]["K"]), R=np.array(ej["camara"]["R"]),
                 t=np.array(ej["camara"]["t"]), width=ej["camara"]["width"],
                 height=ej["camara"]["height"], near=ej["camara"]["near"])
    assert np.allclose(cam.center, ej["camara"]["eye"])          # C = -R^T t = eye
    assert cam.P.shape == (3, 4)
    assert np.allclose(cam.P, cam.K @ np.hstack([cam.R, cam.t.reshape(3, 1)]))


# ------------------------------------------------------------------- ejemplo compartido

def test_K_sale_del_fov_horizontal(ej):
    c = ej["camara"]
    f = (c["width"] / 2) / math.tan(math.radians(c["fov_deg"]) / 2)
    K = np.array([[f, 0, c["width"] / 2], [0, f, c["height"] / 2], [0, 0, 1]])
    assert np.isclose(f, c["f"], atol=ej["tolerancia"])
    assert np.allclose(K, np.array(c["K"]), atol=ej["tolerancia"])


def test_R_y_t_salen_de_look_at(ej):
    c = ej["camara"]
    eye, target, up = (np.array(c[k], float) for k in ("eye", "target", "up"))
    fd = target - eye
    fd /= np.linalg.norm(fd)
    r = np.cross(fd, up)
    r /= np.linalg.norm(r)
    d = np.cross(fd, r)                       # "abajo" de la cámara
    R, t = np.vstack([r, d, fd]), -np.vstack([r, d, fd]) @ eye
    assert np.allclose(R, np.array(c["R"]), atol=ej["tolerancia"])
    assert np.allclose(t, np.array(c["t"]), atol=ej["tolerancia"])
    assert np.allclose(R @ R.T, np.eye(3)) and np.isclose(np.linalg.det(R), 1.0)


def test_puntos_proyectados_coinciden(ej):
    c = ej["camara"]
    K, R, t, near = (np.array(c["K"]), np.array(c["R"]), np.array(c["t"]), c["near"])
    for p in ej["puntos"]:
        Xc = R @ np.array(p["punto_mundo"], float) + t
        assert np.allclose(Xc, p["punto_camara"], atol=ej["tolerancia"]), p["nombre"]
        assert np.isclose(Xc[2], p["z_cam"], atol=ej["tolerancia"])
        visible = Xc[2] > near
        assert visible == p["visible"], p["nombre"]
        if visible:
            uvw = K @ Xc
            assert np.allclose(uvw[:2] / uvw[2], p["uv"], atol=ej["tolerancia"]), p["nombre"]
        else:
            assert p["uv"] is None


def test_punto_detras_de_la_camara_no_se_divide(ej):
    """El caso que rompe un proyector ingenuo: z_cam < 0 debe quedar fuera, no dar un píxel."""
    malos = [p for p in ej["puntos"] if not p["visible"]]
    assert malos, "el ejemplo debe incluir al menos un punto no visible"
    assert all(p["z_cam"] <= ej["camara"]["near"] for p in malos)


def test_matriz_de_modelo_y_pivote_quieto(ej):
    pz = ej["pieza"]
    R = np.array(pz["pose"]["rotation"], float)
    pos = np.array(pz["pose"]["position"], float)
    pivot_local = np.array(pz["cells"][pz["pivot_cell"]], float) + 0.5
    assert np.allclose(pivot_local, pz["pivot_local"])
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = pos - R @ pivot_local                    # M = [[R, p - R·pivot], [0, 1]]
    assert np.allclose(M, np.array(pz["M"]), atol=ej["tolerancia"])
    # el pivote local cae exactamente en la posición de la pose
    assert np.allclose((M @ np.append(pivot_local, 1.0))[:3], pos, atol=ej["tolerancia"])


def test_centros_de_cubos_hasta_pixeles(ej):
    c, pz = ej["camara"], ej["pieza"]
    K, R, t = np.array(c["K"]), np.array(c["R"]), np.array(c["t"])
    M = np.array(pz["M"])
    for fila in pz["centros_de_cubos"]:
        loc = np.array(fila["centro_local"], float)
        world = (M @ np.append(loc, 1.0))[:3]
        assert np.allclose(world, fila["centro_mundo"], atol=ej["tolerancia"])
        Xc = R @ world + t
        assert np.allclose(Xc, fila["punto_camara"], atol=ej["tolerancia"])
        uvw = K @ Xc
        assert np.allclose(uvw[:2] / uvw[2], fila["uv"], atol=ej["tolerancia"])


def test_la_pieza_es_rigida_bajo_la_pose(ej):
    """Las distancias entre centros de cubos no cambian al pasar de local a mundo."""
    pz = ej["pieza"]
    loc = np.array([f["centro_local"] for f in pz["centros_de_cubos"]])
    wld = np.array([f["centro_mundo"] for f in pz["centros_de_cubos"]])
    d_loc = np.linalg.norm(loc[:, None] - loc[None], axis=-1)
    d_wld = np.linalg.norm(wld[:, None] - wld[None], axis=-1)
    assert np.allclose(d_loc, d_wld, atol=1e-12)


def test_rotacion_de_la_pose_es_exacta(ej):
    """Las rotaciones de 90° usan entradas en {-1,0,1}: no acumulan error de punto flotante."""
    R = np.array(ej["pieza"]["pose"]["rotation"], float)
    assert set(np.unique(R).tolist()) <= {-1.0, 0.0, 1.0}
    assert np.allclose(R @ R.T, np.eye(3)) and np.isclose(np.linalg.det(R), 1.0)
