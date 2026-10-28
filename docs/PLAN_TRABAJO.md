# Plan de trabajo

Estados: Pendiente · En curso · En revisión · Terminada. Las fechas están en `docs/CRONOGRAMA.md`.
Cada tarea se enlaza con sus commits y PR en `docs/SEGUIMIENTO.md`.

| ID | Etapa | Tarea | Responsable | Depende de | Criterio de finalización | Estado |
| --- | --- | --- | --- | --- | --- | --- |
| T01 | E1 | Repositorio, protección de rama, plantilla de PR, CI, tablero | Coordinador | — | Los tres abrieron un PR de prueba aprobado; CI verde en Linux y Windows | En curso |
| T02 | E2 | Convenciones y `docs/INTERFACES.md` | A + B + C | T01 | PR de contrato aprobado por los tres | Pendiente |
| T03 | E2 | `core/types.py` y `tests/fixtures/shared_example.json` | A (tipos), B (ejemplo) | T02 | El ejemplo compartido se reproduce a mano | Pendiente |
| T04 | E3 | Escena mínima: contenedor y una pieza (`get_geometry`) | A | T03 | Geometría 3D en el mundo | Pendiente |
| T05 | E3 | `build_camera`, `project` con recorte | B | T03 | `test_known_projection` pasa | Pendiente |
| T06 | E3 | Ventana, bucle y dibujo de líneas | C | T03 | Se ve el pozo y una pieza en perspectiva | Pendiente |
| T07 | E4 | ≥5 piezas (≥2 no planarias), acciones, pivotes, rigidez | A | T04 | Pruebas de rigidez y pivote pasan; revisa C | Pendiente |
| T08 | E5 | `OrbitCamera`, FOV, reset, recorte robusto | B | T05 | Cero fallos en prueba aleatoria; revisa A | Pendiente |
| T09 | E6 | Entrada, HUD, controles | C | T06 | README lista los mismos controles que el HUD; revisa B | Pendiente |
| T10 | E7 | Experimento de homografía y derivación | B | T05 | Tabla de errores y explicación fuera del plano; revisa A | Pendiente |
| T11 | E8 | Integración del prototipo (Hito 3) | Todos | T07–T10 | Etiqueta `v0.3-prototipo` | Pendiente |
| T12 | E9 | Animación de victoria y modo demo | C (+A) | T11 | La demo deja las mismas poses finales en dos ejecuciones | Pendiente |
| T13 | E10 | Pruebas, informe, README, AI_USAGE, contribuciones, video, etiqueta `v1.0` | Todos | T12 | Lista de entregables del enunciado §10 completa | Pendiente |
