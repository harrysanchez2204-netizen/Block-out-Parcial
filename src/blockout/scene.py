"""API pública del módulo A: create_scene, apply_action, get_geometry.

La escena es un valor INMUTABLE en coordenadas del mundo (docs/INTERFACES.md §2 y §4). Nadie fuera
de este archivo cambia poses: la única puerta es `apply_action`, que devuelve una escena nueva.
`get_geometry` es el único lugar donde se aplica la matriz M a los vértices.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from blockout.core.types import Action, Container, Geometry3D, Mesh3D, Piece, Pose, Scene
from blockout.scene.pieces import CATALOG, local_mesh
from blockout.scene.transforms import clean_rotation, model_matrix, rot_axis_exact, transform_points

CONTAINER_COLOR = (120, 130, 150)
STATUSES = ("playing", "victory")


# --------------------------------------------------------------------------- celdas ocupadas

def occupied_cells(piece: Piece) -> np.ndarray:
    """Pieza -> (n,3) índices enteros de las celdas del CONTENEDOR que ocupa en el mundo.

    El centro del cubo local (i,j,k) es (i,j,k) + 0.5. Se lleva al mundo con M y se le resta 0.5:
    si la pose está alineada a la rejilla, el resultado es entero. Se redondea para absorber el
    error de punto flotante (del orden de 1e-15), nunca para "arreglar" una pose desalineada.
    """
    centers = np.asarray(piece.cells, dtype=float) + 0.5
    return np.rint(transform_points(model_matrix(piece), centers) - 0.5).astype(int)


def _inside(piece: Piece, size) -> bool:
    """True si todas las celdas de la pieza están dentro de [0, W) × [0, D) × [0, H)."""
    c = occupied_cells(piece)
    return bool((c >= 0).all() and (c < np.asarray(size)).all())


# ------------------------------------------------------------------------------- creación

def create_scene(config: dict | None = None) -> Scene:
    """config opcional {size, pieces} -> Scene inicial. Determinista: mismo config, misma escena.

    Disposición inicial: las piezas se ubican sin rotar en "casillas" del contenedor, dos por nivel
    (franjas Y ∈ [0,2) e Y ∈ [3,5)) y niveles que bajan de 3 en 3 desde el techo. Ninguna pieza del
    catálogo mide más de 3×2×2 sin rotar, así que no se solapan ni se salen.
    La posición guardada es la del PIVOTE: esquina mínima de la casilla + (celda pivote − celda
    mínima) + 0.5, es decir, el centro del cubo pivote en el mundo.
    Un nombre desconocido o una escena en la que las piezas no caben es un error de configuración:
    se lanza ValueError al arrancar en vez de abrir la aplicación con piezas fuera del contenedor.
    """
    config = config or {}
    size = tuple(int(s) for s in config.get("size", (5, 5, 10)))
    names = list(config.get("pieces", list(CATALOG)))
    W, D, H = size

    pieces = []
    for n, name in enumerate(names):
        if name not in CATALOG:
            raise ValueError(f"pieza desconocida en config: {name!r}")
        cells, pivot, color = CATALOG[name]
        cells_arr = np.asarray(cells)
        slot = np.array([max(0, (W - 3) // 2), 3 * (n % 2), H - 2 - 3 * (n // 2)])
        position = slot + (cells_arr[pivot] - cells_arr.min(axis=0)) + 0.5
        piece = Piece(id=n, name=name, cells=tuple(tuple(c) for c in cells), pivot_cell=pivot,
                      pose=Pose(np.eye(3), position.astype(float)), color=color)
        if not _inside(piece, size):
            raise ValueError(f"la pieza {name!r} no cabe en un contenedor {size}")
        pieces.append(piece)
    return Scene(container=Container(size=size), pieces=tuple(pieces), active=0)


# -------------------------------------------------------------------------------- acciones

def _with_pose(scene: Scene, idx: int, pose: Pose) -> Scene:
    """Escena nueva con la pose de la pieza `idx` reemplazada (las demás se comparten, no se copian)."""
    pieces = list(scene.pieces)
    pieces[idx] = replace(pieces[idx], pose=pose)
    return replace(scene, pieces=tuple(pieces))


def _is_int(x) -> bool:
    return isinstance(x, (int, np.integer)) and not isinstance(x, bool)


def _apply(scene: Scene, a: Action) -> Scene:
    n = len(scene.pieces)

    if a.kind == "select":
        if _is_int(a.piece) and 0 <= a.piece < n:
            return replace(scene, active=int(a.piece))
        return scene                                     # sin pieza o fuera de rango
    if a.kind == "select_next":
        return replace(scene, active=(scene.active + 1) % n) if n else scene
    if a.kind == "set_status":
        return replace(scene, status=a.value) if a.value in STATUSES else scene

    # Las acciones restantes actúan sobre una pieza: la indicada o, si piece es None, la activa.
    idx = scene.active if a.piece is None else a.piece
    if not (_is_int(idx) and 0 <= idx < n):
        return scene
    piece = scene.pieces[idx]
    size = scene.container.size

    if a.kind == "translate":
        delta = np.asarray(a.delta, dtype=float)
        if delta.shape != (3,) or not np.array_equal(delta, np.rint(delta)):
            return scene                                 # solo pasos enteros: la pieza sigue en la rejilla
        moved = Pose(piece.pose.rotation, piece.pose.position + delta)
        return _with_pose(scene, idx, moved) if _inside(replace(piece, pose=moved), size) else scene

    if a.kind == "rotate":
        if not (_is_int(a.axis) and 0 <= a.axis <= 2 and _is_int(a.steps)):
            return scene
        # Ejes del MUNDO: el giro nuevo se multiplica a la IZQUIERDA de la rotación acumulada.
        # (A la derecha giraría alrededor de los ejes propios de la pieza, que ya están girados y
        # el usuario no ve.) El pivote no cambia: la posición guardada es la del pivote.
        R = clean_rotation(rot_axis_exact(int(a.axis), int(a.steps)) @ piece.pose.rotation)
        turned = Pose(R, piece.pose.position)
        return _with_pose(scene, idx, turned) if _inside(replace(piece, pose=turned), size) else scene

    if a.kind == "set_pose":
        # La usa la animación de victoria (E9): las piezas pueden salir del contenedor, así que aquí
        # no se aplican límites. Sí se exige una pose válida y se limpia la rotación (rigidez).
        p = a.pose
        if p is None:
            return scene
        R = np.asarray(p.rotation, dtype=float)
        pos = np.asarray(p.position, dtype=float)
        if R.shape != (3, 3) or pos.shape != (3,) or not (np.isfinite(R).all() and np.isfinite(pos).all()):
            return scene
        return _with_pose(scene, idx, Pose(clean_rotation(R), pos.copy()))

    return scene                                         # kind desconocido


def apply_action(scene: Scene, action: Action) -> Scene:
    """(escena, acción) -> escena NUEVA. La de entrada nunca se modifica. Nunca lanza excepción.

    Acciones (docs/INTERFACES.md §2, `Action`):
      select(piece)          cambia la pieza activa; sin pieza o fuera de rango: sin cambios.
      select_next            pasa a la siguiente pieza, volviendo a la primera al final.
      translate(delta)       mueve la pieza un número ENTERO de cubos; se rechaza si se sale.
      rotate(axis, steps)    gira 90°·steps alrededor de un eje del MUNDO por el pivote; se rechaza
                             si alguna celda queda fuera del contenedor.
      set_pose(pose)         pone una pose completa (animación). Sin límites; rotación limpiada.
      set_status(value)      "playing" o "victory".
    Cualquier otra cosa (kind desconocido, índice inválido, datos mal formados) devuelve `scene`.
    Las validaciones de `_apply` cubren los casos conocidos; el try/except es solo la red de
    seguridad que garantiza el "nunca lanza" del contrato ante datos que nadie anticipó.
    """
    if not isinstance(action, Action):
        return scene
    try:
        return _apply(scene, action)
    except (TypeError, ValueError, IndexError, np.linalg.LinAlgError):
        return scene


# ---------------------------------------------------------------------------- geometría

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
