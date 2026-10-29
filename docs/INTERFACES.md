# Contrato entre módulos (E2)

Este documento es el **acuerdo técnico** del equipo. Todo lo que un módulo le entrega a otro está descrito
aquí: sistemas de coordenadas, estructuras de datos, funciones públicas, qué pasa en los casos raros y quién
es el dueño de cada parte del estado.

Regla práctica: **si no está en este documento, no es parte del contrato** y no se debe usar desde otro
módulo. Si alguien necesita algo nuevo, se cambia primero este documento (ver §9) y después el código.

Módulos y responsables (ver `docs/ROLES.md`):

| Módulo | Carpeta | Responsable |
| --- | --- | --- |
| Contratos compartidos | `src/blockout/core/` | los tres (PR aprobado por todos) |
| A · Escena y geometría | `src/blockout/scene/` | A |
| B · Cámara y proyección | `src/blockout/projection/`, `experiments/` | B |
| C · Interfaz y animación | `src/blockout/app/` | C |

---

## 1. Sistemas de coordenadas

Hay cuatro sistemas. Cada punto del programa vive en uno y solo uno de ellos, y el nombre de la variable
debe decir en cuál: `p_local`, `p_world`, `p_cam`, `uv`.

### 1.1 Mundo (world)

- **Mano derecha.** `X` a la derecha, `Y` hacia el fondo (alejándose del jugador), `Z` hacia arriba.
- **Unidad = 1 cubo.** No hay escalas ni metros: una pieza de 3 cubos mide 3 unidades.
- El **piso del contenedor es el plano `Z = 0`**. La esquina del piso más cercana al origen es `(0, 0, 0)`.
- El contenedor de tamaño `(W, D, H)` ocupa `0 ≤ X ≤ W`, `0 ≤ Y ≤ D`, `0 ≤ Z ≤ H`. Las piezas caen
  en `-Z` (hacia el piso).
- Todas las coordenadas del mundo son `float`, aunque en la práctica las piezas queden en valores medios
  (`.5`) porque los pivotes son centros de cubo.

```
        Z (arriba)
        |
        |      Y (fondo)
        |    /
        |  /
        |/______ X (derecha)
      (0,0,0) = esquina del piso
```

### 1.2 Objeto / local (de cada pieza)

- Una pieza es un conjunto de **cubos unitarios** en celdas enteras `(i, j, k)`.
- La celda `(i, j, k)` ocupa el cubo `[i, i+1] × [j, j+1] × [k, k+1]` en coordenadas locales. Su **centro**
  es `(i+0.5, j+0.5, k+0.5)`.
- El **origen local** es la esquina mínima de la celda `(0, 0, 0)`. Toda pieza tiene al menos una celda y por
  convención incluye la celda `(0, 0, 0)`.
- El **pivote** de la pieza es el **centro de uno de sus cubos**, señalado por el índice `pivot_cell`
  dentro de la tupla `cells`. Nunca es una arista ni un vértice: así una rotación de 90° manda cubos a
  cubos y la pieza sigue alineada a la cuadrícula.

### 1.3 Cámara

- **Convención OpenCV:** `x` a la derecha, `y` **hacia abajo**, `z` hacia adelante (eje óptico, hacia la
  escena). Es mano derecha.
- Un punto es visible solo si `z_cam > near`. Lo que está detrás de la cámara tiene `z_cam ≤ 0`.
- Paso mundo → cámara: `X_cam = R · X_world + t`, con `R` de 3×3 (rotación) y `t` de 3×1 (traslación).
- El **centro de la cámara** en el mundo es `C = -Rᵀ · t`.

### 1.4 Imagen

- `u` hacia la derecha, `v` **hacia abajo**, origen en la **esquina superior izquierda**. Unidad: píxeles.
- Es el mismo sistema de la ventana de pygame, así que la interfaz dibuja `(u, v)` sin convertir nada.
- Consecuencia que conviene recordar: subir en el mundo (`+Z`) hace **bajar** `v`.

### 1.5 Cadena completa de transformación

```
[X Y Z 1]ᵀ  --M(4x4)-->  mundo  --[R|t](3x4)-->  cámara  --K(3x3)-->  λ[u v 1]ᵀ
   local                                                                 ↓ dividir por λ = z_cam
                                                                      (u, v) píxeles
```

`λ · [u v 1]ᵀ = K · [R | t] · M · [X Y Z 1]ᵀ`, donde `λ = z_cam`. El orden de los factores **no se
cambia**: `M` primero (local → mundo), `[R|t]` después (mundo → cámara), `K` al final (cámara → píxeles).

Matriz de modelo de una pieza, con `R` y `p` de su pose y `pivot_local` el centro del cubo pivote:

```
M = [ R   p - R·pivot_local ]
    [ 0            1        ]
```

Así `M · pivot_local = p` siempre: **el pivote no se mueve al rotar**.

Intrínsecos a partir del campo de visión **horizontal** `fov`, con imagen de `width × height`:

```
f = (width / 2) / tan(fov / 2)        fx = fy = f   (píxeles cuadrados, sin sesgo)
K = [ f  0  cx ]                      cx = width / 2
    [ 0  f  cy ]                      cy = height / 2
    [ 0  0   1 ]
```

---

## 2. Estructuras compartidas (`src/blockout/core/types.py`)

Son `dataclass`. Las que describen estado del juego son **inmutables** (`frozen=True`): para cambiar algo
se construye una copia nueva. Esto evita que dos módulos se pisen el estado.

Ningún módulo define sus propias versiones de estas clases ni les agrega atributos por fuera.

### `Pose`
| Campo | Tipo / forma | Significado |
| --- | --- | --- |
| `rotation` | `(3,3)` float | Rotación de la pieza respecto al mundo. Ortonormal, `det = +1`. |
| `position` | `(3,)` float | Posición en el **mundo del pivote** de la pieza (no de su esquina). |

### `Piece`
| Campo | Tipo / forma | Significado |
| --- | --- | --- |
| `id` | `int` | Identificador estable (índice en `Scene.pieces`). |
| `name` | `str` | Nombre del catálogo (`"I"`, `"L"`, `"Tripode"`, …). |
| `cells` | `tuple[tuple[int,int,int], ...]` | Celdas enteras ocupadas, en coordenadas locales. |
| `pivot_cell` | `int` | Índice dentro de `cells` del cubo cuyo centro es el pivote. |
| `pose` | `Pose` | Pose actual. |
| `color` | `tuple[int,int,int]` | Color RGB, 0–255. |
| `pivot_local` | propiedad `(3,)` | `cells[pivot_cell] + 0.5`. Se calcula, no se guarda. |

### `Container`
| Campo | Tipo | Significado |
| --- | --- | --- |
| `size` | `tuple[int,int,int]` | `(W, D, H)` en cubos. Por defecto `(5, 5, 10)`. |

### `Scene` — el estado del juego
| Campo | Tipo | Significado |
| --- | --- | --- |
| `container` | `Container` | Pozo. |
| `pieces` | `tuple[Piece, ...]` | Piezas. El orden define los `id`. |
| `active` | `int` | Índice de la pieza seleccionada. Siempre válido (`0 ≤ active < len(pieces)`). |
| `time` | `float` | Tiempo lógico en segundos. Lo usa la animación. |
| `status` | `str` | `"playing"` o `"victory"`. |

**La escena no sabe nada de cámara, de píxeles ni de pygame.** No tiene campos de color de fondo, de
ventana ni de teclas.

### `Action` — la única forma de cambiar la escena
| Campo | Tipo | Se usa en |
| --- | --- | --- |
| `kind` | `str` | obligatorio: `"select"`, `"select_next"`, `"translate"`, `"rotate"`, `"set_pose"`, `"set_status"` |
| `piece` | `int \| None` | pieza objetivo; `None` = la pieza activa |
| `axis` | `int \| None` | `0 = X`, `1 = Y`, `2 = Z` (`rotate`) — **ejes del mundo** |
| `steps` | `int` | cuartos de vuelta, con signo (`rotate`) |
| `delta` | `tuple[int,int,int]` | desplazamiento en cubos (`translate`) |
| `pose` | `Pose \| None` | pose completa (`set_pose`, lo usa la animación) |
| `value` | `str \| None` | nuevo estado (`set_status`) |

### `Mesh3D` y `Geometry3D` — lo que A entrega a B
| Campo | Tipo / forma | Significado |
| --- | --- | --- |
| `name` | `str` | Nombre (pieza o `"container"`). |
| `vertices` | `(N,3)` float | Vértices **ya en coordenadas del mundo** (es decir, con `M` aplicada). |
| `edges` | `(E,2)` int | Índices a `vertices`. |
| `faces` | `(F,4)` int | Cuadriláteros, índices a `vertices`, con orientación **antihoraria vista desde afuera**. |
| `color` | `tuple[int,int,int]` | Color RGB. |
| `active` | `bool` | `True` si es la pieza seleccionada (se dibuja más gruesa). |

`Geometry3D.meshes` es la lista de `Mesh3D`. Primero el contenedor, después las piezas en orden de `id`.

### `Camera` — lo que B construye
| Campo | Tipo / forma | Significado |
| --- | --- | --- |
| `K` | `(3,3)` | Intrínsecos. |
| `R` | `(3,3)` | Rotación mundo → cámara. |
| `t` | `(3,)` | Traslación mundo → cámara. |
| `width`, `height` | `int` | Tamaño de la imagen en píxeles. |
| `near` | `float` | Plano cercano, por defecto `0.1`. |
| `center` | propiedad `(3,)` | `-Rᵀ t`, posición de la cámara en el mundo. |
| `P` | propiedad `(3,4)` | `K [R \| t]`. |

### `DrawPrimitives2D` — lo que B entrega a C
| Campo | Tipo / forma | Significado |
| --- | --- | --- |
| `segments` | `(S,2,2)` float | Segmentos ya recortados y proyectados: `[[u0,v0],[u1,v1]]`. |
| `seg_colors` | `list[tuple]`, largo `S` | Color de cada segmento. |
| `seg_depths` | `(S,)` float | Profundidad media `z_cam` de cada segmento. |
| `seg_active` | `(S,)` bool | Si pertenece a la pieza activa. |
| `polygons` | `list[(pts (n,2), color, depth)]` | Caras rellenas, **ya ordenadas de lejos a cerca**. Vacía si no se piden caras. |

**La interfaz solo recibe esto para dibujar: no conoce el 3D.** Aquí no hay vértices del mundo, ni matrices,
ni piezas.

---

## 3. Funciones públicas

Solo estas funciones se llaman desde otro módulo. Lo que empieza con `_` es privado.

### 3.1 Módulo A — `blockout.scene`

| Función | Entrada | Salida | Errores |
| --- | --- | --- | --- |
| `create_scene(config: dict \| None = None) -> Scene` | `config` con claves opcionales `size` y `pieces` | `Scene` inicial válida | Si `config` es `None` usa los valores por defecto. **Determinista:** el mismo `config` da exactamente la misma escena (sin `random`, sin reloj). |
| `apply_action(scene: Scene, action: Action) -> Scene` | escena y acción | **escena nueva** (la de entrada no se modifica) | Nunca lanza excepción: una acción inválida (índice fuera de rango, `kind` desconocido, `select` sin pieza) **devuelve la escena sin cambios**. |
| `get_geometry(scene: Scene) -> Geometry3D` | escena | geometría en coordenadas del **mundo** | Función pura: no modifica la escena. |
| `model_matrix(piece: Piece) -> (4,4)` | pieza | `M` local → mundo | — |
| `rot_axis_exact(axis: int, quarter_turns: int) -> (3,3)` | eje `0/1/2`, giros con signo | rotación con entradas exactas en `{-1, 0, 1}` | `quarter_turns` se toma módulo 4. |
| `transform_points(M, pts) -> (N,3)` | `M (4,4)`, `pts (N,3)` | puntos transformados | — |
| `rot_axis_angle(axis_vec, angle_rad) -> (3,3)` | eje cualquiera `(3,)`, ángulo en radianes | rotación continua (Rodrigues), para la animación de victoria | `ValueError` si el eje es el vector cero. |
| `occupied_cells(piece) -> (n,3) int` | pieza | celdas enteras del contenedor que ocupa en el mundo | — |

### 3.2 Módulo B — `blockout.projection`

| Función | Entrada | Salida | Errores |
| --- | --- | --- | --- |
| `intrinsics_from_fov(width, height, fov_deg) -> (3,3)` | enteros y grados | `K` | `fov_deg` en `(0, 180)`. |
| `look_at(eye, target, up=(0,0,1)) -> (R, t)` | puntos del mundo | extrínsecos | Falla si la dirección de vista es paralela a `up`: por eso la elevación de la cámara se limita a ±89°. |
| `build_camera(eye, target, width, height, fov_deg=50, near=0.1) -> Camera` | — | `Camera` | — |
| `project_points(cam, pts_world) -> (uv, z, visible)` | `pts_world (N,3)` | `uv (N,2)`, `z (N,)`, `visible (N,) bool` | Los puntos con `z ≤ near` se marcan `visible = False` y su `uv` es `NaN`: **jamás se divide por ~0**. |
| `project(geometry, cam, fill_faces=False) -> DrawPrimitives2D` | geometría del mundo | primitivas 2D | Recorta aristas contra el plano cercano; descarta las que quedan completamente detrás. |
| `clip_segment_near(a, b, near)` | extremos en coords de **cámara** | `(a', b')` o `None` | `None` = el segmento está completamente detrás. |
| `OrbitCamera` | estado `target, azimuth, elevation, distance, fov` | `.build(w, h) -> Camera` | `elevation` se limita a ±89°, `distance` a `[2, 80]`, `fov` a `[15, 120]`. `.reset()` vuelve al estado inicial. |

`OrbitCamera` tiene además `.orbit(d_az, d_el)`, `.zoom(factor)`, `.set_fov(fov)` y la propiedad `.eye`:

```
eye = target + distance · (cos(el)·cos(az),  cos(el)·sin(az),  sin(el))
```

### 3.3 Módulo C — `blockout.app`

| Función | Entrada | Salida |
| --- | --- | --- |
| `run(demo=False, size=(1000,700), max_frames=None)` | banderas | abre la ventana y corre el bucle |
| `render_frame(surface, font, prim, hud_lines)` | `DrawPrimitives2D` | dibuja en la superficie |
| `VictoryAnimation(scene).step(dt) -> list[Action]` | `dt` en segundos | acciones `set_pose` |
| `DemoRunner().tick() -> list[(frame, kind, data)]` | — | eventos del guion del fotograma actual |

---

## 4. Quién es dueño de qué estado

| Estado | Dueño | Quién lo lee | Quién lo escribe |
| --- | --- | --- | --- |
| `Scene` (contenedor, piezas, poses, activa, estado) | A | B (vía `get_geometry`), C | **solo** `apply_action` |
| `OrbitCamera` (azimut, elevación, distancia, FOV) | B | C | C, llamando a los métodos de `OrbitCamera` |
| Ventana, teclado, ratón, HUD, fotogramas | C | — | C |
| Tiempo de la animación | C (`VictoryAnimation`) | — | C |

Dos reglas que sostienen todo lo demás:

1. **Mover la cámara nunca cambia la escena.** `orbit`, `zoom`, `set_fov` y `reset` solo tocan
   `OrbitCamera`. Las posiciones de las piezas en el mundo quedan idénticas.
2. **Transformar una pieza nunca cambia la cámara.** `translate` y `rotate` solo producen una `Scene` nueva.

Una forma de comprobarlo en una prueba: orbitar la cámara y verificar que `get_geometry(scene)` devuelve
exactamente los mismos vértices.

---

## 5. Flujo de un fotograma

Es de **una sola dirección**. Nadie devuelve datos hacia atrás.

```
teclado / ratón / guion de la demo        (C)
        │  Action                              OrbitCamera.orbit/zoom/...   (C→B)
        ▼                                             │
  apply_action(scene, action) ──► Scene nueva          ▼
        │                                     OrbitCamera.build(w,h) ──► Camera
        ▼                                                     │
  get_geometry(scene) ──► Geometry3D (mundo) ──► project(geometry, camera) ──► DrawPrimitives2D
                                                                                      │
                                                                       render_frame(...)  (C)
```

### Cómo modifican el estado la entrada del usuario y la animación

- **Entrada del usuario:** cada tecla se traduce a una `Action` y se aplica con `apply_action`. La interfaz
  **no** toca `scene.pieces` ni `pose.position` directamente.
- **Animación de victoria:** recibe la escena del instante inicial, y en cada fotograma emite acciones
  `set_pose` con poses calculadas como **función pura del tiempo** (mismo `t` ⇒ mismas poses, sin acumular
  error). Opera sobre la **escena 3D**, nunca sobre píxeles: no mueve imágenes ni dibuja encima. Al
  terminar restaura las poses que había antes y emite `set_status("playing")`.
- **Modo demo:** el guion está fijado por **número de fotograma** (no por reloj real) y no usa `random` ni
  `time.time()`. En modo demo se ignora el ratón. Dos ejecuciones producen la misma secuencia y las mismas
  poses finales.

---

## 6. Casos límite y qué se espera en cada uno

| Caso | Comportamiento acordado |
| --- | --- |
| Punto detrás de la cámara (`z_cam ≤ 0`) | No se proyecta. En `project_points`: `visible = False`, `uv = NaN`. |
| Punto entre la cámara y el plano cercano (`0 < z_cam ≤ near`) | Igual que el anterior: no visible. |
| Arista con un extremo adelante y otro atrás | Se **recorta** en `z = near` por interpolación lineal y se dibuja la parte visible. |
| Cara con vértices a ambos lados | Sutherland–Hodgman contra `z = near`. Si quedan menos de 3 vértices, se descarta. |
| Cara que mira hacia otro lado | Se descarta (backface culling) antes de dibujar. |
| Acción con `piece` fuera de rango o `kind` desconocido | `apply_action` devuelve la escena **sin cambios**, sin excepción. |
| `select` sin `piece` | Devuelve la escena sin cambios (no cambia la selección). |
| Rotaciones acumuladas | Se usan matrices exactas de 90° y se re-ortonormaliza con SVD: la pieza no se deforma ni se desalinea. Si el resultado está a menos de `1e-9` de una matriz con entradas en `{-1,0,1}`, se toma esa (la SVD varía entre plataformas). |
| `translate` o `rotate` que dejaría alguna celda fuera del contenedor | Se rechaza: `apply_action` devuelve la escena **sin cambios**. No se buscan posiciones alternativas. |
| `translate` con `delta` no entero o mal formado | Escena sin cambios: solo se avanza un número entero de cubos para no salir de la rejilla. |
| `set_pose` | **Sin límites** de contenedor (la animación puede sacar las piezas). Exige rotación `(3,3)` y posición `(3,)` finitas; la rotación se limpia igual que en `rotate`. |
| Piezas que se cruzan entre sí | No se detecta: las colisiones entre piezas son opcionales (R34). |
| Elevación de la cámara en ±90° | Se limita a ±89° para que `look_at` no sea degenerado. |
| Coordenadas de píxel enormes (extremo casi en el plano de la cámara) | La interfaz descarta segmentos con coordenadas > 1e5 en vez de dibujar basura. |

---

## 7. Ejemplo compartido

Está en `tests/fixtures/shared_example.json` y lo verifica `tests/test_contratos.py`. **Los tres módulos
deben reproducir estos números**, y se pueden comprobar a mano con lápiz y papel.

### Cámara del ejemplo

`width = 640`, `height = 480`, `fov = 60°`, `near = 0.1`, `eye = (0, -10, 0)`, `target = (0, 0, 0)`,
`up = (0, 0, 1)`.

```
f  = (640/2) / tan(30°) = 320 / 0.5773502692 = 554.2562584220408
K  = [[554.2562584220408, 0, 320], [0, 554.2562584220408, 240], [0, 0, 1]]
R  = [[1, 0, 0], [0, 0, -1], [0, 1, 0]]          t = (0, 0, 10)
```

Lectura de `R`: la fila 1 dice que la derecha de la cámara es `+X` del mundo; la fila 2, que el "abajo" de
la cámara es `-Z` del mundo (o sea, arriba en el mundo es arriba en la pantalla); la fila 3, que la cámara
mira hacia `+Y`. Y `t = -R·eye = (0, 0, 10)`: el origen del mundo está a 10 unidades delante de la cámara.

### Puntos proyectados

| Punto del mundo | `X_cam` | `z_cam` | `(u, v)` | Por qué |
| --- | --- | --- | --- | --- |
| `(0, 0, 0)` | `(0, 0, 10)` | 10 | `(320, 240)` | está en el eje óptico ⇒ cae en el centro de la imagen |
| `(1, 0, 0)` | `(1, 0, 10)` | 10 | `(375.4256258422041, 240)` | `u = 320 + f·1/10 = 320 + 55.4256…` |
| `(0, 0, 1)` | `(0, -1, 10)` | 10 | `(320, 184.57437415779592)` | `v = 240 − f·1/10`: subir en el mundo **baja** `v` |
| `(0, 1, 0)` | `(0, 0, 11)` | 11 | `(320, 240)` | mismo píxel que el origen, **distinta profundidad**: por eso hace falta `z` para ordenar el dibujo |
| `(0, -12, 0)` | `(0, 0, -2)` | −2 | no visible (`NaN`) | detrás de la cámara |

### Matriz de modelo

Pieza en forma de L con `cells = [(0,0,0), (1,0,0), (2,0,0), (0,1,0)]`, `pivot_cell = 0`
(⇒ `pivot_local = (0.5, 0.5, 0.5)`), rotada 90° alrededor de `Z` y con el pivote en `(2.5, 2.5, 0.5)`:

```
R_pose = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]            p = (2.5, 2.5, 0.5)

M = [[0, -1, 0, 3],
     [1,  0, 0, 2],
     [0,  0, 1, 0],
     [0,  0, 0, 1]]          porque  p - R·pivot_local = (2.5,2.5,0.5) - (-0.5,0.5,0.5) = (3, 2, 0)
```

Centros de los cuatro cubos, de local a mundo y a píxeles con la cámara de arriba:

| Centro local | Mundo | `X_cam` | `(u, v)` |
| --- | --- | --- | --- |
| `(0.5, 0.5, 0.5)` (pivote) | `(2.5, 2.5, 0.5)` | `(2.5, -0.5, 12.5)` | `(430.8512516844082, 217.82974966311838)` |
| `(1.5, 0.5, 0.5)` | `(2.5, 3.5, 0.5)` | `(2.5, -0.5, 13.5)` | `(422.6400478559335, 219.4719904288133)` |
| `(2.5, 0.5, 0.5)` | `(2.5, 4.5, 0.5)` | `(2.5, -0.5, 14.5)` | `(415.56142386586913, 220.8877152268262)` |
| `(0.5, 1.5, 0.5)` | `(1.5, 2.5, 0.5)` | `(1.5, -0.5, 12.5)` | `(386.51075101064487, 217.82974966311838)` |

Comprobación clave: el pivote local va a `(2.5, 2.5, 0.5)`, que es exactamente `p`. **El pivote queda
quieto.** Y la hilera de cubos que en local iba en `+X` ahora va en `+Y` en el mundo, como corresponde a un
giro de 90° alrededor de `Z`.

### Cómo lo usa cada módulo

- **A** comprueba que `model_matrix` de esa pieza da esa `M` y que `get_geometry` deja esos centros donde dice.
- **B** comprueba que `build_camera((0,-10,0), (0,0,0), 640, 480, 60)` da esa `K`, esa `R` y esa `t`, y que
  `project_points` da esos `(u, v)` con tolerancia `1e-9`.
- **C** usa el ejemplo como prueba de humo de que lo que dibuja viene de la cadena correcta.

---

## 8. Convenciones de código

- Nombres de variables con el sistema de coordenadas: `p_local`, `p_world`, `p_cam`, `uv`.
- Los arreglos son `numpy` de `float64`; las formas están anotadas en los comentarios (`(N,3)`, `(3,3)`).
- Un módulo **no importa** a otro módulo hermano: `scene` y `projection` solo importan de `core`.
  `app` puede importar de los tres, pero solo las funciones de §3.
- Las funciones de `scene` y `projection` son **puras** (no imprimen, no guardan archivos, no usan reloj).
- Nada de `print` en `scene/` ni en `projection/`.
- Docstring en español, de una línea, diciendo qué entra y qué sale.

---

## 9. Cómo se cambia este contrato

1. Se abre un PR que modifica **este documento** (y `core/types.py` si hace falta).
2. El PR explica qué se rompe y qué módulos hay que ajustar.
3. **Lo aprueban los tres integrantes** (es la excepción a la rotación de revisión de `docs/ROLES.md`).
4. Se fusiona antes de escribir el código que lo usa.

Cambios que **no** necesitan tocar este documento: detalles internos de un módulo, nombres de funciones
privadas, pruebas, colores, mensajes del HUD.
