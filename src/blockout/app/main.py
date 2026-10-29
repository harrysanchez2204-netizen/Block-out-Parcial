"""Bucle principal (módulo C). E6: teclado y ratón, cámara orbital, HUD y caras opcionales.

Cada fotograma recorre la cadena completa en un solo sentido (docs/INTERFACES.md §5):

    evento --input_map--> Command --+--> apply_action(scene)         (A: estado 3D)
                                    +--> OrbitCamera.orbit/zoom/...  (B: estado de la cámara)
    Scene --get_geometry--> Geometry3D --project(·, OrbitCamera.build)--> DrawPrimitives2D --> pantalla

La aplicación solo llama funciones públicas de §3. No calcula proyecciones ni guarda vértices 3D.
Falta: animación de victoria y modo demo (E9).
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field

import pygame

from blockout.app.hud import build_hud_lines
from blockout.app.input_map import Command, translate_event
from blockout.app.renderer import render_frame
from blockout.core.types import DrawPrimitives2D, Scene
from blockout.projection import OrbitCamera, project
from blockout.scene import apply_action, create_scene, get_geometry

FPS = 60
BLOCKED_MSG = "! Movimiento bloqueado: la pieza saldria del contenedor"


@dataclass
class AppState:
    """Todo lo que la aplicación recuerda entre fotogramas.

    `scene` es de A y solo se reemplaza con lo que devuelve apply_action. `camera` es de B y solo
    cambia con sus métodos. `fill_faces`, `show_help`, `message` y `running` son de C.
    """
    scene: Scene = field(default_factory=create_scene)
    camera: OrbitCamera = field(default_factory=OrbitCamera)
    fill_faces: bool = False
    show_help: bool = True
    message: str = ""
    running: bool = True


def apply_command(state: AppState, cmd: Command) -> None:
    """Ejecuta una orden. Es el ÚNICO lugar donde la entrada cambia la escena o la cámara."""
    if cmd.kind == "action":
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
    elif cmd.kind == "quit":
        state.running = False


def frame_primitives(state: AppState, width: int, height: int) -> DrawPrimitives2D:
    """Estado -> primitivas 2D del fotograma. La cámara se reconstruye cada vez (K, R, t nuevas)."""
    return project(get_geometry(state.scene), state.camera.build(width, height),
                   fill_faces=state.fill_faces)


def run(demo: bool = False, size: tuple[int, int] = (1000, 700),
        max_frames: int | None = None) -> None:
    """Abre la ventana y corre el bucle. `max_frames` corta el bucle (lo usan las pruebas sin ventana).

    `demo` ya existe para respetar la firma del contrato; el guion determinista llega en E9.
    """
    pygame.init()
    try:
        screen = pygame.display.set_mode(size)
        pygame.display.set_caption("Blockout – cámara móvil")
        pygame.key.set_repeat(250, 60)       # mantener una tecla la repite (orbitar con flechas)
        font = pygame.font.Font(None, 22)    # fuente incluida en pygame: igual en Linux y Windows
        clock = pygame.time.Clock()
        state = AppState()
        frame = 0
        while state.running:
            for ev in pygame.event.get():
                for cmd in translate_event(ev):
                    apply_command(state, cmd)

            width, height = screen.get_size()
            prim = frame_primitives(state, width, height)
            hud = build_hud_lines(state.scene, state.camera, state.fill_faces, state.message, demo,
                                  state.show_help)
            render_frame(screen, font, prim, hud)
            pygame.display.flip()

            clock.tick(FPS)
            frame += 1
            if max_frames is not None and frame >= max_frames:
                state.running = False
    finally:
        pygame.quit()


def main(argv: list[str] | None = None) -> None:
    """Punto de entrada de `python -m blockout [--demo]`."""
    ap = argparse.ArgumentParser(prog="blockout", description="Blockout desde una cámara móvil")
    ap.add_argument("--demo", action="store_true", help="secuencia determinista (llega en E9)")
    args = ap.parse_args(argv)
    run(demo=args.demo)
