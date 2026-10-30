# Uso de IA y agentes

Registro exigido por el enunciado (§7). Se actualiza en cada PR que incluya código o texto generado con IA.
Todo cambio generado por IA pasa por pull request y revisión humana.

## Herramientas utilizadas

| Herramienta | Para qué se usa | Quién |
| --- | --- | --- |
| Claude | Análisis del enunciado, plan de trabajo, esqueleto del repositorio (E1) | _completar_ |
| Claude | Borrador del código de E3 (escena, cámara y proyección, bucle y dibujo) con sus pruebas | _completar_ |

## Tareas delegadas

| Fecha      | Tarea | Herramienta | PR / commit |
|------------| --- | --- | --- |
| 2026-10-27 | Esqueleto del repositorio, CI, plantillas y documentos base (E1) | Claude | _completar_ |
| 2026-10-28 | Borrador de E3: `scene/` (M, malla local, contenedor, `get_geometry`), `projection/` (K, `look_at`, recorte, `project`), `app/` (ventana, bucle, dibujo) y pruebas | Claude | PR de A, B y C de E3: _completar_ |
| 2026-10-28 | Borrador de E4: catálogo de 6 piezas, `is_planar`, forma canónica, acciones con límites del contenedor, `clean_rotation`, `rot_axis_angle` y pruebas | Claude | PR de E4: _completar_ |
| 2026-10-28 | Borrador de E5: `OrbitCamera`, `clip_polygon_near`, descarte de caras traseras, algoritmo del pintor y pruebas | Claude | PR #8 |
| 2026-10-29 | Borrador de E7: `homography.py`, experimento, pruebas y sección 2 de `docs/INFORME.md` | Claude | PR de E7: pendiente |
| 2026-10-29 | Verificación de E8: revisión del contrato contra el código, `test_contrato_codigo.py`, `test_trazabilidad.py`, `docs/VERIFICACION.md`, documentos de planeación y revisión del historial de PR | Claude | PR de E8: _completar_ |
| 2026-10-28 | Borrador de E6: mapa de teclas y ratón, HUD, renderizador con caras y aristas por profundidad, sección Controles del README y pruebas con eventos simulados | Claude | PR #9 |
| 2026-10-29 | Borrador de E9: `animation.py`, `demo.py`, integración en `main.py`, tecla `V`, `--demo` y `tests/test_smoke.py` | Claude | PR de E9: _completar_ |
| 2026-10-29 | E9 (rol A): caché de la malla local y `tests/test_victoria_escena.py`; R22 y R23 en `docs/VERIFICACION.md` | Claude | PR de E9: _completar_ |


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
| 2026-10-28 | Una prueba "rotación que no cabe" giraba la pieza I alrededor de su propio eje (X), lo que no mueve ninguna celda: la prueba no probaba nada | La prueba falló al correrla | Se reescribió con un caso de respuesta conocida: la I acostada en el piso no puede pararse (`z = −1`) |
| 2026-10-28 | La guía re-ortonormalizaba con SVD tras cada giro; en otra plataforma eso puede dejar `0.9999999999999998` y sacar los vértices de la rejilla | Revisión del razonamiento (en Linux salió exacta en 200 orientaciones, pero no está garantizado) | `clean_rotation`: SVD y, si queda a < `1e-9` de una matriz entera, se toma la entera |
| 2026-10-28 | Una prueba de E5 ponía la cámara justo encima del cubo, mirando recto hacia abajo: caso degenerado de `look_at` | La prueba lanzó `ValueError` | Se corrió el ojo a `(0.6, 0.4, 6)` |
| 2026-10-29 | La primera vista 2 tenía el azimut opuesto a la vista 1 y `H21` presentaba ceros estructurales por simetría | Revisión de la matriz | Se ajustó el azimut de la vista 2 a 145° |
| 2026-10-29 | Los primeros puntos interiores tenían un margen de colinealidad de 9.6 px | Medición del margen | Se eligieron `(1, 3)` y `(4, 2.5)`, alcanzando 28.4 px |
| 2026-10-29 | Los vértices de las piezas producían errores de miles de píxeles | Revisión de resultados | Se explicó el efecto de los rayos casi paralelos al piso y se agregó la mediana |
| 2026-10-29 | Las cifras de error del orden de `1e-13` variaban entre plataformas | Revisión de portabilidad | Se utilizaron valores `< 1e-9` en las tablas |
| 2026-10-29 | 7 desajustes entre `docs/INTERFACES.md` y el código (por ejemplo, §3.3 decía que `run` estaba en `blockout.app` y no se exportaba) | Revisión del contrato contra el código en E8 | Contrato actualizado, `app/__init__.py` exporta `run` y `render_frame`, y `tests/test_contrato_codigo.py` lo vigila |
| 2026-10-29 | La primera versión de `test_contrato_codigo.py` separaba mal `size=(1000,700)` y daba 14 fallos falsos | La prueba falló contra un código correcto | Separar los parámetros solo por comas fuera de paréntesis |
| 2026-10-29 | Los PR #2, #3, #4, #7, #8 y #9 se fusionaron sin aprobación formal; la protección de `main` no estaba activa | Revisión del historial de PR en E8 | Protección de `main` activada, regla "nadie fusiona su propio PR" y revisiones posteriores a la fusión |
| 2026-10-28 | La ayuda del HUD en líneas largas tapaba el borde superior del contenedor | Revisión de la captura | Columna angosta a la izquierda, verificada por una prueba; tecla `H` para ocultarla |
| 2026-10-28 | La guía ponía el FOV en `[` `]`, que en teclado latinoamericano requieren AltGr | Revisión de la distribución de teclado | FOV en `Z` / `X` |
| 2026-10-29 | La fórmula de victoria de la guía hacía saltar las piezas al empezar (en `t = 0` no estaban en su pose) | Comparar la pose en `t = 0` con la original | Curvas `e(s)` y `b(s)` que empiezan y terminan en la pose original |
| 2026-10-29 | Dos giros del guion de la demo sacaban piezas del contenedor y la escena los rechazaba en silencio | `test_ninguna_accion_del_guion_es_rechazada` | Separar la pieza de la pared antes de girarla |
| 2026-10-29 | En la victoria, la pieza de arriba se salía del cuadro | Mosaico de capturas de la demo | Las piezas se juntan hacia la altura media del pozo |
| 2026-10-29 | 360 pasos de 1/60 s suman 5.9999… y la victoria duraba 361 fotogramas | Prueba de duración | Tolerancia de `1e-9` |
| 2026-10-29 | `get_geometry` reconstruía la malla de cada pieza en cada fotograma (31 % del tiempo): la demo con caras iba a 63 fps posibles | Perfilado de la demo | Malla en caché por forma, de solo lectura: 93 fps |
