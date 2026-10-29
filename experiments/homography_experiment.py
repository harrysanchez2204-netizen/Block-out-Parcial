"""Experimento de homografía (E7, rol B con datos de A). Enunciado §3, requisitos R18–R20.

Ejecutar desde la raíz del repositorio (o con clic derecho → Run en PyCharm):

    python experiments/homography_experiment.py

Imprime las tablas y escribe en results/:
    homografia.json   todos los números (lo lee tests/test_homography.py para que el informe no
                      quede con cifras viejas: si cambian las cámaras hay que volver a correr esto)
    homografia.md     las mismas tablas en Markdown, listas para docs/INFORME.md
    homografia.png    figura de las dos vistas con los puntos en el plano y fuera de él

Plano: el piso del contenedor (Z = 0), el "fondo del pozo" del enunciado.
Vistas: la cámara inicial de la aplicación y otra orbitada al lado opuesto, con otro FOV.
Determinista: la única aleatoriedad (el ruido) usa una semilla fija.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from blockout.projection import OrbitCamera, build_camera, project_points
from blockout.projection.homography import (FLOOR_PLANE, apply_homography, collinearity_margin,
                                            estimate_homography_dlt, homography_between_views,
                                            homography_from_plane_normal, plane_to_image_homography,
                                            pure_rotation_homography, reprojection_errors)
from blockout.scene import create_scene, get_geometry

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
W, H = 1000, 700

# Vista 1 = cámara inicial de la aplicación. Vista 2 = casi al lado opuesto del pozo, más alta y con
# otro FOV (K1 ≠ K2). No se usa exactamente el azimut opuesto (−60° + 180° = 120°): con los dos
# centros en el mismo plano vertical por el objetivo, H21 sale con ceros estructurales (una
# configuración simétrica especial). 145° deja una H21 genérica.
VIEW1 = dict(azimuth=-60.0, elevation=25.0, distance=22.0, fov=50.0)
VIEW2 = dict(azimuth=145.0, elevation=40.0, distance=20.0, fov=55.0)

# 4 esquinas del piso + 2 puntos interiores elegidos para alejarse de cualquier trío alineado:
# en las dos imágenes, ningún punto queda a menos de ~28 px de la recta que pasa por otros dos.
FLOOR_PTS = np.array([[0, 0, 0], [5, 0, 0], [5, 5, 0], [0, 5, 0], [1, 3, 0], [4, 2.5, 0]], float)
HEIGHTS = (0.25, 0.5, 1.0, 2.0)      # en cubos; una pieza mide 1
NOISE_SIGMA = 0.5                    # px, desviación del ruido gaussiano en cada coordenada
NOISE_TRIALS = 200
SEED = 2026


def cameras():
    """Las dos cámaras del experimento, construidas con la cámara orbital del módulo B."""
    return OrbitCamera(**VIEW1).build(W, H), OrbitCamera(**VIEW2).build(W, H)


def _err(e: np.ndarray) -> dict:
    return {"medio_px": float(e.mean()), "mediana_px": float(np.median(e)), "max_px": float(e.max())}


def run() -> dict:
    """Corre todos los casos y devuelve un diccionario con los resultados (sin imprimir nada)."""
    c1, c2 = cameras()
    out: dict = {"vistas": {"vista_1": VIEW1, "vista_2": VIEW2, "imagen": [W, H]},
                 "centros": {"vista_1": c1.center.tolist(), "vista_2": c2.center.tolist()}}

    # ---------------------------------------------------------------- 1. derivación analítica
    H1 = plane_to_image_homography(c1, **FLOOR_PLANE)
    H2 = plane_to_image_homography(c2, **FLOOR_PLANE)
    H21 = homography_between_views(c1, c2, **FLOOR_PLANE)
    H21_n = homography_from_plane_normal(c1, c2, n_world=(0, 0, 1), d_world=0.0)
    out["H21"] = H21.tolist()
    out["dos_derivaciones_diferencia_max"] = float(np.abs(H21 - H21_n).max())
    out["matrices"] = {
        "P (3x4)": {"rango": int(np.linalg.matrix_rank(c1.P))},
        "H1 (3x3)": {"rango": int(np.linalg.matrix_rank(H1))},
        "H21 (3x3)": {"rango": int(np.linalg.matrix_rank(H21)), "det": float(np.linalg.det(H21))},
    }

    # ---------------------------------------------------------------- 2. verificación en el plano
    x1, _, v1 = project_points(c1, FLOOR_PTS)
    x2, _, v2 = project_points(c2, FLOOR_PTS)
    assert v1.all() and v2.all(), "algún punto del piso no es visible en las dos vistas"
    out["puntos_piso"] = {
        "mundo": FLOOR_PTS.tolist(), "vista_1_px": x1.tolist(), "vista_2_px": x2.tolist(),
        "margen_colinealidad_px": [collinearity_margin(x1), collinearity_margin(x2)],
    }
    e_plane = reprojection_errors(H21, x1, x2)
    out["en_el_plano"] = {"por_punto_px": e_plane.tolist(), **_err(e_plane)}

    # ---------------------------------------------------------------- 3. DLT sin y con ruido
    Hd = estimate_homography_dlt(x1, x2)
    out["dlt_sin_ruido"] = {"diferencia_con_analitica_max": float(np.abs(Hd - H21).max()),
                            **_err(reprojection_errors(Hd, x1, x2))}

    # Malla densa del piso: mide si la H estimada GENERALIZA a puntos que no usó para estimarse.
    g = np.linspace(0.0, 5.0, 11)
    grid = np.array([[a, b, 0.0] for a in g for b in g])
    g1, _, _ = project_points(c1, grid)
    g2, _, _ = project_points(c2, grid)
    rng = np.random.default_rng(SEED)
    noisy = {}
    for name, idx in (("4_esquinas", [0, 1, 2, 3]), ("6_puntos", list(range(6)))):
        e_pts, e_grid = [], []
        for _ in range(NOISE_TRIALS):
            n1 = x1[idx] + rng.normal(0.0, NOISE_SIGMA, (len(idx), 2))
            n2 = x2[idx] + rng.normal(0.0, NOISE_SIGMA, (len(idx), 2))
            Hn = estimate_homography_dlt(n1, n2)
            # Se compara contra la verdad SIN ruido: así se mide el error de la H, no el del ruido.
            e_pts.append(reprojection_errors(Hn, x1[idx], x2[idx]).mean())
            e_grid.append(reprojection_errors(Hn, g1, g2).mean())
        noisy[name] = {"error_medio_en_sus_puntos_px": float(np.mean(e_pts)),
                       "error_medio_en_malla_px": float(np.mean(e_grid)),
                       "error_malla_percentil_95_px": float(np.percentile(e_grid, 95))}
    out["dlt_con_ruido"] = {"sigma_px": NOISE_SIGMA, "repeticiones": NOISE_TRIALS, "semilla": SEED,
                            **noisy}

    # ---------------------------------------------------------------- 4. fuera del plano (paralaje)
    off = []
    for z in HEIGHTS:
        P = FLOOR_PTS.copy()
        P[:, 2] = z
        a, _, _ = project_points(c1, P)
        b, _, _ = project_points(c2, P)
        off.append({"Z": z, **_err(reprojection_errors(H21, a, b))})
    out["fuera_del_plano"] = off

    # Predicción de la deducción: λ1 x1 = H1 p + Z·e1 y λ2 x2 = H2 p + Z·e2, con eᵢ = Kᵢ·r3ᵢ.
    # H21 aplicada a x1 da H2 p + Z·H21 e1: solo coincide con x2 si Z·(H21 e1 − λ e2) = 0.
    # Se calcula el punto predicho con esa fórmula y se compara con lo que da project_points.
    z = 1.0
    P = FLOOR_PTS.copy()
    P[:, 2] = z
    a, _, _ = project_points(c1, P)
    e1v, e2v = c1.K @ c1.R[:, 2], c2.K @ c2.R[:, 2]
    ph = np.hstack([FLOOR_PTS[:, :2], np.ones((len(P), 1))])
    pred = (ph @ H1.T + z * e1v) @ (H2 @ np.linalg.inv(H1)).T     # H21·(λ1 x1), sin normalizar
    pred = pred[:, :2] / pred[:, 2:3]
    out["paralaje_formula_vs_medido_max_px"] = float(np.abs(pred - apply_homography(H21, a)).max())

    # Datos de A: los vértices reales de las piezas de la escena inicial (alturas 1 a 9).
    verts = np.vstack([m.vertices for m in get_geometry(create_scene()).meshes[1:]])
    a, _, va = project_points(c1, verts)
    b, _, vb = project_points(c2, verts)
    ok = va & vb
    e_pieces = reprojection_errors(H21, a[ok], b[ok])
    out["vertices_de_las_piezas"] = {"n": int(ok.sum()), "Z_min": float(verts[:, 2].min()),
                                     "Z_max": float(verts[:, 2].max()), **_err(e_pieces)}

    # ---------------------------------------------------------------- 5. mismo centro (solo gira)
    # Cámara 3: el MISMO centro que la 1, mirando a otro punto y con otro FOV.
    c3 = build_camera(c1.center, (4.0, 1.0, 1.0), W, H, 60.0)
    H31 = homography_between_views(c1, c3, **FLOOR_PLANE)
    H31_rot = pure_rotation_homography(c1, c3)
    same = []
    for z in HEIGHTS:
        P = FLOOR_PTS.copy()
        P[:, 2] = z
        a, _, _ = project_points(c1, P)
        b, _, _ = project_points(c3, P)
        same.append({"Z": z, **_err(reprojection_errors(H31, a, b))})
    out["mismo_centro"] = {"vista_3": {"centro": c3.center.tolist(), "mira_a": [4.0, 1.0, 1.0],
                                       "fov": 60.0},
                           "H_piso_vs_K2RK1inv_diferencia_max": float(np.abs(H31 - H31_rot).max()),
                           "fuera_del_plano": same}
    return out


def to_markdown(r: dict) -> str:
    """Resultados -> tablas en Markdown para el informe."""
    # Los errores del orden de 1e-13 dependen de la librería de álgebra lineal (cambian entre Linux y
    # Windows). Se escriben como "< 1e-9": así la tabla es idéntica en cualquier máquina y la prueba
    # que compara el informe con este resultado no falla en el CI de Windows.
    f = lambda x: "< 1e-9" if abs(x) < 1e-9 else f"{x:.2f}"          # noqa: E731
    row = lambda name, d: (f"| {name} | {f(d['medio_px'])} | {f(d['mediana_px'])} | "   # noqa: E731
                           f"{f(d['max_px'])} |")
    L = ["| Caso | Error medio (px) | Mediana (px) | Error máximo (px) |", "| --- | --- | --- | --- |",
         row("6 puntos del piso, H21 analítica", r["en_el_plano"]),
         row("6 puntos del piso, H21 estimada por DLT sin ruido", r["dlt_sin_ruido"])]
    for o in r["fuera_del_plano"]:
        L.append(row(f"Mismos 6 puntos elevados a Z = {o['Z']}, misma H21", o))
    p = r["vertices_de_las_piezas"]
    L.append(row(f"{p['n']} vértices de las piezas de la escena (Z de {p['Z_min']:.0f} a "
                 f"{p['Z_max']:.0f}), misma H21", p))
    for o in r["mismo_centro"]["fuera_del_plano"]:
        L.append(row(f"Mismo centro de cámara, puntos a Z = {o['Z']}", o))
    n = r["dlt_con_ruido"]
    L += ["", f"DLT con ruido gaussiano σ = {n['sigma_px']} px en ambas vistas, "
          f"{n['repeticiones']} repeticiones (semilla {n['semilla']}). Error contra la verdad sin ruido:", "",
          "| Puntos usados | En sus puntos (px) | En una malla de 121 puntos del piso (px) | Malla, percentil 95 (px) |",
          "| --- | --- | --- | --- |"]
    for k, label in (("4_esquinas", "4 esquinas (mínimo)"), ("6_puntos", "6 puntos")):
        d = n[k]
        L.append(f"| {label} | {d['error_medio_en_sus_puntos_px']:.3f} | "
                 f"{d['error_medio_en_malla_px']:.3f} | {d['error_malla_percentil_95_px']:.3f} |")
    return "\n".join(L) + "\n"


def save_figure(r: dict, path: Path) -> None:
    """Dos paneles: vista 1 con los puntos, y vista 2 con la verdad y lo que predice H21."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    c1, c2 = cameras()
    H21 = np.array(r["H21"])
    x1 = np.array(r["puntos_piso"]["vista_1_px"])
    x2 = np.array(r["puntos_piso"]["vista_2_px"])
    P = FLOOR_PTS.copy()
    P[:, 2] = 1.0
    a, _, _ = project_points(c1, P)
    b, _, _ = project_points(c2, P)
    order = [0, 1, 2, 3, 0]

    hb = apply_homography(H21, a)                    # lo que H21 predice para los puntos elevados
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.6))
    panels = ((ax[0], "Vista 1: cámara inicial", [x1, a]),
              (ax[1], "Vista 2: otro lado del pozo, otro FOV", [x2, b, hb]))
    for axk, title, pts in panels:
        allp = np.vstack(pts)
        lo, hi = allp.min(axis=0) - 45, allp.max(axis=0) + 45
        axk.set_xlim(lo[0], hi[0])
        axk.set_ylim(hi[1], lo[1])               # v crece hacia abajo, como en la pantalla
        axk.set_aspect("equal")
        axk.set_title(title)
        axk.set_xlabel("u (px)")
        axk.set_ylabel("v (px)")
        axk.grid(alpha=0.25)
    ax[0].plot(*x1[order].T, "-", color="0.65", lw=1, label="borde del piso")
    ax[0].plot(*x1.T, "o", color="tab:blue", label="puntos del piso, Z = 0")
    ax[0].plot(*a.T, "s", color="tab:red", mfc="none", label="mismos puntos a Z = 1")
    ax[1].plot(*x2[order].T, "-", color="0.65", lw=1)
    ax[1].plot(*x2.T, "o", color="tab:blue", label="piso: posición real")
    ax[1].plot(*apply_homography(H21, x1).T, "+", color="k", ms=13, mew=1.5,
               label="piso: H21·x1 (coincide)")
    ax[1].plot(*b.T, "s", color="tab:red", mfc="none", label="Z = 1: posición real")
    ax[1].plot(*hb.T, "x", color="tab:red", ms=9, label="Z = 1: H21·x1 (falla)")
    for p, q in zip(hb, b):                      # flecha: de lo predicho a lo real = paralaje
        ax[1].annotate("", q, p, arrowprops=dict(arrowstyle="->", color="tab:red", lw=0.9))
    for axk, pts in ((ax[0], x1), (ax[1], x2)):
        for i, p in enumerate(pts):
            axk.annotate(str(i + 1), p, textcoords="offset points", xytext=(6, -12), fontsize=9)
    for axk in ax:
        axk.legend(loc="upper right", fontsize=8, framealpha=0.9)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main() -> None:
    r = run()
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "homografia.json").write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n",
                                             encoding="utf-8")
    md = to_markdown(r)
    (RESULTS / "homografia.md").write_text(md, encoding="utf-8")
    save_figure(r, RESULTS / "homografia.png")

    np.set_printoptions(precision=6, suppress=True)
    print("H21 (analítica, H[2,2] = 1) =\n", np.array(r["H21"]))
    print(f"\nDos derivaciones (H2·H1⁻¹ y K2(R + t nᵀ/d)K1⁻¹), diferencia máx = "
          f"{r['dos_derivaciones_diferencia_max']:.1e}")
    m = r["puntos_piso"]["margen_colinealidad_px"]
    print(f"Margen de colinealidad (px): vista 1 = {m[0]:.1f}, vista 2 = {m[1]:.1f}")
    print(f"Paralaje: fórmula contra medido, diferencia máx = "
          f"{r['paralaje_formula_vs_medido_max_px']:.1e} px\n")
    print(md)
    print(f"Archivos escritos en {RESULTS}")


if __name__ == "__main__":
    sys.exit(main())
