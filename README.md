# Blockout desde una cámara móvil

Proyecto de Visión por Computador (Ingeniería Electrónica, UTP, 2026-II). Visualización 3D interactiva
inspirada en Blockout: la escena vive en coordenadas 3D del mundo y se proyecta a la pantalla con una
matriz de cámara implementada por el equipo (λ·[u v 1]ᵀ = K [R|t] M [X Y Z 1]ᵀ).

**Estado:** E2 — contrato entre módulos acordado (`docs/INTERFACES.md`). Ver `docs/SEGUIMIENTO.md`.

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

_Se completan en la etapa E6._

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
