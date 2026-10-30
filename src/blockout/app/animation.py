"""Animación de victoria (módulo C, E9). Requisito R22 y enunciado §3 ("Animación de victoria").

El enunciado pide una animación breve con objetos 3D que use la MISMA cadena de transformaciones y
proyección, con los controles de cámara disponibles, y (§4) que modifique **poses 3D a través de la
interfaz de la escena**, nunca coordenadas de pantalla. Por eso esta clase no dibuja ni conoce la cámara:
solo produce acciones `set_pose` que la aplicación pasa a `apply_action`. Después, cada fotograma sigue
el camino normal: `get_geometry` (M) -> `project` (K[R|t]) -> pantalla.

Cada pose es una FUNCIÓN PURA DEL TIEMPO calculada desde la escena guardada al empezar (`base`). No se
suma nada fotograma a fotograma, así que no se acumula error y el mismo t siempre da las mismas poses.

Con s = t / T en [0, 1] se usan dos curvas suaves:

    e(s) = (1 − cos πs) / 2     va de 0 a 1        (avance del giro)
    b(s) = sin²(πs)             va de 0 a 1 y vuelve a 0 (cuánto se separan del lugar original)

Las dos tienen derivada cero en s = 0 y s = 1: las piezas arrancan y frenan con suavidad. Para la
pieza i, con pivote p_i y rotación R_i al empezar, y el eje vertical del pozo en c = (W/2, D/2):

    posición(s) = c + Rz(2π·e) · ( u_i · (r_i + ΔR·b) ) + (0, 0, z_i + (z_m − z_i)·k·b)
    rotación(s) = Rot(a_i, 4π·e) · R_i

r_i y u_i son la distancia y la dirección horizontal del pivote al eje, y z_m es la altura media del
pozo: a mitad de la animación las piezas salen por fuera de las paredes y se juntan hacia esa altura
(las de arriba bajan y las de abajo suben), así ninguna se sale del cuadro de la cámara. Como en s = 0 y
s = 1 vale
b = 0, e = 0 o 1, y los giros son de una vuelta (órbita) y dos vueltas (giro propio), en los dos
extremos la pose es exactamente la del principio: no hay saltos al empezar ni al terminar.
El giro propio es alrededor del PIVOTE, porque Pose.position es la posición del pivote (§1.2).
"""
from __future__ import annotations

import math

import numpy as np

from blockout.core.types import Action, Pose, Scene
from blockout.scene import rot_axis_angle

DURATION = 6.0           # segundos de animación
ORBIT_TURNS = 1          # vueltas alrededor del eje del pozo (entero: vuelve al mismo lugar)
SPIN_TURNS = 2           # vueltas de cada pieza sobre sí misma (entero: vuelve a la misma orientación)
RADIAL_OUT = 3.0         # cuánto se alejan del eje en la mitad de la animación (cubos)
GATHER = 0.6             # fracción del camino hacia la altura media del pozo, en la mitad de la animación

# Eje de giro propio de cada pieza (se normaliza al usarlo). Distintos para que no giren todas igual.
SPIN_AXES = ((0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 0), (1, -1, 1), (-1, 1, 1))


def ease(s: float) -> float:
    """0 -> 1 con velocidad cero en los extremos: e(s) = (1 − cos πs)/2."""
    return 0.5 - 0.5 * math.cos(math.pi * s)


def bump(s: float) -> float:
    """0 -> 1 -> 0 con velocidad cero en los extremos: b(s) = sin²(πs)."""
    return math.sin(math.pi * s) ** 2


def _rot_z(theta: float) -> np.ndarray:
    c, s = math.cos(theta), math.sin(theta)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


class VictoryAnimation:
    """VictoryAnimation(scene).step(dt) -> list[Action], como dice docs/INTERFACES.md §3.3.

    * El primer `step` emite `set_status("victory")` junto con las poses.
    * Cada `step` avanza t en dt y emite un `set_pose` por pieza, con la pose de `pose_at(i, t)`.
    * El `step` que llega a la duración restaura **exactamente** las poses guardadas al empezar y emite
      `set_status("playing")`. Después de eso, `finished` es True y `step` devuelve una lista vacía.
    """

    def __init__(self, scene: Scene, duration: float = DURATION):
        self.base = scene                         # escena inmutable: no hace falta copiarla
        self.duration = float(duration)
        self.t = 0.0
        self.finished = False
        self._started = False
        W, D, H = scene.container.size
        self.center = np.array([W / 2.0, D / 2.0])
        self.mid_height = H / 2.0

    # ------------------------------------------------------------------ función pura del tiempo
    def pose_at(self, i: int, t: float) -> Pose:
        """Pose de la pieza i en el instante t (segundos desde que empezó). No modifica nada."""
        piece = self.base.pieces[i]
        s = min(max(t / self.duration, 0.0), 1.0)
        e, b = ease(s), bump(s)
        p0 = np.asarray(piece.pose.position, dtype=float)

        d = p0[:2] - self.center                  # del eje del pozo al pivote, en el plano XY
        r = float(np.hypot(*d))
        if r > 1e-9:
            u = d / r
        else:                                     # pivote justo sobre el eje: dirección por índice
            ang = 2.0 * math.pi * i / max(len(self.base.pieces), 1)
            u = np.array([math.cos(ang), math.sin(ang)])
        horiz = self.center + (_rot_z(2.0 * math.pi * ORBIT_TURNS * e)[:2, :2] @ (u * (r + RADIAL_OUT * b)))
        z = p0[2] + (self.mid_height - p0[2]) * GATHER * b
        R = rot_axis_angle(SPIN_AXES[i % len(SPIN_AXES)], 2.0 * math.pi * SPIN_TURNS * e) @ piece.pose.rotation
        return Pose(R, np.array([horiz[0], horiz[1], z]))

    def actions_at(self, t: float) -> list[Action]:
        """Un `set_pose` por pieza con las poses del instante t."""
        return [Action("set_pose", piece=i, pose=self.pose_at(i, t)) for i in range(len(self.base.pieces))]

    # ------------------------------------------------------------------ avance por fotogramas
    def step(self, dt: float) -> list[Action]:
        """Avanza dt segundos y devuelve las acciones de este fotograma (ver la clase)."""
        if self.finished:
            return []
        if math.isfinite(dt) and dt > 0:
            self.t = min(self.t + dt, self.duration)
        acts = []
        if not self._started:
            acts.append(Action("set_status", value="victory"))
            self._started = True
        # Sumar 1/60 trescientas sesenta veces da 5.9999999999999 y no 6: con esta tolerancia, 6 s son
        # exactamente 360 fotogramas en cualquier máquina.
        if self.t >= self.duration - 1e-9:
            acts += [Action("set_pose", piece=i, pose=p.pose) for i, p in enumerate(self.base.pieces)]
            acts.append(Action("set_status", value="playing"))
            self.finished = True
            return acts
        return acts + self.actions_at(self.t)
