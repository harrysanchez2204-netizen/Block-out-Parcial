# Blockout desde una cámara móvil

Proyecto de Visión por Computador (Ingeniería Electrónica, UTP, 2026-II). Visualización 3D interactiva
inspirada en Blockout: la escena vive en coordenadas 3D del mundo y se proyecta a la pantalla con una
matriz de cámara implementada por el equipo (λ·[u v 1]ᵀ = K [R|t] M [X Y Z 1]ᵀ).

**Estado:** E8 — prototipo interactivo (Hito 3): 6 piezas, controles de pieza y cámara, HUD, caras rellenas y
experimento de homografía. Ver `docs/SEGUIMIENTO.md` y la verificación en `docs/VERIFICACION.md`.

Antes de escribir código en `scene/`, `projection/` o `app/`, leer **`docs/INTERFACES.md`**: ahí están los
sistemas de coordenadas, las estructuras compartidas, las funciones públicas de cada módulo y el ejemplo
numérico que los tres deben reproducir (`tests/fixtures/shared_example.json`).

## Equipo y roles

| Rol | Responsable | Usuario Git |
| --- | --- | --- |
| A · Escena y geometría | Emmanuel Parra Ocampo | @ZXemmp |
| B · Cámara y proyección | Juan Sebastián Atis Chaves | @juanatis |
| C · Interfaz y animación | Harrinson Quitumbo Sanchez | @harrysanchez2204-netizen |

Coordinador de seguimiento: _se define en la sesión de E8_. Detalles en `docs/ROLES.md`.

## Instalación

Requiere Python 3.10 o superior.

**Linux / macOS**

```bash
git clone https://github.com/harrysanchez2204-netizen/Block-out-Parcial.git && cd Block-out-Parcial
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .
pytest -q
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/harrysanchez2204-netizen/Block-out-Parcial.git; cd Block-out-Parcial
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pip install -e .
pytest -q
```

## Ejecución

```bash
python -m blockout                              # aplicación interactiva
python -m blockout --demo                       # demostración determinista (20 s; Enter la repite)
python experiments/homography_experiment.py     # experimento de homografía -> results/
```

## Modo demostración

`python -m blockout --demo` corre un guion fijo de 20 segundos: la escena quieta, transformaciones de
piezas (incluidas las dos no planarias), caras rellenas, movimientos de cámara y la animación de victoria con
la cámara orbitando. El guion va por número de fotograma y no usa el reloj ni números al azar, así que
siempre hace exactamente lo mismo. Durante la demo se ignoran el ratón y el teclado, salvo `Esc` (salir),
`H` (ayuda), `G` (caras) y `Enter` (repetir desde el principio).

## Controles

La misma ayuda aparece en una columna a la izquierda de la ventana (`H` la oculta). `tests/test_interfaz.py`
comprueba que este bloque es idéntico a la ayuda del HUD.

```
PIEZA (ejes del mundo)
  Tab / 1-6    elegir
  A/D S/W F/R  mover en X Y Z
  I/K J/L U/O  rotar en X Y Z
CAMARA
  arrastrar o flechas  orbitar
  rueda o RePag/AvPag  distancia
  Z/X  campo de vision
  C    vista inicial
V victoria   G caras
H ayuda   Esc salir
```

| Control | Efecto | Qué cambia |
| --- | --- | --- |
| `Tab` / `1`–`6` | Pieza siguiente / pieza por número | Escena (A) |
| `A` `D` · `S` `W` · `F` `R` | Mover la pieza activa 1 cubo en −X +X · −Y +Y · −Z +Z | Escena (A) |
| `I` `K` · `J` `L` · `U` `O` | Girar 90° alrededor de X · Y · Z del **mundo**, por el pivote | Escena (A) |
| Arrastrar con el botón izquierdo · flechas | Orbitar alrededor del contenedor (5° por flecha) | Cámara (B) |
| Rueda · `RePág` `AvPág` | Acercar / alejar la cámara (cambia su posición) | Cámara (B) |
| `Z` `X` | Cerrar / abrir el campo de visión 5° (cambia `K`, no la posición) | Cámara (B) |
| `C` | Volver a la vista inicial | Cámara (B) |
| `G` | Activar / desactivar caras rellenas | Aplicación (C) |
| `H` | Mostrar / ocultar esta ayuda en pantalla | Aplicación (C) |
| `V` | Animación de victoria (6 s). Mientras dura, las piezas no responden pero la cámara sí | Escena (A), vía C |
| `Esc` | Salir | Aplicación (C) |

Si una pieza no se mueve, el movimiento la sacaría del contenedor y se rechaza; el HUD lo avisa. Los ejes
son los del mundo: `X` a la derecha, `Y` hacia el fondo y `Z` hacia arriba en la vista inicial. Se usan
letras, y no `[` `]`, porque las letras están en el mismo lugar en cualquier teclado latino.

## Estructura

```
src/blockout/core/        contratos compartidos (tipos)         — cambian solo por PR de los tres
src/blockout/scene/       módulo A: contenedor, piezas, poses
src/blockout/projection/  módulo B: cámara, proyección, homografía
src/blockout/app/         módulo C: ventana, entrada, animación, demo
experiments/              experimento de homografía (informe)
tests/                    pruebas automáticas
docs/                     interfaces, roles, plan, cronograma, seguimiento, informe
```

## Documentación

`docs/INTERFACES.md` · `docs/ROLES.md` · `docs/PLAN_TRABAJO.md` · `docs/CRONOGRAMA.md` ·
`docs/SEGUIMIENTO.md` · `docs/VERIFICACION.md` · `docs/INFORME.md` · `AI_USAGE.md`
