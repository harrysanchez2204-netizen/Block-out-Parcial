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


def clip_polygon_near(poly_cam: np.ndarray, near: float) -> np.ndarray:
    """Polígono (n,3) en coords de CÁMARA -> polígono recortado a z ≥ near (m,3), o vacío (0,3).

    Sutherland–Hodgman contra un solo plano: se recorre el borde arista por arista (p -> q):
      * p adentro              -> se conserva p;
      * p y q a lados distintos -> se agrega el punto de corte, el mismo s = (near − p_z)/(q_z − p_z)
                                   que usa clip_segment_near.
    El polígono resultante sigue siendo convexo si el original lo era (un cuadrilátero recortado
    queda con 3, 4 o 5 vértices). Con menos de 3 vértices no es una cara y se descarta.
    """
    poly = np.asarray(poly_cam, dtype=float)
    out = []
    n = len(poly)
    for k in range(n):
        p, q = poly[k], poly[(k + 1) % n]
        p_in, q_in = p[2] >= near, q[2] >= near
        if p_in:
            out.append(p)
        if p_in != q_in:
            s = (near - p[2]) / (q[2] - p[2])
            r = p + s * (q - p)
            r[2] = near
            out.append(r)
    return np.array(out, dtype=float) if len(out) >= 3 else np.empty((0, 3))


def is_back_face(quad_cam: np.ndarray) -> bool:
    """Cara (≥3 vértices, coords de CÁMARA, antihoraria vista desde afuera) -> True si da la espalda.

    La normal exterior es n = (P1 − P0) × (P2 − P0) (regla de la mano derecha con el orden
    antihorario, docs/INTERFACES.md §2 `faces`). La cámara está en el origen, así que el vector de la
    cara hacia la cámara es −c, con c el centroide. La cara es visible si la normal apunta hacia la
    cámara: n · (−c) > 0, es decir n · c < 0. Si n · c ≥ 0 la cara se ve "de espaldas" (o de canto).
    Se usa la cara SIN recortar: el recorte no cambia su orientación y así no depende de él.
    """
    q = np.asarray(quad_cam, dtype=float)
    n = np.cross(q[1] - q[0], q[2] - q[0])
    return float(np.dot(n, q.mean(axis=0))) >= 0.0


def project(geometry: Geometry3D, cam: Camera, fill_faces: bool = False) -> DrawPrimitives2D:
    """Geometry3D (mundo) -> DrawPrimitives2D (píxeles).

    Aristas (siempre): mundo -> cámara, recorte contra z = near, división en perspectiva. Las que
    quedan completamente detrás se descartan.

    Caras (solo si fill_faces=True, R16): para cada cara
      1. descarte de caras traseras (`is_back_face`): en un objeto cerrado, las caras que dan la
         espalda quedan tapadas por las de adelante, así que no se dibujan;
      2. recorte contra z = near (`clip_polygon_near`) y división en perspectiva;
      3. algoritmo del pintor: se ordenan de LEJOS a CERCA por la profundidad media del polígono
         recortado, para que al dibujarlas en ese orden las cercanas tapen a las lejanas.
    Limitación conocida del pintor: ordena caras completas por un solo número, así que dos caras
    que se cruzan o se solapan en profundidad pueden quedar en orden incorrecto. Para cubos
    alineados a la rejilla y sin piezas cruzadas no pasa en la práctica; va en el informe.
    """
    segs, cols, depths, act, polys = [], [], [], [], []
    for mesh in geometry.meshes:
        if len(mesh.vertices) == 0:
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
        if fill_faces:
            for face in mesh.faces:
                quad = pc[face]
                if is_back_face(quad):
                    continue
                clipped = clip_polygon_near(quad, cam.near)
                if len(clipped) == 0:
                    continue
                polys.append((perspective_divide(cam, clipped), tuple(mesh.color),
                              float(clipped[:, 2].mean())))
    polys.sort(key=lambda poly: -poly[2])          # estable: empates conservan el orden de entrada
    return DrawPrimitives2D(segments=np.array(segs, dtype=float).reshape(-1, 2, 2),
                            seg_colors=cols,
                            seg_depths=np.array(depths, dtype=float),
                            seg_active=np.array(act, dtype=bool),
                            polygons=polys)
