# Seguimiento semanal

Una entrada por semana (como mínimo): fechas reales, bloqueos, decisiones y ajustes de cronograma, con
enlaces a commits y PR.

## Semana 1 — desde 2026-10-27

- **Hecho:** esqueleto del repositorio, CI en Linux y Windows (T01) — PR #1 fusionado.
- **Hecho:** contrato entre módulos (T02, T03) — `docs/INTERFACES.md`, `src/blockout/core/types.py`,
  `tests/fixtures/shared_example.json` y `tests/test_contratos.py` en el PR de la rama `feat/e2-contratos`.
- **Hecho (2026-10-28):** PR #2 de contrato fusionado en `main` (`26cd9f2`) → Hito 1.
- **Hecho (2026-10-28):** primera integración (E3). A: `61e6906`; B: PR #3; C: PR #4 (`6dce4e5`) → Hito 2.
  Evidencia: `docs/img/e3_primera_integracion.png`.
- **Hecho (2026-10-28):** E4, 6 piezas y acciones con límites (PR #6, revisado y aprobado por C) y su
  contrato (PR #7).
- **Hecho (2026-10-28):** E5, cámara orbital, recorte de polígonos y caras rellenas (PR #8).
- **Hecho (2026-10-29):** E6, controles de teclado y ratón, HUD y dibujo por profundidad (PR #9).
- **Hecho (2026-10-29):** E7, experimento de homografía (PR #10, `858f74d`). Resultados en `docs/INFORME.md` §2.
- **Hecho (2026-10-29):** capturas de E4 restauradas y uso de IA de E4 registrado (PR #11).
- **En curso:** E8, integración del prototipo (`docs/e8-integracion`). Verificación R01–R21 en
  `docs/VERIFICACION.md`; 7 desajustes entre el contrato y el código corregidos.
- **Bloqueos y problemas de proceso (encontrados en E8):**
  - La protección de `main` no está activa. Los PR #2, #3, #4, #7, #8 y #9 se fusionaron **sin aprobación
    formal**; #7 y #9 los fusionó su propio autor. Solo el PR #6 tiene una revisión completa. Los dos PR de
    contrato (#2 y #7) pedían tres aprobaciones y no tienen ninguna.
  - `61e6906` (E3, rol A) entró a `main` sin PR.
  - El primer commit de E4 (`320add1`) agregó copias sueltas de archivos fuera de `scene/`; el segundo las
    borró junto con las capturas `docs/img/e4_*.png`.
  - Tres commits de E1 y E2 (`0d7e02c`, `dc4b431`, `05ec5b3`) quedaron con el autor "Claude" en lugar de un
    integrante. No se reescriben (cambiaría la historia de `main`); se declaran en `AI_USAGE.md` y en la
    declaración de contribuciones.
  - No existían las etiquetas de hito `v0.1-diseno` ni `v0.2-integracion`.
- **Acciones acordadas en E8:** activar la protección de `main`; revisar a posteriori los PR #8 y #9 dejando
  constancia de que la revisión es posterior a la fusión; desde ahora, nadie fusiona su propio PR; crear las
  etiquetas `v0.1-diseno` (`26cd9f2`), `v0.2-integracion` (`6dce4e5`) y `v0.3-prototipo` (merge de E8).
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
  - (E3) Vista inicial: objetivo `(2.5, 2.5, 5)`, azimut −60°, elevación 25°, distancia 22, FOV 50°. Se
    aparta de la guía (objetivo a `z = 4`, distancia 20) porque con esa vista el contenedor se salía por arriba.
  - (E3) El contenedor dibuja rejilla en el piso y en las paredes del fondo (`Y = D`) e izquierda (`X = 0`),
    que son las lejanas desde la vista inicial; las cercanas solo llevan borde para no tapar las piezas.
  - (E4) Los movimientos que sacarían una pieza del contenedor se rechazan; `set_pose` no tiene límites; no se
    detectan colisiones entre piezas (R34, opcional).
  - (E5) La vista inicial de la cámara orbital es la vista fija de E3.
  - (E6) Caras y aristas se dibujan en una sola lista de lejos a cerca. El FOV va en `Z`/`X` porque `[` `]`
    exigen AltGr en el teclado latinoamericano.
  - (E7) Plano del experimento: el piso. Vista 2 en azimut 145° y no en el opuesto exacto (caso simétrico).
- **Cambios de cronograma:** los hitos 2 y 3 se adelantaron. El cronograma los ponía en las semanas 2 y 3–4,
  y E3–E6 se terminaron en la semana 1. Las fechas previstas del curso siguen sin completar en
  `docs/CRONOGRAMA.md`.
