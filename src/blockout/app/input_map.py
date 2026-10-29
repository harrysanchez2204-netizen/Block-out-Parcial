"""Entrada -> órdenes (módulo C). Traducción PURA: un evento de pygame entra, una lista de órdenes sale.

Aquí no se toca la escena, ni la cámara, ni la ventana. Por eso cada tecla se puede probar con eventos
sintéticos y sin pantalla (tests/test_interfaz.py). Quien ejecuta las órdenes es `app/main.py`:

  * orden "action" -> apply_action(scene, action)        (A: la escena solo cambia así)
  * orden "orbit" / "zoom" / "fov" / "reset" -> métodos de OrbitCamera   (B: solo cambia la cámara)
  * orden "faces" / "help" / "quit" -> estado propio de la aplicación      (C)

Teclas: se usan LETRAS para todo lo importante. pygame entrega el código de la tecla según la
distribución del teclado (en español latinoamericano, `[` y `]` exigen AltGr o están en otro lugar),
y las letras están en el mismo sitio en cualquier distribución latina. Por eso el FOV va en Z / X y
no en [ / ] como proponía la guía.

Las traslaciones y rotaciones son en ejes del MUNDO (X derecha, Y fondo, Z arriba): W siempre lleva
la pieza hacia +Y aunque la cámara esté orbitada. Se eligió así porque es lo que guarda la escena y
lo que el HUD puede mostrar sin ambigüedad.
"""
from __future__ import annotations

from dataclasses import dataclass

import pygame

from blockout.core.types import Action

ORBIT_DEG_PER_PIXEL = 0.4      # arrastrar 100 px con el ratón = 40°
ORBIT_DEG_PER_KEY = 5.0        # una pulsación de flecha = 5°
ZOOM_IN, ZOOM_OUT = 0.9, 1.1   # factor de distancia por paso de rueda o de RePág/AvPág
FOV_STEP = 5.0                 # grados por pulsación de Z / X


@dataclass(frozen=True)
class Command:
    """Una orden para main.py. `kind`: action | orbit | zoom | fov | reset | faces | help | quit."""
    kind: str
    action: Action | None = None
    args: tuple = ()


# --------------------------------------------------------------------------- pieza (módulo A)
# piece=None en todas: actúan sobre la pieza ACTIVA, así esta tabla no necesita saber cuál es.
PIECE_KEYS: dict[int, Action] = {
    pygame.K_a: Action("translate", delta=(-1, 0, 0)),
    pygame.K_d: Action("translate", delta=(1, 0, 0)),
    pygame.K_s: Action("translate", delta=(0, -1, 0)),
    pygame.K_w: Action("translate", delta=(0, 1, 0)),
    pygame.K_f: Action("translate", delta=(0, 0, -1)),
    pygame.K_r: Action("translate", delta=(0, 0, 1)),
    pygame.K_i: Action("rotate", axis=0, steps=1),
    pygame.K_k: Action("rotate", axis=0, steps=-1),
    pygame.K_j: Action("rotate", axis=1, steps=1),
    pygame.K_l: Action("rotate", axis=1, steps=-1),
    pygame.K_u: Action("rotate", axis=2, steps=1),
    pygame.K_o: Action("rotate", axis=2, steps=-1),
    pygame.K_TAB: Action("select_next"),
}
# 1..9 eligen la pieza por número (la escena ignora los números que no existen).
for _n in range(9):
    PIECE_KEYS[pygame.K_1 + _n] = Action("select", piece=_n)

# -------------------------------------------------------------------------- cámara (módulo B)
CAMERA_KEYS: dict[int, Command] = {
    pygame.K_LEFT: Command("orbit", args=(-ORBIT_DEG_PER_KEY, 0.0)),
    pygame.K_RIGHT: Command("orbit", args=(ORBIT_DEG_PER_KEY, 0.0)),
    pygame.K_UP: Command("orbit", args=(0.0, ORBIT_DEG_PER_KEY)),
    pygame.K_DOWN: Command("orbit", args=(0.0, -ORBIT_DEG_PER_KEY)),
    pygame.K_PAGEUP: Command("zoom", args=(ZOOM_IN,)),
    pygame.K_PAGEDOWN: Command("zoom", args=(ZOOM_OUT,)),
    pygame.K_z: Command("fov", args=(-FOV_STEP,)),
    pygame.K_x: Command("fov", args=(FOV_STEP,)),
    pygame.K_c: Command("reset"),
}

# ------------------------------------------------------------------------ aplicación (módulo C)
APP_KEYS: dict[int, Command] = {
    pygame.K_g: Command("faces"),
    pygame.K_h: Command("help"),
    pygame.K_ESCAPE: Command("quit"),
}

# Ayuda que muestran el HUD y el README. tests/test_interfaz.py comprueba que el README la contiene
# literalmente y que cada tecla de las tablas aparece aquí: así no pueden quedar desincronizados.
# Líneas CORTAS a propósito: forman una columna a la izquierda (x < 290 px) que no tapa el contenedor,
# que en la vista inicial empieza en x ≈ 310 px.
HELP_LINES: list[str] = [
    "PIEZA (ejes del mundo)",
    "  Tab / 1-6    elegir",
    "  A/D S/W F/R  mover en X Y Z",
    "  I/K J/L U/O  rotar en X Y Z",
    "CAMARA",
    "  arrastrar o flechas  orbitar",
    "  rueda o RePag/AvPag  distancia",
    "  Z/X  campo de vision",
    "  C    vista inicial",
    "G caras   H ayuda   Esc salir",
]


def translate_event(ev: pygame.event.Event) -> list[Command]:
    """Evento de pygame -> lista de órdenes (vacía si el evento no significa nada para la app)."""
    if ev.type == pygame.QUIT:
        return [Command("quit")]

    if ev.type == pygame.KEYDOWN:
        if ev.key in PIECE_KEYS:
            return [Command("action", action=PIECE_KEYS[ev.key])]
        if ev.key in CAMERA_KEYS:
            return [CAMERA_KEYS[ev.key]]
        if ev.key in APP_KEYS:
            return [APP_KEYS[ev.key]]
        return []

    if ev.type == pygame.MOUSEMOTION and ev.buttons[0]:
        # Arrastrar a la derecha gira la escena hacia la derecha = la cámara va hacia la izquierda
        # (azimut menor). Arrastrar hacia abajo sube la cámara (elevación mayor).
        dx, dy = ev.rel
        return [Command("orbit", args=(-dx * ORBIT_DEG_PER_PIXEL, dy * ORBIT_DEG_PER_PIXEL))]

    if ev.type == pygame.MOUSEWHEEL and ev.y != 0:
        return [Command("zoom", args=(ZOOM_IN if ev.y > 0 else ZOOM_OUT,))]

    return []
