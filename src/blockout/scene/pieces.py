"""Catálogo de piezas y malla local (módulo A).

Una pieza es una lista de cubos unitarios en celdas enteras (i, j, k) de su sistema LOCAL. El cubo
(i, j, k) ocupa [i, i+1] × [j, j+1] × [k, k+1]. Ver docs/INTERFACES.md §1.2.

E4: seis piezas (R02 pide ≥ 5 distintas) y dos de ellas no planarias (R03 pide ≥ 2). Las dos
propiedades no se afirman a ojo: `is_planar` y `canonical_form` permiten comprobarlas en las pruebas.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from blockout.scene.transforms import rot_axis_exact

# nombre -> (celdas (i, j, k), índice del cubo pivote, color RGB)
# El pivote es el cubo alrededor del cual "se siente natural" girar: el del medio cuando lo hay.
# La "L" conserva pivote 0 para coincidir con la pieza del ejemplo compartido.
CATALOG: dict[str, tuple[list[tuple[int, int, int]], int, tuple[int, int, int]]] = {
    "I":        ([(0, 0, 0), (1, 0, 0), (2, 0, 0)],            1, (80, 200, 255)),   # planaria
    "L":        ([(0, 0, 0), (1, 0, 0), (2, 0, 0), (0, 1, 0)], 0, (255, 170, 60)),   # planaria
    "O":        ([(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)], 0, (255, 230, 80)),   # planaria
    "T":        ([(0, 0, 0), (1, 0, 0), (2, 0, 0), (1, 1, 0)], 1, (190, 120, 255)),  # planaria
    "Tripode":  ([(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)], 0, (120, 230, 120)),  # NO planaria
    "Tornillo": ([(0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 1, 1)], 1, (255, 100, 120)),  # NO planaria
}


def is_planar(cells) -> bool:
    """celdas -> True si todos los centros de cubo caben en un mismo plano.

    Se restan el promedio y se mira el rango de la matriz (n, 3) resultante:
      rango ≤ 1 -> los centros están en una recta;  rango 2 -> en un plano;  rango 3 -> ocupan 3D.
    Una pieza es "no planaria" (R03) cuando el rango es 3: no hay plano que contenga todos sus cubos.
    """
    c = np.asarray(cells, dtype=float)
    return int(np.linalg.matrix_rank(c - c.mean(axis=0))) <= 2


def all_rotations() -> list[np.ndarray]:
    """Las 24 rotaciones propias del cubo, como matrices exactas.

    Se generan componiendo giros de 90° en X, Y y Z hasta que no aparecen nuevas (es el grupo de
    rotaciones del cubo, que tiene 24 elementos: 6 caras que pueden quedar arriba × 4 giros).
    """
    found = {tuple(np.eye(3).ravel())}
    frontier = [np.eye(3)]
    gens = [rot_axis_exact(a, 1) for a in range(3)]
    while frontier:
        nxt = []
        for R in frontier:
            for G in gens:
                Q = G @ R
                key = tuple(Q.ravel())
                if key not in found:
                    found.add(key)
                    nxt.append(Q)
        frontier = nxt
    return [np.array(k).reshape(3, 3) for k in sorted(found)]


def _normalized(cells: np.ndarray) -> tuple:
    """Traslada las celdas para que la mínima quede en (0,0,0) y las ordena: forma comparable."""
    c = np.rint(cells).astype(int)
    c = c - c.min(axis=0)
    return tuple(sorted(map(tuple, c.tolist())))


def canonical_form(cells) -> tuple:
    """celdas -> representante único de la forma, sin importar posición ni orientación.

    Se rota la pieza con las 24 rotaciones, se lleva cada resultado a su esquina mínima y se toma el
    menor en orden lexicográfico. Dos piezas tienen la misma forma canónica si y solo si una se
    obtiene de la otra con una rotación y una traslación. Así se comprueba que las seis son distintas.
    (Una pieza y su imagen en espejo cuentan como distintas: un espejo no es una rotación.)
    """
    c = np.asarray(cells, dtype=float)
    return min(_normalized(c @ R.T) for R in all_rotations())


def is_connected(cells) -> bool:
    """celdas -> True si todos los cubos se tocan por caras formando una sola pieza (BFS)."""
    cells = {tuple(c) for c in cells}
    if not cells:
        return False
    start = next(iter(cells))
    seen, stack = {start}, [start]
    while stack:
        x, y, z = stack.pop()
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = (x + d[0], y + d[1], z + d[2])
            if n in cells and n not in seen:
                seen.add(n)
                stack.append(n)
    return len(seen) == len(cells)

# Las 8 esquinas de un cubo unitario. El índice codifica la esquina en binario:
# bit 0 = x, bit 1 = y, bit 2 = z.  Ej.: 5 = 0b101 -> (1, 0, 1).
CUBE_CORNERS = np.array([[i & 1, (i >> 1) & 1, (i >> 2) & 1] for i in range(8)], dtype=float)

# 12 aristas: pares de esquinas que difieren en exactamente un bit (una sola coordenada).
CUBE_EDGES = [(0, 1), (2, 3), (4, 5), (6, 7),      # paralelas a X
              (0, 2), (1, 3), (4, 6), (5, 7),      # paralelas a Y
              (0, 4), (1, 5), (2, 6), (3, 7)]      # paralelas a Z

# 6 caras como cuadriláteros recorridos por el borde (sin cruzarse). La orientación se corrige
# en `local_mesh` para que quede hacia afuera.
CUBE_FACES = [(0, 1, 3, 2), (4, 5, 7, 6),          # z = 0, z = 1
              (0, 1, 5, 4), (2, 3, 7, 6),          # y = 0, y = 1
              (0, 2, 6, 4), (1, 3, 7, 5)]          # x = 0, x = 1


def _build_local_mesh(cells) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """celdas -> (vértices (N,3), aristas (E,2), caras (F,4)) en coordenadas LOCALES.

    * Los vértices compartidos entre cubos vecinos se guardan una sola vez (diccionario por
      coordenada entera), así la pieza es una sola malla y no 4 cubos sueltos.
    * Las aristas compartidas también se guardan una vez (se usa un conjunto de pares ordenados).
    * Una cara compartida por dos cubos queda DENTRO de la pieza: se elimina. Así solo quedan
      caras de la superficie, lo que necesitará el descarte de caras traseras (E5, R16).
    * Cada cara queda antihoraria vista desde afuera: su normal (regla de la mano derecha,
      (P1 − P0) × (P2 − P0)) apunta hacia afuera del cubo al que pertenece.
    """
    index: dict[tuple[int, int, int], int] = {}
    verts: list[tuple[int, int, int]] = []
    edges: set[tuple[int, int]] = set()
    face_count: dict[tuple[int, ...], int] = {}
    face_list: list[tuple[tuple[int, ...], list[int]]] = []

    def vid(p) -> int:
        key = tuple(int(round(x)) for x in p)
        if key not in index:
            index[key] = len(verts)
            verts.append(key)
        return index[key]

    for cell in cells:
        base = np.asarray(cell, dtype=float)
        ids = [vid(base + corner) for corner in CUBE_CORNERS]
        center = base + 0.5
        for a, b in CUBE_EDGES:
            edges.add(tuple(sorted((ids[a], ids[b]))))
        for face in CUBE_FACES:
            q = [ids[k] for k in face]
            P = np.array([verts[i] for i in q], dtype=float)
            normal = np.cross(P[1] - P[0], P[2] - P[0])
            if np.dot(normal, P.mean(axis=0) - center) < 0:     # apunta hacia adentro: invertir
                q = q[::-1]
            key = tuple(sorted(q))
            face_count[key] = face_count.get(key, 0) + 1
            face_list.append((key, q))

    faces = [q for key, q in face_list if face_count[key] == 1]   # sin caras internas
    return (np.array(verts, dtype=float),
            np.array(sorted(edges), dtype=int).reshape(-1, 2),
            np.array(faces, dtype=int).reshape(-1, 4))


@lru_cache(maxsize=64)
def _cached_local_mesh(key: tuple) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Malla local construida UNA vez por forma de pieza, con arreglos de solo lectura."""
    arrays = _build_local_mesh(key)
    for a in arrays:
        a.setflags(write=False)
    return arrays


def local_mesh(cells) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """celdas -> (vértices (N,3), aristas (E,2), caras (F,4)) en coordenadas LOCALES. Ver _build_local_mesh.

    E9: la forma de una pieza nunca cambia (solo cambia su pose), pero get_geometry la pedía en cada
    fotograma: era el 31 % del tiempo de un fotograma de la demo. Ahora se construye una vez por forma
    y se reutiliza. Los arreglos devueltos son de SOLO LECTURA: si alguien intenta modificarlos, numpy
    lanza ValueError en vez de dañar en silencio la malla de todos los fotogramas siguientes.
    """
    key = tuple(tuple(int(round(x)) for x in c) for c in cells)
    return _cached_local_mesh(key)
