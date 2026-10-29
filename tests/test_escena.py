"""Pruebas del módulo A (E3): matriz M, malla local, contenedor y get_geometry.

La pieza del ejemplo compartido (tests/fixtures/shared_example.json) es la referencia: si la M o los
centros de cubo no coinciden con ese archivo, el módulo A no cumple el contrato.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from blockout.core.types import Action, Container, Piece, Pose, Scene
from blockout.scene import apply_action, create_scene, get_geometry, model_matrix, rot_axis_exact
from blockout.scene.pieces import CUBE_CORNERS, local_mesh
from blockout.scene.scene import container_mesh
from blockout.scene.transforms import orthonormalize, transform_points

FIXTURE = Path(__file__).parent / "fixtures" / "shared_example.json"


@pytest.fixture(scope="module")
def ej() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _pieza_del_ejemplo(ej) -> Piece:
    pz = ej["pieza"]
    pose = Pose(np.array(pz["pose"]["rotation"], float), np.array(pz["pose"]["position"], float))
    return Piece(id=0, name=pz["nombre"], cells=tuple(tuple(c) for c in pz["cells"]),
                 pivot_cell=pz["pivot_cell"], pose=pose)


# ------------------------------------------------------------------- contra el ejemplo

def test_model_matrix_coincide_con_el_ejemplo(ej):
    M = model_matrix(_pieza_del_ejemplo(ej))
    assert np.allclose(M, np.array(ej["pieza"]["M"]), atol=ej["tolerancia"])


def test_centros_de_cubo_en_el_mundo_coinciden(ej):
    M = model_matrix(_pieza_del_ejemplo(ej))
    loc = np.array([f["centro_local"] for f in ej["pieza"]["centros_de_cubos"]])
    esperado = np.array([f["centro_mundo"] for f in ej["pieza"]["centros_de_cubos"]])
    assert np.allclose(transform_points(M, loc), esperado, atol=ej["tolerancia"])


def test_get_geometry_deja_los_cubos_donde_dice_el_ejemplo(ej):
    """Cada cubo del ejemplo debe tener sus 8 esquinas entre los vértices que entrega A."""
    sc = Scene(container=Container(), pieces=(_pieza_del_ejemplo(ej),))
    v = get_geometry(sc).meshes[1].vertices
    for fila in ej["pieza"]["centros_de_cubos"]:
        esquinas = np.array(fila["centro_mundo"]) - 0.5 + CUBE_CORNERS
        for e in esquinas:
            assert np.min(np.linalg.norm(v - e, axis=1)) < 1e-12


# ----------------------------------------------------------------------- matriz M

def test_pivote_quieto_bajo_las_24_orientaciones():
    """Para cualquier rotación de 90° compuesta, M lleva el pivote local exactamente a p."""
    p = np.array([2.5, 1.5, 6.5])
    base = Piece(0, "L", ((0, 0, 0), (1, 0, 0), (2, 0, 0), (0, 1, 0)), 2, Pose(np.eye(3), p))
    R = np.eye(3)
    for k in range(24):
        R = rot_axis_exact(k % 3, 1 + k % 2) @ R
        pz = Piece(0, "L", base.cells, 2, Pose(R, p))
        assert np.allclose(transform_points(model_matrix(pz), base.pivot_local), p)


def test_rotaciones_exactas_son_rotaciones_propias():
    for axis in range(3):
        for n in range(-4, 5):
            R = rot_axis_exact(axis, n)
            assert set(np.unique(R).tolist()) <= {-1.0, 0.0, 1.0}
            assert np.array_equal(R @ R.T, np.eye(3)) and round(np.linalg.det(R)) == 1
    # sentido positivo (mano derecha): +90° en Z lleva X a Y
    assert np.array_equal(rot_axis_exact(2, 1) @ [1, 0, 0], [0, 1, 0])
    assert np.array_equal(rot_axis_exact(0, -1), rot_axis_exact(0, 3))
    with pytest.raises(ValueError):
        rot_axis_exact(3, 1)


def test_orthonormalize_corrige_una_rotacion_ruidosa():
    R = rot_axis_exact(1, 1) + 1e-3 * np.arange(9).reshape(3, 3)
    Q = orthonormalize(R)
    assert np.allclose(Q @ Q.T, np.eye(3)) and np.isclose(np.linalg.det(Q), 1.0)
    assert np.allclose(Q, rot_axis_exact(1, 1), atol=1e-2)


# ----------------------------------------------------------------------- malla local

def test_malla_local_de_la_L():
    """L plana de 4 cubos: 20 vértices, 36 aristas y 18 caras (24 − 2·3 internas)."""
    v, e, f = local_mesh([(0, 0, 0), (1, 0, 0), (2, 0, 0), (0, 1, 0)])
    assert v.shape == (20, 3) and e.shape == (36, 2) and f.shape == (18, 4)
    assert np.array_equal(v, np.round(v))                     # vértices enteros
    assert len({tuple(sorted(x)) for x in e.tolist()}) == len(e)   # sin aristas repetidas


def test_caras_orientadas_hacia_afuera():
    """Antihoraria vista desde afuera <=> la normal (P1−P0)×(P2−P0) se aleja del centroide."""
    cells = [(0, 0, 0), (1, 0, 0), (2, 0, 0), (0, 1, 0)]
    v, _, f = local_mesh(cells)
    for quad in f:
        P = v[quad]
        n = np.cross(P[1] - P[0], P[2] - P[0])
        centro_cubo = min((np.asarray(c) + 0.5 for c in cells),
                          key=lambda c: np.linalg.norm(c - P.mean(axis=0)))
        assert np.dot(n, P.mean(axis=0) - centro_cubo) > 0


# ------------------------------------------------------------------------ contenedor

def _aristas_esperadas(W, D, H):
    """Cuenta a mano: piso + fondo + izquierda − las 3 aristas compartidas + columna + borde."""
    piso = W * (D + 1) + D * (W + 1)
    fondo = W * (H + 1) + H * (W + 1)
    izq = D * (H + 1) + H * (D + 1)
    compartidas = W + D + H          # piso∩fondo, piso∩izquierda, fondo∩izquierda
    return piso + fondo + izq - compartidas + H + W + D   # + columna (W,0) + 2 lados del borde


@pytest.mark.parametrize("size", [(5, 5, 10), (3, 4, 6), (1, 1, 1)])
def test_contenedor_tiene_las_aristas_esperadas(size):
    m = container_mesh(size)
    assert len(m.edges) == _aristas_esperadas(*size)
    assert m.faces.shape == (0, 4)
    W, D, H = size
    assert m.vertices.min(axis=0).tolist() == [0, 0, 0]
    assert m.vertices.max(axis=0).tolist() == [W, D, H]
    largos = np.linalg.norm(m.vertices[m.edges[:, 0]] - m.vertices[m.edges[:, 1]], axis=1)
    assert np.allclose(largos, 1.0)                               # segmentos unitarios


# ------------------------------------------------------------------- escena y acciones

def test_create_scene_es_determinista_y_valida():
    a, b = create_scene(), create_scene()
    assert len(a.pieces) >= 1 and a.active == 0 and a.status == "playing"
    for pa, pb in zip(a.pieces, b.pieces):
        assert np.array_equal(pa.pose.position, pb.pose.position)
    with pytest.raises(ValueError):
        create_scene({"pieces": ["no-existe"]})


def test_la_pieza_inicial_queda_dentro_del_contenedor_y_en_la_rejilla():
    sc = create_scene()
    W, D, H = sc.container.size
    geo = get_geometry(sc)
    assert geo.meshes[0].name == "container"                     # orden del contrato
    for m in geo.meshes[1:]:
        assert np.array_equal(m.vertices, np.round(m.vertices))
        assert (m.vertices >= 0).all() and (m.vertices <= [W, D, H]).all()
    assert geo.meshes[1].active is True


def test_get_geometry_no_modifica_la_escena():
    sc = create_scene()
    antes = sc.pieces[0].pose.position.copy()
    get_geometry(sc)
    assert np.array_equal(sc.pieces[0].pose.position, antes)


@pytest.mark.parametrize("accion", [Action("rotate", axis=0), Action("translate", delta=(1, 0, 0)),
                                    Action("select", piece=99), Action("no-existe")])
def test_apply_action_no_lanza_y_devuelve_una_escena(accion):
    sc = create_scene()
    assert isinstance(apply_action(sc, accion), Scene)
