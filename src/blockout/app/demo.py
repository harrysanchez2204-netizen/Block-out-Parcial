"""Modo de demostración (módulo C, E9). Requisito R23 y enunciado §3 ("Modo de demostración").

El enunciado pide una secuencia DETERMINISTA, que pueda reproducirse durante la evaluación, y que muestre
la escena principal, transformaciones de piezas, movimientos de cámara y la animación de victoria.

Determinista quiere decir: dos ejecuciones dan exactamente lo mismo. Para eso:
  * El guion se escribe en NÚMEROS DE FOTOGRAMA, no en segundos del reloj real. Si el computador se
    pone lento, la demo se ve más lenta, pero en el fotograma 600 siempre pasa lo mismo.
  * No hay `random`, ni `time.time()`, ni nada que dependa del reloj o del sistema.
  * Durante la demo la aplicación ignora el ratón y casi todo el teclado (ver app/main.py), así que nadie
    puede cambiar el resultado sin querer.

El guion usa los mismos caminos que el teclado: acciones de escena para A, órdenes de cámara para B. Así
la demo muestra exactamente lo que hace la aplicación, no una animación aparte.
"""
from __future__ import annotations

from blockout.app.animation import DURATION as VICTORY_SECONDS
from blockout.app.input_map import Command
from blockout.core.types import Action

FPS = 60


def at(seconds: float) -> int:
    """Segundos del guion -> número de fotograma (a 60 fotogramas por segundo)."""
    return int(round(seconds * FPS))


VICTORY_START = 12.5                          # segundos
END_SECONDS = VICTORY_START + VICTORY_SECONDS + 1.5


def build_script() -> list[tuple[int, str, object]]:
    """Guion completo: lista de (fotograma, tipo, datos), ordenada por fotograma.

    Tipos: "action" (datos = Action de escena), "camera" y "app" (datos = Command), "victory" (sin datos).

      0 –  2 s  escena principal quieta
      2 –  7 s  transformaciones: la I baja y gira; el Trípode y el Tornillo (no planarios) giran en
                los tres ejes del mundo y se mueven
      7 s       caras rellenas
      8 – 12 s  cámara: órbita, acercamiento, campo de visión y vuelta a la vista inicial
     12.5 s     victoria; durante la animación la cámara sigue orbitando (los controles siguen activos)
     20 s       fin
    """
    ev: list[tuple[int, str, object]] = []

    def act(sec, action):
        ev.append((at(sec), "action", action))

    # --- transformaciones de piezas (R04, R05)
    # La I y el Trípode arrancan pegados a la pared Y = 0: antes de girarlos se separan un cubo, como
    # haría un jugador. Si no, el giro los sacaría del contenedor y la escena lo rechazaría (§6).
    act(2.0, Action("select", piece=0))                     # I
    act(2.4, Action("translate", delta=(0, 0, -1)))
    act(2.8, Action("translate", delta=(0, 1, 0)))
    act(3.2, Action("rotate", axis=2, steps=1))             # 90° en Z
    act(3.8, Action("select", piece=4))                     # Trípode (no planario)
    act(4.0, Action("translate", delta=(0, 1, 0)))
    act(4.3, Action("rotate", axis=0, steps=1))             # 90° en X
    act(4.7, Action("rotate", axis=1, steps=1))             # 90° en Y
    act(5.1, Action("translate", delta=(1, 0, 0)))
    act(5.6, Action("select", piece=5))                     # Tornillo (no planario)
    act(6.0, Action("rotate", axis=2, steps=-1))
    act(6.4, Action("translate", delta=(0, 0, -1)))
    act(6.8, Action("select", piece=0))

    # --- vista con caras rellenas (R16)
    ev.append((at(7.0), "app", Command("faces")))

    # --- cámara (R07–R10): pasos pequeños en fotogramas seguidos para que el movimiento se vea fluido
    for k in range(at(2.0)):                                 # 8–10 s: media vuelta y un poco más alto
        ev.append((at(8.0) + k, "camera", Command("orbit", args=(1.5, 0.12))))
    for k in range(at(0.8)):                                 # 10–10.8 s: acercarse
        ev.append((at(10.0) + k, "camera", Command("zoom", args=(0.995,))))
    for k in range(at(0.8)):                                 # 10.8–11.6 s: cerrar el campo de visión
        ev.append((at(10.8) + k, "camera", Command("fov", args=(-0.2,))))
    ev.append((at(12.0), "camera", Command("reset")))

    # --- victoria (R22), con la cámara orbitando mientras tanto
    ev.append((at(VICTORY_START), "victory", None))
    for k in range(at(VICTORY_SECONDS)):
        ev.append((at(VICTORY_START) + k, "camera", Command("orbit", args=(0.5, 0.0))))
    ev.append((at(VICTORY_START + VICTORY_SECONDS + 0.5), "camera", Command("reset")))

    return sorted(ev, key=lambda e: e[0])                   # sort estable: respeta el orden de arriba


class DemoRunner:
    """DemoRunner().tick() -> eventos del fotograma actual, como dice docs/INTERFACES.md §3.3.

    Cada `tick` devuelve los eventos del guion del fotograma en curso y avanza un fotograma.
    `finished` pasa a True después del último fotograma de la demo.
    """

    def __init__(self):
        self.script = build_script()
        self.frame = 0
        self.total_frames = at(END_SECONDS)
        self._i = 0

    @property
    def finished(self) -> bool:
        return self.frame >= self.total_frames

    @property
    def seconds(self) -> float:
        return self.frame / FPS

    def tick(self) -> list[tuple[int, str, object]]:
        out = []
        while self._i < len(self.script) and self.script[self._i][0] <= self.frame:
            out.append(self.script[self._i])
            self._i += 1
        self.frame += 1
        return out
