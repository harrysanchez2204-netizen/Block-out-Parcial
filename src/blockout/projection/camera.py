"""Construcción de la cámara (módulo B): K, R, t y P = K [R | t].

    λ [u v 1]ᵀ = K · [R | t] · M · [X Y Z 1]ᵀ
                 └──── este archivo arma K y [R | t]

Se hace con numpy a mano. No se usa la cámara de ningún motor gráfico (enunciado §3, R17).
Convención de cámara (OpenCV): x a la derecha, y hacia abajo, z hacia adelante. Ver
docs/INTERFACES.md §1.3.

E3 entrega la cámara fija (build_camera). La cámara orbital (OrbitCamera) llega en E5.
"""
from __future__ import annotations

import math

import numpy as np

from blockout.core.types import Camera

WORLD_UP = np.array([0.0, 0.0, 1.0])     # Z del mundo apunta hacia arriba


def intrinsics_from_fov(width: int, height: int, fov_deg: float) -> np.ndarray:
    """(ancho, alto en píxeles, FOV horizontal en grados) -> K (3,3).

    Geometría: la imagen mide `width` píxeles y subtiende el ángulo `fov` desde el centro óptico.
    Medio ancho de imagen frente a media apertura forma un triángulo rectángulo:

        tan(fov / 2) = (width / 2) / f     =>     f = (width / 2) / tan(fov / 2)   [píxeles]

    Píxeles cuadrados y sin sesgo => fx = fy = f. El punto principal es el centro de la imagen.
    Abrir el FOV disminuye f (la imagen se "aleja"); el centro de la cámara no se mueve.
    """
    if not 0.0 < fov_deg < 180.0:
        raise ValueError(f"fov_deg debe estar en (0, 180): {fov_deg}")
    f = (width / 2.0) / math.tan(math.radians(fov_deg) / 2.0)
    return np.array([[f, 0.0, width / 2.0],
                     [0.0, f, height / 2.0],
                     [0.0, 0.0, 1.0]])


def look_at(eye, target, up=WORLD_UP) -> tuple[np.ndarray, np.ndarray]:
    """(posición de la cámara, punto observado, arriba del mundo) -> (R (3,3), t (3,)).

    Se construyen los tres ejes de la cámara expresados en el MUNDO:
        adelante  z_c = (target − eye) / ‖·‖
        derecha   x_c = z_c × up / ‖·‖          (perpendicular a la mirada y a la vertical)
        abajo     y_c = z_c × x_c               (cierra un sistema de mano derecha)
    R tiene esos ejes como FILAS: así R · v da las componentes de v en los ejes de la cámara.
    Para que X_cam = R · (X_world − eye), se toma t = −R · eye. El centro es C = −Rᵀ t = eye.

    Si la mirada es paralela a `up`, z_c × up = 0 y "derecha" no está definida: se lanza
    ValueError. Por eso la cámara orbital limitará la elevación a ±89° (E5).
    """
    eye = np.asarray(eye, dtype=float)
    target = np.asarray(target, dtype=float)
    up = np.asarray(up, dtype=float)
    fwd = target - eye
    n = np.linalg.norm(fwd)
    if n < 1e-12:
        raise ValueError("eye y target coinciden: no hay dirección de vista")
    fwd /= n
    right = np.cross(fwd, up)
    nr = np.linalg.norm(right)
    if nr < 1e-9:
        raise ValueError("la dirección de vista es paralela a 'up': look_at degenerado")
    right /= nr
    down = np.cross(fwd, right)
    R = np.vstack([right, down, fwd])
    return R, -R @ eye


def build_camera(eye, target, width: int, height: int, fov_deg: float = 50.0,
                 near: float = 0.1) -> Camera:
    """(eye, target, tamaño, FOV, near) -> Camera inmutable con K, R, t."""
    R, t = look_at(eye, target)
    return Camera(K=intrinsics_from_fov(width, height, fov_deg), R=R, t=t,
                  width=int(width), height=int(height), near=float(near))
