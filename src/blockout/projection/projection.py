"""Proyección en perspectiva con recorte (módulo B).

Orden de cada punto (docs/INTERFACES.md §1.5):

    mundo --[R|t]--> cámara --recorte z ≥ near--> K --división por λ = z_cam--> píxeles (u, v)

La regla de oro: NUNCA se divide por z sin haber garantizado antes z ≥ near > 0. Un punto detrás de
la cámara (z < 0) dividido "a ciegas" aparece reflejado e invertido en la imagen, y un punto con
z ≈ 0 da coordenadas gigantes. Por eso primero se recorta y después se divide.
"""
from __future__ import annotations

import numpy as np

from blockout.core.types import Camera, DrawPrimitives2D, Geometry3D


def world_to_camera(cam: Camera, pts_world: np.ndarray) -> np.ndarray:
    """(N,3) mundo -> (N,3) cámara:  X_c = R · X_w + t   (en filas: X_w · Rᵀ + t)."""
    return np.atleast_2d(np.asarray(pts_world, dtype=float)) @ cam.R.T + cam.t


def perspective_divide(cam: Camera, pts_cam: np.ndarray) -> np.ndarray:
    """(N,3) cámara con z > 0 -> (N,2) píxeles.

    K · X_c = (f·x + cx·z,  f·y + cy·z,  z) = λ (u, v, 1)  con λ = z, luego
        u = f · x / z + cx,     v = f · y / z + cy.
    Precondición: z > 0 en todos los puntos (lo garantizan project_points y el recorte).
    """
    uvw = np.atleast_2d(pts_cam) @ cam.K.T
    return uvw[:, :2] / uvw[:, 2:3]


def project_points(cam: Camera, pts_world: np.ndarray):
    """(N,3) mundo -> (uv (N,2), z (N,), visible (N,) bool).

    Un punto es visible solo si z_cam > near. Los no visibles quedan con uv = NaN y nunca se
    dividen. Esta es la función que usa el ejemplo compartido y, en E7, el experimento de homografía.
    """
    pc = world_to_camera(cam, pts_world)
    z = pc[:, 2]
    visible = z > cam.near
    uv = np.full((len(pc), 2), np.nan)
    if visible.any():
        uv[visible] = perspective_divide(cam, pc[visible])
    return uv, z, visible


def clip_segment_near(a: np.ndarray, b: np.ndarray, near: float):
    """Segmento a–b en coords de CÁMARA -> (a', b') dentro de z ≥ near, o None si queda detrás.

    Si un extremo está delante y el otro detrás, el corte con el plano z = near sale de la
    parametrización p(s) = a + s·(b − a) imponiendo p_z(s) = near:

        a_z + s·(b_z − a_z) = near    =>    s = (near − a_z) / (b_z − a_z)

    El denominador no es cero porque a_z y b_z están a lados distintos de near. Como la
    transformación mundo -> cámara es afín, recortar en coordenadas de cámara equivale a recortar
    la arista 3D original: el pedazo que se dibuja es parte real de la arista.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a_in, b_in = a[2] >= near, b[2] >= near
    if not a_in and not b_in:
        return None
    if a_in and b_in:
        return a, b
    s = (near - a[2]) / (b[2] - a[2])
    p = a + s * (b - a)
    p[2] = near                          # evita que el redondeo lo deje en near − 1e-17
    return (a, p) if a_in else (p, b)


def project(geometry: Geometry3D, cam: Camera, fill_faces: bool = False) -> DrawPrimitives2D:
    """Geometry3D (mundo) -> DrawPrimitives2D (píxeles). Solo aristas en E3.

    Cada arista: mundo -> cámara, recorte contra z = near, división en perspectiva. Las que quedan
    completamente detrás se descartan. `fill_faces` existe para respetar la firma del contrato;
    las caras rellenas (descarte de caras traseras + algoritmo del pintor, R16) llegan en E5, y
    mientras tanto `polygons` sale vacía, que el contrato permite ("vacía si no se piden caras").
    """
    segs, cols, depths, act = [], [], [], []
    for mesh in geometry.meshes:
        if len(mesh.vertices) == 0 or len(mesh.edges) == 0:
            continue
        pc = world_to_camera(cam, mesh.vertices)
        for i, j in mesh.edges:
            clipped = clip_segment_near(pc[i], pc[j], cam.near)
            if clipped is None:
                continue
            a, b = clipped
            segs.append(perspective_divide(cam, np.vstack([a, b])))
            cols.append(tuple(mesh.color))
            depths.append(0.5 * (a[2] + b[2]))
            act.append(bool(mesh.active))
    return DrawPrimitives2D(segments=np.array(segs, dtype=float).reshape(-1, 2, 2),
                            seg_colors=cols,
                            seg_depths=np.array(depths, dtype=float),
                            seg_active=np.array(act, dtype=bool),
                            polygons=[])
