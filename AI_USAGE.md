# Uso de IA y agentes

Registro exigido por el enunciado (§7). Se actualiza en cada PR que incluya código o texto generado con IA.
Todo cambio generado por IA pasa por pull request y revisión humana.

## Herramientas utilizadas

| Herramienta | Para qué se usa | Quién |
| --- | --- | --- |
| Claude | Análisis del enunciado, plan de trabajo, esqueleto del repositorio (E1) | _completar_ |
| Claude | Borrador del código de E3 (escena, cámara y proyección, bucle y dibujo) con sus pruebas | _completar_ |

## Tareas delegadas

| Fecha | Tarea | Herramienta | PR / commit |
| --- | --- | --- | --- |
| 2026-10-27 | Esqueleto del repositorio, CI, plantillas y documentos base (E1) | Claude | _completar_ |
| 2026-10-28 | Borrador de E3: `scene/` (M, malla local, contenedor, `get_geometry`), `projection/` (K, `look_at`, recorte, `project`), `app/` (ventana, bucle, dibujo) y pruebas | Claude | PR de A, B y C de E3: _completar_ |
| 2026-10-28 | Borrador de E5: `OrbitCamera`, `clip_polygon_near`, descarte de caras traseras, algoritmo del pintor y pruebas | Claude | PR #8 |
| 2026-10-29 | Borrador de E7: `homography.py`, experimento, pruebas y sección 2 de `docs/INFORME.md` | Claude | PR de E7: pendiente |

## Cómo se verificó el código y las afirmaciones matemáticas

- **Ejemplo compartido:** las pruebas de A (`test_escena.py`) y de B (`test_proyeccion.py`) comparan contra
  `tests/fixtures/shared_example.json` con tolerancia `1e-9` (M, centros de cubo, K, R, t y los `(u, v)`).
- **Fórmula del enunciado escrita aparte:** `test_integracion_e3.py` calcula `λ[u v 1]ᵀ = K[R|t]M X` con las
  matrices copiadas del JSON, sin usar el código de ningún módulo, y exige que cada arista de la pieza
  proyectada por la aplicación coincida.
- **Conteos hechos a mano:** la L plana tiene 20 vértices, 36 aristas y 18 caras (24 − 2·3 internas); el
  contenedor `(W, D, H)` tiene `piso + fondo + izquierda − (W + D + H) + H + W + D` aristas (290 para 5×5×10).
- **Cada PR por separado:** A y B se probaron solos sobre `main`, y C sobre A + B, en el orden de fusión.
- **Captura sin ventana** (`docs/img/e3_primera_integracion.png`) revisada a ojo: piso en `Z = 0`, `+Z` hacia
  arriba en la pantalla, pieza dentro del contenedor.

## Errores significativos encontrados y corregidos

| Fecha | Qué falló | Cómo se detectó | Corrección |
| --- | --- | --- | --- |
| 2026-10-28 | Con la vista inicial de la guía (objetivo a `z = 4`, distancia 20) el borde superior del contenedor salía en `v < 0` y se montaba sobre el HUD | Rango de `v` de los segmentos proyectados (−8.9) y la captura | Objetivo en el centro real del contenedor `(2.5, 2.5, 5)` y distancia 22: `v ∈ [71, 655]` |
| 2026-10-28 | El borrador de la guía para el contenedor repetía segmentos (las columnas de esquina coincidían con líneas de pared) | Conteo de aristas | Contenedor como conjunto de segmentos unitarios: cada uno aparece una sola vez |
| 2026-10-28 | Una prueba de E5 ponía la cámara justo encima del cubo, mirando recto hacia abajo: caso degenerado de `look_at` | La prueba lanzó `ValueError` | Se corrió el ojo a `(0.6, 0.4, 6)` |
| 2026-10-29 | La primera vista 2 tenía el azimut opuesto a la vista 1 y `H21` presentaba ceros estructurales por simetría | Revisión de la matriz | Se ajustó el azimut de la vista 2 a 145° |
| 2026-10-29 | Los primeros puntos interiores tenían un margen de colinealidad de 9.6 px | Medición del margen | Se eligieron `(1, 3)` y `(4, 2.5)`, alcanzando 28.4 px |
| 2026-10-29 | Los vértices de las piezas producían errores de miles de píxeles | Revisión de resultados | Se explicó el efecto de los rayos casi paralelos al piso y se agregó la mediana |
| 2026-10-29 | Las cifras de error del orden de `1e-13` variaban entre plataformas | Revisión de portabilidad | Se utilizaron valores `< 1e-9` en las tablas |
