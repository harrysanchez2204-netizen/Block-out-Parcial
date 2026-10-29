"""Catálogo de piezas y malla local (módulo A).

Una pieza es una lista de cubos unitarios en celdas enteras (i, j, k) de su sistema LOCAL. El cubo
(i, j, k) ocupa [i, i+1] × [j, j+1] × [k, k+1]. Ver docs/INTERFACES.md §1.2.

En E3 el catálogo tiene una sola pieza (la "L" del ejemplo compartido). E4 completa las demás
(≥ 5 distintas, ≥ 2 no planarias, requisitos R02 y R03).
"""
from __future__ import annotations

import numpy as np

# nombre -> (celdas (i, j, k), índice del cubo pivote, color RGB)
CATALOG: dict[str, tuple[list[tuple[int, int, int]], int, tuple[int, int, int]]] = {
    "L": ([(0, 0, 0), (1, 0, 0), (2, 0, 0), (0, 1, 0)], 0, (255, 170, 60)),
}

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


def local_mesh(cells) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
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
