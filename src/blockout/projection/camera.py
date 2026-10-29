"""Construcción de la cámara (módulo B): K, R, t y P = K [R | t].

    λ [u v 1]ᵀ = K · [R | t] · M · [X Y Z 1]ᵀ
                 └──── este archivo arma K y [R | t]

Se hace con numpy a mano. No se usa la cámara de ningún motor gráfico (enunciado §3, R17).
Convención de cámara (OpenCV): x a la derecha, y hacia abajo, z hacia adelante. Ver
docs/INTERFACES.md §1.3.

E3 entregó la cámara fija (build_camera). E5 agrega la cámara orbital (OrbitCamera).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

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


# Límites acordados en docs/INTERFACES.md §3.2.
ELEVATION_LIMIT = 89.0          # grados; en ±90° la mirada sería paralela a Z y look_at falla
DISTANCE_RANGE = (2.0, 80.0)    # unidades del mundo (cubos)
FOV_RANGE = (15.0, 120.0)       # grados, FOV horizontal


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


@dataclass
class OrbitCamera:
    """Estado de la cámara orbital: (objetivo, azimut, elevación, distancia, FOV).

    Es el ÚNICO estado mutable del módulo B, y no toca la escena (R11): orbitar, acercar o cambiar
    el FOV solo cambia estos cinco números. En cada fotograma `build` los convierte en una Camera
    inmutable con K, R, t nuevas. La escena 3D sigue intacta.

    Coordenadas esféricas alrededor del objetivo T (α = azimut alrededor de Z, ε = elevación sobre
    el plano XY, d = distancia):

        eye = T + d · (cos ε · cos α,  cos ε · sin α,  sin ε)

    Valores por defecto = la vista fija de E3 (`app/main.py`): objetivo en el centro del contenedor
    5×5×10, azimut −60°, elevación 25°, distancia 22, FOV 50°.

    Entradas no finitas (NaN, inf) o factores de zoom ≤ 0 se ignoran: la cámara no queda en un
    estado inválido por un evento raro del ratón.
    """
    target: np.ndarray = field(default_factory=lambda: np.array([2.5, 2.5, 5.0]))
    azimuth: float = -60.0          # grados, alrededor de Z del mundo
    elevation: float = 25.0         # grados sobre el plano XY, en [−89, 89]
    distance: float = 22.0          # unidades del mundo, en [2, 80]
    fov: float = 50.0               # grados, FOV horizontal, en [15, 120]
    _home: tuple = field(init=False, repr=False, default=())

    def __post_init__(self) -> None:
        self.target = np.asarray(self.target, dtype=float).copy()
        self.azimuth = float(self.azimuth) % 360.0
        self.elevation = _clamp(float(self.elevation), -ELEVATION_LIMIT, ELEVATION_LIMIT)
        self.distance = _clamp(float(self.distance), *DISTANCE_RANGE)
        self.fov = _clamp(float(self.fov), *FOV_RANGE)
        # Se guarda una COPIA del estado inicial para reset (R10).
        self._home = (self.target.copy(), self.azimuth, self.elevation, self.distance, self.fov)

    def orbit(self, d_az: float, d_el: float) -> None:
        """Gira alrededor del objetivo: suma grados al azimut (módulo 360) y a la elevación (±89°)."""
        if not (math.isfinite(d_az) and math.isfinite(d_el)):
            return
        self.azimuth = (self.azimuth + d_az) % 360.0
        self.elevation = _clamp(self.elevation + d_el, -ELEVATION_LIMIT, ELEVATION_LIMIT)

    def zoom(self, factor: float) -> None:
        """Multiplica la distancia (factor < 1 acerca). Cambia la POSICIÓN de la cámara, no K."""
        if not (math.isfinite(factor) and factor > 0):
            return
        self.distance = _clamp(self.distance * factor, *DISTANCE_RANGE)

    def set_fov(self, fov: float) -> None:
        """Cambia el FOV horizontal (en grados). Cambia K (la focal f), no la posición."""
        if not math.isfinite(fov):
            return
        self.fov = _clamp(float(fov), *FOV_RANGE)

    def reset(self) -> None:
        """Vuelve exactamente al estado con que se creó la cámara (R10)."""
        target, self.azimuth, self.elevation, self.distance, self.fov = self._home
        self.target = target.copy()

    @property
    def eye(self) -> np.ndarray:
        """Centro de la cámara en el mundo, a partir de las coordenadas esféricas."""
        az, el = math.radians(self.azimuth), math.radians(self.elevation)
        return self.target + self.distance * np.array([math.cos(el) * math.cos(az),
                                                       math.cos(el) * math.sin(az),
                                                       math.sin(el)])

    def build(self, width: int, height: int) -> Camera:
        """Estado orbital -> Camera inmutable (K, R, t) para un viewport de width × height."""
        return build_camera(self.eye, self.target, width, height, self.fov)
