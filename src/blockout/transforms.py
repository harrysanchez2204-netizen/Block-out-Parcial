"""Transformaciones rígidas del módulo A (escena y geometría).

Aquí vive la matriz M de la cadena del enunciado:

    λ [u v 1]ᵀ = K [R | t] · M · [X Y Z 1]ᵀ
                             └── este archivo

M (4x4) lleva un punto de las coordenadas LOCALES de una pieza a coordenadas del MUNDO.
Ver docs/INTERFACES.md §1.2 y §1.5.
"""
from __future__ import annotations

import numpy as np

from blockout.core.types import Piece


def rot_axis_exact(axis: int, quarter_turns: int) -> np.ndarray:
    """(eje 0/1/2, giros de 90° con signo) -> rotación (3,3) con entradas exactas en {-1, 0, 1}.

    Por qué exacta: cos y sen de múltiplos de 90° solo valen -1, 0 o 1. Si se calcularan con
    np.cos(np.pi/2) saldría 6.1e-17 en vez de 0, y al componer muchas rotaciones ese error se
    acumula: los vértices dejarían de caer en enteros y la pieza se saldría de la cuadrícula.
    `quarter_turns` se toma módulo 4 (−1 equivale a 3).
    """
    n = quarter_turns % 4
    c = (1, 0, -1, 0)[n]          # cos(90°·n)
    s = (0, 1, 0, -1)[n]          # sen(90°·n)
    if axis == 0:                 # alrededor de X: mueve Y→Z
        m = [[1, 0, 0], [0, c, -s], [0, s, c]]
    elif axis == 1:               # alrededor de Y: mueve Z→X
        m = [[c, 0, s], [0, 1, 0], [-s, 0, c]]
    elif axis == 2:               # alrededor de Z: mueve X→Y
        m = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
    else:
        raise ValueError(f"eje inválido: {axis} (debe ser 0, 1 o 2)")
    return np.array(m, dtype=float)


def rot_axis_angle(axis_vec, angle_rad: float) -> np.ndarray:
    """(eje cualquiera (3,), ángulo en radianes) -> rotación (3,3). Fórmula de Rodrigues.

    Con a el eje unitario y [a]ₓ su matriz de producto cruz ([a]ₓ·v = a × v):
        R = I + sen(θ)·[a]ₓ + (1 − cos(θ))·[a]ₓ²
    Es para rotaciones CONTINUAS (la animación de victoria, E9). Las piezas que maneja el usuario
    giran con rot_axis_exact, que no acumula error.
    """
    a = np.asarray(axis_vec, dtype=float)
    n = np.linalg.norm(a)
    if n < 1e-12:
        raise ValueError("el eje de rotación no puede ser el vector cero")
    a = a / n
    Kx = np.array([[0.0, -a[2], a[1]],
                   [a[2], 0.0, -a[0]],
                   [-a[1], a[0], 0.0]])
    return np.eye(3) + np.sin(angle_rad) * Kx + (1.0 - np.cos(angle_rad)) * (Kx @ Kx)


def orthonormalize(R: np.ndarray) -> np.ndarray:
    """(3,3) casi-rotación -> la rotación propia más cercana (SVD, det = +1).

    Si R = U Σ Vᵀ, la matriz ortogonal más cercana en norma de Frobenius es U Vᵀ (se tiran los
    valores singulares). Si sale det = −1 (una reflexión), se invierte la última columna de U.
    Con rotaciones exactas de 90° no cambia nada; está para las rotaciones continuas (E9).
    """
    U, _, Vt = np.linalg.svd(R)
    Q = U @ Vt
    if np.linalg.det(Q) < 0:
        U = U.copy()
        U[:, -1] *= -1
        Q = U @ Vt
    return Q


def clean_rotation(R: np.ndarray, snap_tol: float = 1e-9) -> np.ndarray:
    """(3,3) -> rotación propia; si está a < snap_tol de una matriz entera, devuelve esa exacta.

    Por qué los dos pasos:
      1. `orthonormalize` (SVD) garantiza RᵀR = I y det = +1: la pieza no se deforma (rigidez).
      2. La SVD la calcula la librería de álgebra lineal instalada (OpenBLAS, MKL…), que no es la
         misma en Linux y en Windows. Aunque en una máquina devuelva una rotación de 90° exacta, en
         otra podría salir 0.9999999999999998. Si la matriz está a menos de `snap_tol` de una con
         entradas en {-1, 0, 1}, se toma esa: así las rotaciones de pieza siguen exactas y los
         vértices siguen cayendo en enteros en cualquier sistema operativo.
    Las rotaciones continuas de la animación (E9) no están cerca de una entera y no se redondean.
    """
    Q = orthonormalize(np.asarray(R, dtype=float))
    Qi = np.rint(Q)
    if np.abs(Q - Qi).max() < snap_tol:
        return Qi + 0.0                    # + 0.0 convierte un posible −0.0 en 0.0
    return Q


def model_matrix(piece: Piece) -> np.ndarray:
    """Pieza -> M (4,4), de coordenadas locales de la pieza a coordenadas del mundo.

    Queremos girar la pieza alrededor de su pivote y dejar el pivote en `pose.position`:

        X_world = R · (X_local − pivot_local) + p
                = R · X_local + (p − R · pivot_local)

    En homogéneas eso es una sola matriz:

        M = [[R, p − R·pivot_local],
             [0,          1       ]]

    Comprobación: M · [pivot_local, 1] = R·pivot + p − R·pivot = p. El pivote no se mueve al rotar.
    """
    R = np.asarray(piece.pose.rotation, dtype=float)
    p = np.asarray(piece.pose.position, dtype=float)
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = p - R @ piece.pivot_local
    return M


def to_homogeneous(pts: np.ndarray) -> np.ndarray:
    """(N,3) -> (N,4) agregando una columna de unos (w = 1: son puntos, no direcciones)."""
    pts = np.atleast_2d(np.asarray(pts, dtype=float))
    return np.hstack([pts, np.ones((len(pts), 1))])


def transform_points(M: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """M (4,4) y puntos (N,3) -> puntos transformados (N,3).

    Cada punto es un vector columna X, así que el resultado es M·X. Con los puntos apilados como
    filas (N,4), eso se escribe X_filas · Mᵀ. Como M es afín (última fila [0 0 0 1]), w sigue
    siendo 1 y basta quedarse con las tres primeras columnas, sin dividir.
    """
    return (to_homogeneous(pts) @ np.asarray(M, dtype=float).T)[:, :3]
