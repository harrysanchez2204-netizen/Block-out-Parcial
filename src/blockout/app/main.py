"""Bucle principal (módulo C). E3: ventana, cámara fija y dibujo de líneas.

Cada fotograma recorre la cadena completa en un solo sentido (docs/INTERFACES.md §5):

    Scene (A) --get_geometry--> Geometry3D (mundo) --project + Camera (B)--> DrawPrimitives2D --> pantalla (C)

La aplicación solo llama funciones públicas de §3. No calcula proyecciones ni guarda vértices 3D.
Lo que falta llega por etapas: teclas y acciones (E4/E6), cámara orbital (E5), victoria y demo (E9).
"""
from __future__ import annotations

import argparse

import pygame

from blockout.app.renderer import render_frame
from blockout.projection import build_camera, project
from blockout.scene import create_scene, get_geometry

FPS = 60

# Cámara fija de E3. Propuesta para la vista inicial de la cámara orbital (E5): objetivo en el
# centro del contenedor 5×5×10, azimut −60°, elevación 25°, distancia 22.
#   eye = target + 22·(cos25°·cos(−60°), cos25°·sin(−60°), sin25°) ≈ (12.469, −14.767, 14.298)
# Con 1000×700 y FOV 50° todo el contenedor queda entre v ≈ 71 y v ≈ 655: no toca el HUD.
# (Con el objetivo a z = 4 y distancia 20 de la guía, el borde superior salía en v < 0.)
CAMERA_TARGET = (2.5, 2.5, 5.0)
CAMERA_EYE = (12.469, -14.767, 14.298)
CAMERA_FOV = 50.0


def run(demo: bool = False, size: tuple[int, int] = (1000, 700),
        max_frames: int | None = None) -> None:
    """Abre la ventana y corre el bucle. `max_frames` corta el bucle (lo usan las pruebas sin ventana).

    `demo` ya existe para respetar la firma del contrato; el guion determinista llega en E9.
    """
    pygame.init()
    try:
        screen = pygame.display.set_mode(size)
        pygame.display.set_caption("Blockout – cámara móvil")
        font = pygame.font.Font(None, 24)          # fuente incluida en pygame: igual en Linux y Windows
        clock = pygame.time.Clock()

        scene = create_scene()                     # A: estado 3D en el mundo
        frame = 0
        running = True
        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False

            width, height = screen.get_size()
            camera = build_camera(CAMERA_EYE, CAMERA_TARGET, width, height, CAMERA_FOV)   # B
            prim = project(get_geometry(scene), camera)                                 # A -> B
            active = scene.pieces[scene.active].name if scene.pieces else "-"
            hud = [f"Pieza activa: {active}   Estado: {scene.status}" + ("   [DEMO: llega en E9]" if demo else ""),
                   f"Camara fija  fov={CAMERA_FOV:.0f}°   segmentos dibujados: {len(prim.segments)}",
                   "Esc: salir   (controles de pieza y camara: E4-E6)"]
            render_frame(screen, font, prim, hud)                                       # C
            pygame.display.flip()

            clock.tick(FPS)
            frame += 1
            if max_frames is not None and frame >= max_frames:
                running = False
    finally:
        pygame.quit()


def main(argv: list[str] | None = None) -> None:
    """Punto de entrada de `python -m blockout [--demo]`."""
    ap = argparse.ArgumentParser(prog="blockout", description="Blockout desde una cámara móvil")
    ap.add_argument("--demo", action="store_true", help="secuencia determinista (llega en E9)")
    args = ap.parse_args(argv)
    run(demo=args.demo)
