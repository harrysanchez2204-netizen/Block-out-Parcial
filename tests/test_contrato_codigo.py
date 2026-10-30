"""Integración (E8): docs/INTERFACES.md §3 y el código dicen lo mismo.

Se leen las tablas de funciones públicas del contrato y, para cada fila, se comprueba que la función
existe en el módulo que dice el documento y que sus parámetros se llaman igual y en el mismo orden.
Si alguien cambia una firma sin un PR de contrato, o documenta algo que no existe, esta prueba falla.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import importlib
import inspect
import re
from pathlib import Path

import pytest

DOC = (Path(__file__).parents[1] / "docs" / "INTERFACES.md").read_text(encoding="utf-8")

# Subsección del documento -> módulo desde el que se importan sus funciones.
SECTIONS = {
    "### 3.1 Módulo A": "blockout.scene",
    "### 3.2 Módulo B": "blockout.projection",
    "Homografía, en `blockout.projection.homography`": "blockout.projection.homography",
    "### 3.3 Módulo C": "blockout.app",
}
PENDING = "**E9**, todavía no existe"


def _section(title: str) -> str:
    """Texto desde `title` hasta el siguiente encabezado o la siguiente tabla de otra sección."""
    start = DOC.index(title)
    rest = DOC[start + len(title):]
    ends = [i for i in (rest.find("\n### "), rest.find("\n## "), rest.find("\nHomografía, en"))
            if i != -1]
    return rest[: min(ends)] if ends else rest


def _split_top(args: str) -> list[str]:
    """Separa por comas que NO están dentro de paréntesis: `size=(1000,700)` es un solo parámetro."""
    parts, depth, cur = [], 0, ""
    for ch in args:
        depth += ch == "("
        depth -= ch == ")"
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    return parts + [cur]


def _rows():
    """(módulo, nombre, [parámetros] o None si es una clase, fila pendiente) por cada fila de tabla."""
    out = []
    for title, module in SECTIONS.items():
        for line in _section(title).splitlines():
            m = re.match(r"\|\s*`([A-Za-z_]\w*)(\((.*?)\))?(\s*->[^`]*|\.[^`]*)?`", line)
            if not m or m.group(1) in ("Función",):
                continue
            name, args = m.group(1), m.group(3)
            params = None
            if args is not None:
                args = args.replace("\\|", "|")
                params = [a.split(":")[0].split("=")[0].strip() for a in _split_top(args) if a.strip()]
            out.append((module, name, params, PENDING in line))
    return out


ROWS = _rows()


def test_el_contrato_lista_las_funciones_esperadas():
    nombres = {n for _, n, _, _ in ROWS}
    for esperado in ("create_scene", "apply_action", "get_geometry", "model_matrix", "build_camera",
                     "project", "project_points", "OrbitCamera", "homography_between_views",
                     "run", "render_frame"):
        assert esperado in nombres, esperado
    assert len(ROWS) >= 20


@pytest.mark.parametrize("module,name,params,pending", ROWS, ids=[f"{r[0]}.{r[1]}" for r in ROWS])
def test_cada_funcion_del_contrato_existe_con_esa_firma(module, name, params, pending):
    mod = importlib.import_module(module)
    if pending:
        pytest.skip(f"{name}: el contrato la marca como pendiente para E9")
    assert hasattr(mod, name), f"{module} no tiene {name}, pero el contrato la lista"
    obj = getattr(mod, name)
    if params is None:                                   # fila sin paréntesis: una clase
        assert inspect.isclass(obj)
        return
    real = list(inspect.signature(obj).parameters)
    if inspect.isclass(obj):
        assert real[: len(params)] == params, (name, real)
    else:
        assert real == params, f"{name}: el código tiene {real}, el contrato dice {params}"


def test_orbitcamera_tiene_los_metodos_del_contrato():
    from blockout.projection import OrbitCamera
    cam = OrbitCamera()
    for metodo in ("orbit", "zoom", "set_fov", "reset", "build"):
        assert callable(getattr(cam, metodo)), metodo
    assert cam.eye.shape == (3,)


def test_lo_pendiente_de_e9_sigue_marcado_mientras_no_exista():
    import blockout.app as app
    for _, name, _, pending in ROWS:
        if name in ("VictoryAnimation", "DemoRunner"):
            assert pending or hasattr(app, name), f"{name} no existe y el contrato no lo marca pendiente"
