"""Homografía inducida por un plano (módulo B, E7). Requisitos R18–R20, enunciado §3.

Tres matrices que el enunciado pide no confundir:

    M  (4×4, invertible)  transformación 3D: mueve puntos en el espacio (model_matrix, módulo A)
    P  (3×4, rango 3)     proyección de cámara K[R|t]: lleva 3D a la imagen. NO es invertible y
                          NO es una homografía: pierde la profundidad.
    H  (3×3, invertible)  homografía: lleva la imagen de UN PLANO en una vista a su imagen en otra.

Derivación (docs/INFORME.md §2). Un plano del mundo se escribe X = O + a·e1 + b·e2. Proyectándolo:

    λ x = K [R | t] (O + a e1 + b e2, 1)ᵀ = K [R e1 | R e2 | R O + t] (a, b, 1)ᵀ = Hᵢ (a, b, 1)ᵀ

Para el piso Z = 0 (O = 0, e1 = X, e2 = Y) queda Hᵢ = K [r1 | r2 | t]: P sin su tercera columna,
porque Z = 0 la anula. Cada vista tiene su Hᵢ (3×3) y, eliminando (a, b) entre las dos:

    x2 ~ H2 H1⁻¹ x1    =>    H21 = H2 · H1⁻¹       (definida salvo escala; se normaliza H[2,2] = 1)

Todo se hace con numpy a mano. cv2 no se usa (se permitiría solo para contrastar en pruebas).
"""
from __future__ import annotations

import numpy as np

from blockout.core.types import Camera

# Plano del experimento: el piso del contenedor ("fondo del pozo", enunciado §3 paso 1).
FLOOR_PLANE = dict(origin=(0.0, 0.0, 0.0), e1=(1.0, 0.0, 0.0), e2=(0.0, 1.0, 0.0))

# |det| de H normalizada (en píxeles) por debajo del cual la vista ve el plano "de canto":
# la cámara está sobre el plano y todas sus líneas colapsan en una recta de la imagen.
_DEGENERATE_TOL = 1e-9


def plane_to_image_homography(cam: Camera, origin, e1, e2) -> np.ndarray:
    """Cámara y plano X = origin + a·e1 + b·e2 (mundo) -> H (3,3) de (a, b, 1) a píxeles (u, v, 1).

    Las tres columnas son: K·R·e1 (imagen de la dirección e1), K·R·e2 (imagen de e2) y
    K·(R·origin + t) (imagen del origen del plano). Para el piso: H = K [r1 | r2 | t].
    """
    origin, e1, e2 = (np.asarray(v, dtype=float) for v in (origin, e1, e2))
    cols = np.column_stack([cam.R @ e1, cam.R @ e2, cam.R @ origin + cam.t])
    return cam.K @ cols


def _check_not_degenerate(H: np.ndarray, which: str) -> None:
    """Lanza ValueError si H es singular: la cámara está contenida en el plano (lo ve de canto)."""
    Hn = H / np.linalg.norm(H)
    if abs(np.linalg.det(Hn)) < _DEGENERATE_TOL:
        raise ValueError(f"la cámara {which} está sobre el plano: su homografía es singular")


def homography_between_views(cam1: Camera, cam2: Camera, origin, e1, e2) -> np.ndarray:
    """H21 (3,3) tal que x2 ~ H21·x1 para los puntos DEL PLANO. H21 = H2·H1⁻¹, con H21[2,2] = 1.

    Por qué se puede invertir H1: es invertible salvo que el centro de la cámara 1 esté en el plano.
    En ese caso lanza ValueError en vez de devolver números sin sentido.
    """
    H1 = plane_to_image_homography(cam1, origin, e1, e2)
    H2 = plane_to_image_homography(cam2, origin, e1, e2)
    _check_not_degenerate(H1, "1")
    _check_not_degenerate(H2, "2")
    H = H2 @ np.linalg.inv(H1)
    return H / H[2, 2]


def homography_from_plane_normal(cam1: Camera, cam2: Camera, n_world, d_world) -> np.ndarray:
    """Fórmula general H21 = K2 (R + t·nᵀ/d) K1⁻¹, para comprobar la anterior por otro camino.

    El plano es nᵀX = d en el MUNDO. (R, t) es el movimiento de la cámara 1 a la 2:
        X_c2 = R · X_c1 + t,   con R = R2·R1ᵀ  y  t = t2 − R·t1.
    El plano en coordenadas de la cámara 1 es n1ᵀ X_c1 = d1 con n1 = R1·n y d1 = d + n1ᵀ t1.
    Para un punto del plano, 1 = n1ᵀ X_c1 / d1, así que X_c2 = (R + t n1ᵀ/d1) X_c1, y
    multiplicando por K2 y K1⁻¹ a cada lado queda la fórmula.
    """
    n = np.asarray(n_world, dtype=float)
    R = cam2.R @ cam1.R.T
    t = cam2.t - R @ cam1.t
    n1 = cam1.R @ n
    d1 = float(d_world) + n1 @ cam1.t
    H = cam2.K @ (R + np.outer(t, n1) / d1) @ np.linalg.inv(cam1.K)
    return H / H[2, 2]


def pure_rotation_homography(cam1: Camera, cam2: Camera) -> np.ndarray:
    """H21 = K2 R K1⁻¹ para dos cámaras con el MISMO centro (la 2 solo gira respecto de la 1).

    Con t = 0 el término t·nᵀ/d desaparece: H ya no depende de ningún plano y vale para TODOS los
    puntos de la escena, estén o no en el piso (enunciado §3 paso 4: el problema es el cambio de centro).
    """
    if not np.allclose(cam1.center, cam2.center, atol=1e-9):
        raise ValueError("las cámaras no comparten centro: K2 R K1⁻¹ no es válida")
    H = cam2.K @ (cam2.R @ cam1.R.T) @ np.linalg.inv(cam1.K)
    return H / H[2, 2]


def apply_homography(H: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """H (3,3) y puntos (N,2) en píxeles -> puntos transformados (N,2), con división por la 3ª coord."""
    p = np.atleast_2d(np.asarray(pts, dtype=float))
    q = np.hstack([p, np.ones((len(p), 1))]) @ H.T
    return q[:, :2] / q[:, 2:3]


def _hartley_normalize(pts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Puntos (N,2) -> (puntos normalizados, T) con centroide en 0 y distancia media √2 al origen.

    Sin esto, las filas de A mezclan números de ~1 con números de ~10⁶ (u·x en píxeles²) y la SVD
    pierde precisión: es la normalización de Hartley que hace estable al DLT.
    """
    c = pts.mean(axis=0)
    s = np.sqrt(2.0) / np.mean(np.linalg.norm(pts - c, axis=1))
    T = np.array([[s, 0.0, -s * c[0]], [0.0, s, -s * c[1]], [0.0, 0.0, 1.0]])
    return apply_homography(T, pts), T


def estimate_homography_dlt(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """≥ 4 correspondencias src -> dst (sin 3 colineales) -> H (3,3) estimada, H[2,2] = 1.

    DLT: de x' ~ H x salen dos ecuaciones lineales en las 9 entradas h de H por cada punto:
        [−x −y −1  0  0  0  u'x u'y u'] h = 0
        [ 0  0  0 −x −y −1  v'x v'y v'] h = 0
    Con N puntos, A (2N×9) h = 0. h es el vector singular de A con el menor valor singular (la
    solución de mínimos cuadrados con ‖h‖ = 1). Con exactamente 4 puntos la solución es exacta.
    """
    src = np.asarray(src, dtype=float)
    dst = np.asarray(dst, dtype=float)
    if len(src) < 4 or len(src) != len(dst):
        raise ValueError("se necesitan al menos 4 correspondencias, la misma cantidad en cada vista")
    if has_three_collinear(src) or has_three_collinear(dst):
        raise ValueError("hay 3 puntos colineales: el DLT queda mal condicionado")
    s, Ts = _hartley_normalize(src)
    d, Td = _hartley_normalize(dst)
    A = []
    for (x, y), (u, v) in zip(s, d):
        A.append([-x, -y, -1.0, 0.0, 0.0, 0.0, u * x, u * y, u])
        A.append([0.0, 0.0, 0.0, -x, -y, -1.0, v * x, v * y, v])
    _, _, Vt = np.linalg.svd(np.asarray(A))
    Hn = Vt[-1].reshape(3, 3)
    H = np.linalg.inv(Td) @ Hn @ Ts                 # deshacer la normalización
    return H / H[2, 2]


def reprojection_errors(H: np.ndarray, src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """Distancia euclidiana en PÍXELES entre H·src y dst, punto por punto (N,)."""
    return np.linalg.norm(apply_homography(H, src) - np.asarray(dst, dtype=float), axis=1)


def collinearity_margin(pts: np.ndarray) -> float:
    """Puntos (N,2) -> la menor distancia (en las unidades de pts) de un punto a la recta de otros dos.

    Mide qué tan lejos está el conjunto de tener 3 puntos alineados: 0 significa que hay 3 colineales.
    Para cada trío (a, b, c): distancia de c a la recta ab = |(b − a) × (c − a)| / ‖b − a‖.
    Se reporta en píxeles para que la "posición general" sea verificable en la imagen (enunciado §3).
    """
    p = np.asarray(pts, dtype=float)
    best = np.inf
    n = len(p)
    for i in range(n):
        for j in range(n):
            if j == i:
                continue
            ab = p[j] - p[i]
            L = np.linalg.norm(ab)
            if L == 0:
                return 0.0                           # dos puntos iguales: degenerado
            for k in range(n):
                if k in (i, j):
                    continue
                ac = p[k] - p[i]
                best = min(best, abs(ab[0] * ac[1] - ab[1] * ac[0]) / L)
    return float(best)


def has_three_collinear(pts: np.ndarray, tol: float = 1.0) -> bool:
    """True si algún punto está a menos de `tol` (píxeles por defecto) de la recta de otros dos."""
    return len(pts) >= 3 and collinearity_margin(pts) < tol
