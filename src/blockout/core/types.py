"""Contratos compartidos entre módulos (A: escena, B: proyección, C: aplicación).

Convención (ver docs/INTERFACES.md):
  * MUNDO: mano derecha, X a la derecha, Y hacia el fondo, Z hacia arriba. Unidad: 1 cubo.
    El piso del contenedor es el plano Z = 0.
  * OBJETO: origen en la esquina mínima del cubo (0,0,0) de la pieza.
  * CÁMARA (convención OpenCV): x derecha, y abajo, z hacia adelante (eje óptico).
  * IMAGEN: u hacia la derecha, v hacia abajo, origen en la esquina superior izquierda (píxeles).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np

Vec3 = np.ndarray  # shape (3,)
Mat3 = np.ndarray  # shape (3, 3)
Mat4 = np.ndarray  # shape (4, 4)


@dataclass(frozen=True)
class Pose:
    """Pose rígida de una pieza. `position` es dónde queda el PIVOTE en el mundo."""
    rotation: Mat3 = field(default_factory=lambda: np.eye(3))
    position: Vec3 = field(default_factory=lambda: np.zeros(3))


@dataclass(frozen=True)
class Piece:
    id: int
    name: str
    cells: tuple            # tuple[(i, j, k)], cubos unitarios en coordenadas locales enteras
    pivot_cell: int         # índice en `cells` del cubo cuyo centro es el pivote
    pose: Pose
    color: tuple = (200, 200, 200)

    @property
    def pivot_local(self) -> Vec3:
        return np.asarray(self.cells[self.pivot_cell], dtype=float) + 0.5


@dataclass(frozen=True)
class Container:
    size: tuple = (5, 5, 10)    # (ancho X, fondo Y, alto Z) en cubos


@dataclass(frozen=True)
class Scene:
    container: Container
    pieces: tuple
    active: int = 0
    time: float = 0.0
    status: str = "playing"     # "playing" | "victory"


@dataclass(frozen=True)
class Action:
    """Cambio de estado pedido a la escena. Lo producen la UI, la demo y la animación."""
    kind: str                   # select | select_next | translate | rotate | set_pose | set_status
    piece: int | None = None
    axis: int | None = None     # 0=X, 1=Y, 2=Z (rotate)
    steps: int = 1              # cuartos de vuelta (rotate)
    delta: tuple = (0, 0, 0)    # (translate)
    pose: Pose | None = None    # (set_pose)
    value: str | None = None    # (set_status)


@dataclass
class Mesh3D:
    """Geometría de una pieza (o del contenedor) YA en coordenadas del mundo."""
    name: str
    vertices: np.ndarray        # (N, 3)
    edges: np.ndarray           # (E, 2) índices a vertices
    faces: np.ndarray           # (F, 4) índices a vertices (cuadriláteros)
    color: tuple = (255, 255, 255)
    active: bool = False


@dataclass
class Geometry3D:
    meshes: list


@dataclass(frozen=True)
class Camera:
    """Cámara pinhole. P = K [R | t] (3x4). `center` es la posición en el mundo."""
    K: Mat3
    R: Mat3
    t: Vec3
    width: int
    height: int
    near: float = 0.1

    @property
    def center(self) -> Vec3:
        return -self.R.T @ self.t

    @property
    def P(self) -> np.ndarray:
        return self.K @ np.hstack([self.R, self.t.reshape(3, 1)])


@dataclass
class DrawPrimitives2D:
    """Resultado de proyectar. La UI solo dibuja esto: no conoce el 3D."""
    segments: np.ndarray        # (S, 2, 2) píxeles (u, v)
    seg_colors: list            # S tuplas RGB
    seg_depths: np.ndarray      # (S,) profundidad media z_cam
    seg_active: np.ndarray      # (S,) bool
    polygons: list = field(default_factory=list)   # [(pts (n,2), color, depth)] ordenados lejos→cerca
