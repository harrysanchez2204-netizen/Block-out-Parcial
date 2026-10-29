# Blockout desde una cámara móvil

Proyecto de Visión por Computador (Ingeniería Electrónica, UTP, 2026-II). Visualización 3D interactiva
inspirada en Blockout: la escena vive en coordenadas 3D del mundo y se proyecta a la pantalla con una
matriz de cámara implementada por el equipo (λ·[u v 1]ᵀ = K [R|t] M [X Y Z 1]ᵀ).

**Estado:** E6 — aplicación interactiva con piezas, cámara orbital y HUD. Ver `docs/SEGUIMIENTO.md`.

Antes de escribir código en `scene/`, `projection/` o `app/`, leer **`docs/INTERFACES.md`**: ahí están los
sistemas de coordenadas, las estructuras compartidas, las funciones públicas de cada módulo y el ejemplo
numérico que los tres deben reproducir (`tests/fixtures/shared_example.json`).

## Equipo y roles

| Rol | Responsable | Usuario Git |
| --- | --- | --- |
| A · Escena y geometría | Emmanuel Parra Ocampo | @ZXemmp |
| B · Cámara y proyección | Juan Sebastián Atis Chaves | @usuario_ |
| C · Interfaz y animación | Harrison Quitumbo Sanchez | harrysanchez2204@gmail.com |

Coordinador de seguimiento: _por completar_. Detalles en `docs/ROLES.md`.

## Instalación

Requiere Python 3.10 o superior.

**Linux / macOS**

```bash
git clone <URL-del-repositorio> && cd Block-Out
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .
pytest -q
```

**Windows (PowerShell)**

```powershell
git clone <URL-del-repositorio>; cd Block-Out
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pip install -e .
pytest -q
```

## Ejecución

```bash
python -m blockout          # aplicación interactiva (desde E3)
python -m blockout --demo   # demostración determinista (desde E9)
```

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
G caras   H ayuda   Esc salir
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
`docs/SEGUIMIENTO.md` · `AI_USAGE.md`
