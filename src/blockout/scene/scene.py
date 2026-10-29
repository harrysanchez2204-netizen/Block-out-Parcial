"""API pública del módulo A: create_scene, apply_action, get_geometry.

La escena es un valor INMUTABLE en coordenadas del mundo (docs/INTERFACES.md §2 y §4). Nadie fuera
de este archivo cambia poses: la única puerta es `apply_action`, que devuelve una escena nueva.
`get_geometry` es el único lugar donde se aplica la matriz M a los vértices.
"""
from __future__ import annotations

import numpy as np

from blockout.core.types import Action, Container, Geometry3D, Mesh3D, Piece, Pose, Scene
from blockout.scene.pieces import CATALOG, local_mesh
from blockout.scene.transforms import model_matrix, transform_points

CONTAINER_COLOR = (120, 130, 150)


def create_scene(config: dict | None = None) -> Scene:
    """config opcional {size, pieces} -> Scene inicial. Determinista: mismo config, misma escena.

    En E3 cada pieza arranca sin rotar y con su pivote cerca del techo del contenedor, como en
    Blockout. El pivote es el centro de un cubo (coordenadas x.5), de modo que con rotación
    identidad todos los cubos caen en celdas enteras del contenedor.
    Un nombre de pieza que no está en CATALOG es un error de programación: se lanza ValueError al
    arrancar, en vez de abrir la aplicación con una pieza de menos sin avisar.
    """
    config = config or {}
    size = tuple(int(s) for s in config.get("size", (5, 5, 10)))
    names = list(config.get("pieces", list(CATALOG)))

    pieces = []
    for n, name in enumerate(names):
        if name not in CATALOG:
            raise ValueError(f"pieza desconocida en config: {name!r}")
        cells, pivot, color = CATALOG[name]
        position = np.array([1.5, 1.5, size[2] - 1.5 - 2.0 * n])   # sin solapes entre piezas
        pieces.append(Piece(id=n, name=name, cells=tuple(tuple(c) for c in cells),
                            pivot_cell=pivot, pose=Pose(np.eye(3), position), color=color))
    return Scene(container=Container(size=size), pieces=tuple(pieces), active=0)


def apply_action(scene: Scene, action: Action) -> Scene:
    """(escena, acción) -> escena nueva. Nunca lanza excepción.

    E3: todavía no hay acciones implementadas (llegan en E4: select, select_next, translate,
    rotate, set_pose, set_status). Toda acción se trata como "aún no soportada" y la escena se
    devuelve sin cambios, que es exactamente lo que el contrato pide para una acción inválida.
    Así la aplicación (C) ya puede llamar a apply_action sin esperar a E4.
    """
    return scene


def container_mesh(size) -> Mesh3D:
    """(W, D, H) -> Mesh3D del contenedor en el MUNDO: rejilla en el piso y en dos paredes.

    Dibuja: rejilla del piso (Z = 0), rejilla de la pared del fondo (Y = D) y de la pared izquierda
    (X = 0), la columna de la esquina (W, 0) y el borde superior. Las paredes del frente y derecha
    quedan solo con su borde para no tapar las piezas desde la vista inicial.

    Cada línea de la rejilla se guarda como segmentos de 1 cubo y en un conjunto: así un segmento
    que pertenece a dos paredes (por ejemplo, la arista piso–fondo) aparece una sola vez y el número
    de aristas es predecible (lo comprueba tests/test_escena.py).
    """
    W, D, H = (int(s) for s in size)
    segs: set[tuple[tuple[int, int, int], tuple[int, int, int]]] = set()

    def add(a, b):
        segs.add(tuple(sorted((tuple(a), tuple(b)))))

    def grid(fixed_axis: int, fixed_value: int, n_u: int, n_v: int):
        """Rejilla de segmentos unitarios en el plano coordenado {eje fijo = valor}."""
        u_axis, v_axis = [a for a in range(3) if a != fixed_axis]
        for i in range(n_u + 1):
            for j in range(n_v + 1):
                p = [0, 0, 0]
                p[fixed_axis], p[u_axis], p[v_axis] = fixed_value, i, j
                if i < n_u:
                    q = list(p); q[u_axis] += 1; add(p, q)
                if j < n_v:
                    q = list(p); q[v_axis] += 1; add(p, q)

    grid(2, 0, W, D)          # piso Z = 0      (ejes X, Y)
    grid(1, D, W, H)          # fondo Y = D     (ejes X, Z)
    grid(0, 0, D, H)          # izquierda X = 0 (ejes Y, Z)
    for z in range(H):        # columna de la esquina (W, 0)
        add((W, 0, z), (W, 0, z + 1))
    for x in range(W):        # borde superior, lados Y = 0 e Y = D
        add((x, 0, H), (x + 1, 0, H)); add((x, D, H), (x + 1, D, H))
    for y in range(D):        # borde superior, lados X = 0 y X = W
        add((0, y, H), (0, y + 1, H)); add((W, y, H), (W, y + 1, H))

    index: dict[tuple[int, int, int], int] = {}
    verts: list[tuple[int, int, int]] = []
    edges = []
    for a, b in sorted(segs):                 # orden fijo: misma malla en cada ejecución
        ids = []
        for p in (a, b):
            if p not in index:
                index[p] = len(verts)
                verts.append(p)
            ids.append(index[p])
        edges.append(ids)
    return Mesh3D("container", np.array(verts, dtype=float), np.array(edges, dtype=int),
                  np.zeros((0, 4), dtype=int), color=CONTAINER_COLOR)


def get_geometry(scene: Scene) -> Geometry3D:
    """Scene -> Geometry3D con TODOS los vértices en coordenadas del MUNDO. Función pura.

    Para cada pieza: malla local (vértices enteros) -> se le aplica M = model_matrix(pieza).
    Orden acordado: primero el contenedor, después las piezas en orden de id.
    """
    meshes = [container_mesh(scene.container.size)]
    for i, piece in enumerate(scene.pieces):
        v_local, edges, faces = local_mesh(piece.cells)
        v_world = transform_points(model_matrix(piece), v_local)
        meshes.append(Mesh3D(piece.name, v_world, edges, faces, color=piece.color,
                             active=(i == scene.active)))
    return Geometry3D(meshes)
