# Seguimiento semanal

Una entrada por semana (como mínimo): fechas reales, bloqueos, decisiones y ajustes de cronograma, con
enlaces a commits y PR.

## Semana 1 — desde 2026-10-27

- **Hecho:** esqueleto del repositorio, CI en Linux y Windows (T01) — PR #1 fusionado.
- **Hecho:** contrato entre módulos (T02, T03) — `docs/INTERFACES.md`, `src/blockout/core/types.py`,
  `tests/fixtures/shared_example.json` y `tests/test_contratos.py` en el PR de la rama `feat/e2-contratos`.
- **En curso:** aprobación del PR de contrato por los tres integrantes; PR de prueba de A y B; protección
  de la rama `main` y tablero.
- **Bloqueos:** _completar_
- **Decisiones:**
  - Mundo de mano derecha con `Z` hacia arriba y piso en `Z = 0`; unidad = 1 cubo.
  - Cámara con convención de OpenCV (`y` hacia abajo, `z` hacia adelante) para que `(u, v)` se dibuje
    directo en pygame sin invertir nada.
  - `K` a partir del FOV **horizontal**, `fx = fy`, centro en el medio de la imagen.
  - El pivote de cada pieza es el **centro de un cubo** (`pivot_cell`), y `Pose.position` es dónde queda ese
    pivote en el mundo: así `M = [[R, p − R·pivot], [0, 1]]` deja el pivote quieto al rotar.
  - La escena solo cambia por `apply_action`, que **devuelve una escena nueva** (estructuras inmutables);
    las acciones inválidas se ignoran en vez de lanzar excepción.
  - Mover la cámara no toca la escena y transformar una pieza no toca la cámara.
  - Los puntos con `z_cam ≤ near` nunca se dividen: se marcan no visibles (`NaN`) y las aristas se recortan.
- **Cambios de cronograma:** _completar_
