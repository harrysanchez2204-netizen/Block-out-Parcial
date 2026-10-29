"""Pruebas del módulo A en E4: catálogo de piezas y acciones sobre la escena.

Requisitos que se verifican aquí: R02 (≥ 5 piezas distintas), R03 (≥ 2 no planarias),
R04 (seleccionar y trasladar), R05 (rotar en tres ejes), R06 (pivote y rigidez) y P2 (límites).
"""
from __future__ import annotations

import numpy as np
import pytest

from blockout.core.types import Action, Pose, Scene
from blockout.scene import apply_action, create_scene, get_geometry, model_matrix, rot_axis_exact
from blockout.scene.pieces import CATALOG, all_rotations, canonical_form, is_connected, is_planar
from blockout.scene.scene import occupied_cells
from blockout.scene.transforms import clean_rotation, rot_axis_angle


def _cells(scene: Scene, i: int) -> set:
    return set(map(tuple, occupied_cells(scene.pieces[i]).tolist()))


# =========================================================================== catálogo (R02, R03)

def test_hay_al_menos_cinco_piezas_y_dos_no_planarias():
    assert len(CATALOG) >= 5
    no_planarias = [n for n, (c, _, _) in CATALOG.items() if not is_planar(c)]
    assert len(no_planarias) >= 2, no_planarias


def test_is_planar_distingue_los_casos():
    assert is_planar([(0, 0, 0), (1, 0, 0), (2, 0, 0)])                 # recta (rango 1)
    assert is_planar([(0, 0, 0), (1, 0, 0), (0, 0, 1), (1, 0, 1)])      # cuadrado vertical
    assert not is_planar([(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)])  # trípode


def test_las_piezas_son_distintas_aunque_se_roten():
    """Ningún par es la misma forma vista desde otro lado (misma forma canónica)."""
    formas = {n: canonical_form(c) for n, (c, _, _) in CATALOG.items()}
    assert len(set(formas.values())) == len(formas), formas


def test_forma_canonica_no_depende_de_la_orientacion_ni_la_posicion():
    cells = np.array(CATALOG["Tornillo"][0])
    for R in all_rotations():
        assert canonical_form(cells @ R.T + [7, -3, 2]) == canonical_form(cells)


def test_son_24_rotaciones_propias_distintas():
    rots = all_rotations()
    assert len(rots) == 24
    assert len({tuple(R.ravel()) for R in rots}) == 24
    assert all(np.isclose(np.linalg.det(R), 1) for R in rots)


def test_cada_pieza_es_conexa_y_su_pivote_es_valido():
    for name, (cells, pivot, color) in CATALOG.items():
        assert is_connected(cells), name
        assert 0 <= pivot < len(cells), name
        assert len(set(map(tuple, cells))) == len(cells), name           # sin cubos repetidos
        assert len(color) == 3
    assert not is_connected([(0, 0, 0), (2, 0, 0)])


# =========================================================================== escena inicial

def test_escena_inicial_dentro_y_sin_solapes():
    sc = create_scene()
    assert len(sc.pieces) == len(CATALOG)
    vistos = set()
    W, D, H = sc.container.size
    for i in range(len(sc.pieces)):
        c = occupied_cells(sc.pieces[i])
        assert (c >= 0).all() and (c < [W, D, H]).all(), sc.pieces[i].name
        assert not (vistos & _cells(sc, i)), sc.pieces[i].name
        vistos |= _cells(sc, i)


def test_escena_inicial_es_determinista():
    a, b = create_scene(), create_scene()
    for pa, pb in zip(a.pieces, b.pieces):
        assert np.array_equal(pa.pose.position, pb.pose.position)
        assert np.array_equal(pa.pose.rotation, pb.pose.rotation)


def test_config_imposible_falla_al_arrancar():
    with pytest.raises(ValueError):
        create_scene({"size": (2, 2, 2)})


# =========================================================================== selección (R04)

def test_select_y_select_next():
    sc = create_scene()
    n = len(sc.pieces)
    assert apply_action(sc, Action("select", piece=3)).active == 3
    assert apply_action(sc, Action("select", piece=n)).active == 0            # fuera de rango
    assert apply_action(sc, Action("select", piece=-1)).active == 0
    assert apply_action(sc, Action("select")).active == 0                     # sin pieza
    s = sc
    for k in range(1, n + 2):
        s = apply_action(s, Action("select_next"))
        assert s.active == k % n                                             # vuelve al inicio
    geo = get_geometry(apply_action(sc, Action("select", piece=2)))
    assert [m.active for m in geo.meshes[1:]] == [i == 2 for i in range(n)]


# =========================================================================== traslación (R04, P2)

def test_translate_mueve_un_numero_entero_de_cubos():
    sc = apply_action(create_scene(), Action("select", piece=1))
    antes = sc.pieces[1].pose.position.copy()
    sc2 = apply_action(sc, Action("translate", delta=(0, 0, -1)))
    assert np.allclose(sc2.pieces[1].pose.position, antes + [0, 0, -1])
    assert np.array_equal(sc.pieces[1].pose.position, antes)                 # la original no cambia
    assert np.allclose(sc2.pieces[0].pose.position, sc.pieces[0].pose.position)   # las demás tampoco


def test_translate_por_indice_no_cambia_la_seleccion():
    sc = create_scene()
    sc2 = apply_action(sc, Action("translate", piece=4, delta=(0, 0, -1)))
    assert sc2.active == 0 and not np.allclose(sc2.pieces[4].pose.position, sc.pieces[4].pose.position)


@pytest.mark.parametrize("delta", [(0.5, 0, 0), (1, 2), "abc", (np.nan, 0, 0)])
def test_translate_rechaza_pasos_no_enteros_o_mal_formados(delta):
    sc = create_scene()
    assert apply_action(sc, Action("translate", delta=delta)) is sc


def test_no_se_sale_del_contenedor_por_ningun_lado():
    sc = create_scene()
    W, D, H = sc.container.size
    for d in [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]:
        s = sc
        for _ in range(2 * max(W, D, H)):                                    # empujar contra la pared
            s = apply_action(s, Action("translate", delta=d))
        c = occupied_cells(s.pieces[0])
        assert (c >= 0).all() and (c < [W, D, H]).all()
        assert (c.min(axis=0) == 0).any() or (c.max(axis=0) == np.array([W, D, H]) - 1).any()


# =========================================================================== rotación (R05, R06)

def test_rotar_37_veces_sigue_siendo_rigida_y_exacta():
    sc = create_scene()
    sc = apply_action(sc, Action("translate", delta=(0, 1, -4)))             # espacio para girar
    v0 = get_geometry(sc).meshes[1].vertices
    d0 = np.linalg.norm(v0[:, None] - v0[None], axis=-1)
    girados = 0
    for k in range(37):
        nuevo = apply_action(sc, Action("rotate", axis=k % 3, steps=1 + k % 3))
        girados += nuevo is not sc
        sc = nuevo
    assert girados > 30                                                      # casi todos caben
    R = sc.pieces[0].pose.rotation
    assert set(np.unique(R).tolist()) <= {-1.0, 0.0, 1.0}                    # exacta
    assert np.array_equal(R @ R.T, np.eye(3)) and round(np.linalg.det(R)) == 1
    v1 = get_geometry(sc).meshes[1].vertices
    assert np.allclose(np.linalg.norm(v1[:, None] - v1[None], axis=-1), d0, atol=1e-12)
    assert np.array_equal(v1, np.round(v1))                                  # sigue en la rejilla


def test_el_pivote_queda_quieto_al_rotar():
    sc = apply_action(create_scene(), Action("translate", delta=(0, 1, -4)))
    pivote = sc.pieces[0].pose.position.copy()
    for axis in range(3):
        s = apply_action(sc, Action("rotate", axis=axis, steps=1))
        assert s is not sc
        p = s.pieces[0]
        assert np.allclose((model_matrix(p) @ np.append(p.pivot_local, 1))[:3], pivote)


def test_rotacion_alrededor_de_ejes_del_mundo():
    """Girar en Z y luego en X da R = Rx · Rz (el giro nuevo va a la IZQUIERDA)."""
    sc = apply_action(create_scene(), Action("translate", delta=(0, 1, -4)))
    s = apply_action(sc, Action("rotate", axis=2, steps=1))
    s = apply_action(s, Action("rotate", axis=0, steps=1))
    assert np.array_equal(s.pieces[0].pose.rotation, rot_axis_exact(0, 1) @ rot_axis_exact(2, 1))


def test_cuatro_cuartos_de_vuelta_vuelven_al_inicio():
    sc = apply_action(create_scene(), Action("translate", delta=(0, 1, -4)))
    for axis in range(3):
        s = sc
        for _ in range(4):
            s = apply_action(s, Action("rotate", axis=axis, steps=1))
        assert np.array_equal(s.pieces[0].pose.rotation, np.eye(3))
        assert _cells(s, 0) == _cells(sc, 0)


def test_una_rotacion_que_saldria_del_contenedor_se_rechaza():
    """La "I" (3 cubos en X, pivote en el del medio) acostada en el piso no puede pararse:
    girarla en Y la pondría de z = −1 a z = 1. Un nivel más arriba sí cabe."""
    sc = create_scene()
    piso = sc
    while (nuevo := apply_action(piso, Action("translate", delta=(0, 0, -1)))) is not piso:
        piso = nuevo                                             # bajar hasta que el piso lo impida
    assert occupied_cells(piso.pieces[0])[:, 2].tolist() == [0, 0, 0]
    assert apply_action(piso, Action("rotate", axis=1, steps=1)) is piso          # rechazada
    arriba = apply_action(piso, Action("translate", delta=(0, 0, 1)))
    parada = apply_action(arriba, Action("rotate", axis=1, steps=1))
    assert parada is not arriba
    assert sorted(occupied_cells(parada.pieces[0])[:, 2].tolist()) == [0, 1, 2]   # ahora vertical


@pytest.mark.parametrize("axis,steps", [(3, 1), (-1, 1), (None, 1), (0, 1.5), (True, 1)])
def test_rotate_con_datos_invalidos_no_cambia_nada(axis, steps):
    sc = create_scene()
    assert apply_action(sc, Action("rotate", axis=axis, steps=steps)) is sc


# =========================================================================== set_pose y set_status

def test_set_pose_pone_la_pose_y_limpia_la_rotacion():
    sc = create_scene()
    R = rot_axis_angle([0.3, 0.5, 1.0], 0.7) + 1e-6                # rotación continua con ruido
    s = apply_action(sc, Action("set_pose", piece=2, pose=Pose(R, np.array([20.0, -5.0, 3.0]))))
    Q = s.pieces[2].pose.rotation
    assert np.allclose(Q @ Q.T, np.eye(3), atol=1e-12) and np.isclose(np.linalg.det(Q), 1)
    assert np.allclose(s.pieces[2].pose.position, [20, -5, 3])    # sin límites: la animación sale


def test_set_pose_exacta_sigue_exacta():
    sc = create_scene()
    R = rot_axis_exact(1, 1) + 1e-13                                # ruido de otra plataforma
    s = apply_action(sc, Action("set_pose", piece=0, pose=Pose(R, sc.pieces[0].pose.position)))
    assert set(np.unique(s.pieces[0].pose.rotation).tolist()) <= {-1.0, 0.0, 1.0}


@pytest.mark.parametrize("pose", [None, Pose(np.eye(2), np.zeros(3)),
                                  Pose(np.eye(3), np.array([np.inf, 0, 0]))])
def test_set_pose_invalida_no_cambia_nada(pose):
    sc = create_scene()
    assert apply_action(sc, Action("set_pose", piece=0, pose=pose)) is sc


def test_set_status():
    sc = create_scene()
    assert apply_action(sc, Action("set_status", value="victory")).status == "victory"
    assert apply_action(sc, Action("set_status", value="ganamos")) is sc


def test_clean_rotation_redondea_solo_lo_casi_entero():
    assert np.array_equal(clean_rotation(rot_axis_exact(2, 1) * (1 + 1e-12)), rot_axis_exact(2, 1))
    R = rot_axis_angle([0, 0, 1], 0.3)
    assert np.allclose(clean_rotation(R), R)                        # una rotación de 17° no se toca


# =========================================================================== nunca lanza

def test_mil_acciones_al_azar_nunca_lanzan_ni_rompen_invariantes():
    """Semilla fija: la prueba es reproducible. Mezcla acciones válidas y basura."""
    rng = np.random.default_rng(2026)
    sc = create_scene()
    W, D, H = sc.container.size
    kinds = ["select", "select_next", "translate", "rotate", "set_status", "nada", "rotate"]
    for _ in range(1000):
        k = kinds[rng.integers(len(kinds))]
        a = Action(k, piece=int(rng.integers(-2, 9)) if rng.random() < 0.5 else None,
                   axis=int(rng.integers(-1, 4)), steps=int(rng.integers(-5, 6)),
                   delta=tuple(int(x) for x in rng.integers(-2, 3, 3)),
                   value=["playing", "victory", "x"][rng.integers(3)])
        antes = [p.pose.position.copy() for p in sc.pieces]
        nuevo = apply_action(sc, a)
        assert isinstance(nuevo, Scene)
        assert all(np.array_equal(p.pose.position, q) for p, q in zip(sc.pieces, antes))  # inmutable
        sc = nuevo
        for i, p in enumerate(sc.pieces):
            c = occupied_cells(p)
            assert (c >= 0).all() and (c < [W, D, H]).all()
            assert set(np.unique(p.pose.rotation).tolist()) <= {-1.0, 0.0, 1.0}
    assert apply_action(sc, "no soy una acción") is sc                     # type: ignore[arg-type]
