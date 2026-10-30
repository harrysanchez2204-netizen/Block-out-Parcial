"""Bucle principal (módulo C). E9: teclado y ratón, cámara orbital, HUD, victoria y modo demo.

Cada fotograma recorre la cadena completa en un solo sentido (docs/INTERFACES.md §5):

    evento o guion --> Command --+--> apply_action(scene)         (A: estado 3D)
                                 +--> OrbitCamera.orbit/zoom/...  (B: estado de la cámara)
    VictoryAnimation.step(dt) --> set_pose --> apply_action(scene)     (la victoria mueve poses 3D)
    Scene --get_geometry--> Geometry3D --project(·, OrbitCamera.build)--> DrawPrimitives2D --> pantalla

La aplicación solo llama funciones públicas de §3. No calcula proyecciones ni guarda vértices 3D.

El tiempo de la animación avanza 1/60 s POR FOTOGRAMA, no según el reloj real: así la victoria y la demo
dan siempre los mismos resultados (R23). `pygame.time.Clock` solo frena el bucle a 60 fotogramas por
segundo; ningún estado depende de él.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field

import pygame

from blockout.app.animation import VictoryAnimation
from blockout.app.demo import FPS, DemoRunner
from blockout.app.hud import build_hud_lines
from blockout.app.input_map import Command, translate_event
from blockout.app.renderer import render_frame
from blockout.core.types import DrawPrimitives2D, Scene
from blockout.projection import OrbitCamera, project
from blockout.scene import apply_action, create_scene, get_geometry

DT = 1.0 / FPS
BLOCKED_MSG = "! Movimiento bloqueado: la pieza saldria del contenedor"
ANIMATING_MSG = "! Animacion en curso: las piezas se mueven solas (la camara si responde)"
# En la demo solo se aceptan estas órdenes del teclado; el resto (incluido el ratón) se ignora para que
# nadie cambie el resultado sin querer. Enter vuelve a empezar la demo.
DEMO_ALLOWED = ("quit", "help", "faces")


@dataclass
class AppState:
    """Todo lo que la aplicación recuerda entre fotogramas.

    `scene` es de A y solo se reemplaza con lo que devuelve apply_action. `camera` es de B y solo
    cambia con sus métodos. El resto es de C: `victory` (animación en curso o None), `demo` (guion en
    curso o None), `frame` (fotogramas transcurridos) y las opciones de dibujo.
    """
    scene: Scene = field(default_factory=create_scene)
    camera: OrbitCamera = field(default_factory=OrbitCamera)
    fill_faces: bool = False
    show_help: bool = True
    message: str = ""
    running: bool = True
    victory: VictoryAnimation | None = None
    demo: DemoRunner | None = None
    frame: int = 0

    @property
    def animating(self) -> bool:
        return self.victory is not None and not self.victory.finished


def apply_command(state: AppState, cmd: Command) -> None:
    """Ejecuta una orden. Es el ÚNICO lugar donde la entrada (o el guion) cambia la escena o la cámara."""
    if cmd.kind == "action":
        if state.animating:
            # La animación pone todas las poses en cada fotograma y al final restaura las del principio:
            # un movimiento del usuario se perdería. Se ignora y se avisa. La cámara sí sigue activa.
            state.message = ANIMATING_MSG
            return
        new = apply_action(state.scene, cmd.action)
        # apply_action devuelve EL MISMO objeto cuando rechaza la acción (contrato, §6): así se sabe
        # sin adivinar que un translate/rotate no se hizo porque la pieza saldría del contenedor.
        blocked = new is state.scene and cmd.action.kind in ("translate", "rotate")
        state.message = BLOCKED_MSG if blocked else ""
        state.scene = new
    elif cmd.kind == "orbit":
        state.camera.orbit(*cmd.args)
    elif cmd.kind == "zoom":
        state.camera.zoom(*cmd.args)
    elif cmd.kind == "fov":
        state.camera.set_fov(state.camera.fov + cmd.args[0])
    elif cmd.kind == "reset":
        state.camera.reset()
    elif cmd.kind == "faces":
        state.fill_faces = not state.fill_faces
    elif cmd.kind == "help":
        state.show_help = not state.show_help
    elif cmd.kind == "victory":
        if not state.animating:                       # V durante la animación no la reinicia
            state.victory = VictoryAnimation(state.scene)
            state.message = ""
    elif cmd.kind == "quit":
        state.running = False


def _demo_command(kind: str, data) -> Command:
    """Evento del guion -> la misma orden que produciría el teclado."""
    if kind == "action":
        return Command("action", action=data)
    if kind == "victory":
        return Command("victory")
    return data                                       # "camera" y "app" ya traen su Command


def advance_frame(state: AppState) -> None:
    """Un fotograma de tiempo: eventos del guion (si hay demo) y luego un paso de la victoria (si hay).

    No usa el reloj ni la ventana: lo llaman igual el bucle real y las pruebas.
    """
    if state.demo is not None and not state.demo.finished:
        for _, kind, data in state.demo.tick():
            apply_command(state, _demo_command(kind, data))
    if state.victory is not None:
        for act in state.victory.step(DT):
            state.scene = apply_action(state.scene, act)    # set_pose / set_status, vía la escena
        if state.victory.finished:
            state.victory = None
            state.message = ""
    state.frame += 1


def new_state(demo: bool = False) -> AppState:
    """Estado inicial. Con demo=True la escena y la cámara arrancan igual que siempre y corre el guion."""
    return AppState(demo=DemoRunner() if demo else None)


def banner_text(state: AppState) -> str:
    """Línea extra del HUD: avance de la demo y de la victoria."""
    parts = []
    if state.demo is not None:
        if state.demo.finished:
            parts.append("DEMO terminada: Enter repite, Esc sale")
        else:
            total = state.demo.total_frames / FPS
            parts.append(f"DEMO {state.demo.seconds:4.1f} s de {total:.1f} s")
    if state.animating:
        parts.append(f"VICTORIA {state.victory.t:3.1f} s de {state.victory.duration:.0f} s")
    return ("! " + "   ".join(parts)) if parts else ""


def frame_primitives(state: AppState, width: int, height: int) -> DrawPrimitives2D:
    """Estado -> primitivas 2D del fotograma. La cámara se reconstruye cada vez (K, R, t nuevas)."""
    return project(get_geometry(state.scene), state.camera.build(width, height),
                   fill_faces=state.fill_faces)


def run(demo: bool = False, size: tuple[int, int] = (1000, 700),
        max_frames: int | None = None) -> None:
    """Abre la ventana y corre el bucle. `max_frames` corta el bucle (lo usan las pruebas sin ventana)."""
    pygame.init()
    try:
        screen = pygame.display.set_mode(size)
        pygame.display.set_caption("Blockout – cámara móvil" + (" – DEMO" if demo else ""))
        pygame.key.set_repeat(250, 60)       # mantener una tecla la repite (orbitar con flechas)
        font = pygame.font.Font(None, 22)    # fuente incluida en pygame: igual en Linux y Windows
        clock = pygame.time.Clock()
        state = new_state(demo)
        while state.running:
            for ev in pygame.event.get():
                if demo and ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
                    show_help = state.show_help
                    state = new_state(demo=True)          # repetir la demo desde cero
                    state.show_help = show_help
                    continue
                for cmd in translate_event(ev):
                    if demo and cmd.kind not in DEMO_ALLOWED:
                        continue
                    apply_command(state, cmd)

            advance_frame(state)
            width, height = screen.get_size()
            prim = frame_primitives(state, width, height)
            hud = build_hud_lines(state.scene, state.camera, state.fill_faces, state.message, demo,
                                  state.show_help, banner_text(state))
            render_frame(screen, font, prim, hud)
            pygame.display.flip()

            clock.tick(FPS)
            if max_frames is not None and state.frame >= max_frames:
                state.running = False
    finally:
        pygame.quit()


def main(argv: list[str] | None = None) -> None:
    """Punto de entrada de `python -m blockout [--demo]`."""
    ap = argparse.ArgumentParser(prog="blockout", description="Blockout desde una cámara móvil")
    ap.add_argument("--demo", action="store_true",
                    help="secuencia determinista: escena, piezas, cámara y victoria (Enter la repite)")
    args = ap.parse_args(argv)
    run(demo=args.demo)
