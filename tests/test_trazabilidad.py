"""Integración (E8, ampliada en E9): docs/VERIFICACION.md no cita pruebas que no existen.

Cada fila R01–R23 nombra una prueba como `tests/archivo.py::nombre`. Aquí se comprueba que están los 23
requisitos, una vez cada uno, y que cada prueba citada está definida en ese archivo. Así la tabla de
trazabilidad no puede quedar desactualizada si alguien renombra o borra una prueba.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
DOC = (ROOT / "docs" / "VERIFICACION.md").read_text(encoding="utf-8")
ROW = re.compile(r"^\| (R\d\d) \|.*?`(tests/[\w/]+\.py)::(\w+)`", re.MULTILINE)


def test_estan_los_23_requisitos_una_vez_cada_uno():
    ids = [m.group(1) for m in ROW.finditer(DOC)]
    assert ids == [f"R{i:02d}" for i in range(1, 24)], ids


def test_cada_prueba_citada_existe():
    for m in ROW.finditer(DOC):
        req, path, name = m.groups()
        source = (ROOT / path).read_text(encoding="utf-8")
        assert re.search(rf"^def {name}\(", source, re.MULTILINE), f"{req}: {path}::{name} no existe"
