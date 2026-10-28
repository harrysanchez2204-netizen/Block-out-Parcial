# Roles y reglas de trabajo

## Roles (enunciado §4)

| Rol | Responsable | Usuario Git | Carpeta | Salidas |
| --- | --- | --- | --- | --- |
| A · Escena y geometría | Emmanuel Parra Ocampo | @ZXemmp | `src/blockout/scene/` | Geometría 3D válida y poses en el sistema acordado |
| B · Cámara y proyección | Juan Sebastian Atis Chaves | @juanatis | `src/blockout/projection/`, `experiments/` | Geometría 2D proyectada y verificación numérica |
| C · Interfaz y animación | Harrinson Quitumbo Sanchez | @harrysanchez2204-netizen | `src/blockout/app/` | Aplicación interactiva que usa los módulos compartidos |

**Coordinador de seguimiento:** _completar_ (además de su rol técnico). Mantiene el plan, el cronograma y el
tablero; actualiza `docs/SEGUIMIENTO.md` al menos una vez por semana.

Los roles son responsabilidades, no exclusividad del conocimiento: los tres deben entender la cadena completa.

## Rotación de revisión (enunciado §6)

| Autor del PR | Revisor obligatorio |
| --- | --- |
| A | C |
| B | A |
| C | B |

(A revisa a B, B revisa a C, C revisa a A.) Un PR que toque `src/blockout/core/` o `docs/INTERFACES.md` lo
aprueban los tres.

## Flujo de Git

- `main` siempre ejecutable. Nadie hace `push` directo a `main`.
- Una rama por funcionalidad: `feat/<modulo>-<tema>` (ej. `feat/scene-rotaciones`), `docs/...`, `fix/...`.
- Commits pequeños, en español o inglés, con verbo en imperativo: `Agrega rot_axis_exact con pruebas`.
- Cada integrante usa **su propia cuenta** y `git config user.name` / `user.email` correctos.
- PR con la plantilla: descripción, tarea enlazada, evidencia de funcionamiento y revisor.
- Mínimo 1 aprobación de un compañero distinto del autor; se resuelven todos los comentarios antes de fusionar.
- CI en verde (Linux y Windows) para fusionar.
- Para fusionar, usar *merge commit* o *rebase*; evitar *squash* si borra la autoría de commits individuales.
- Etiquetas de hito: `v0.1-diseno`, `v0.2-integracion`, `v0.3-prototipo`, `v1.0`.

## Configuración del repositorio (lista de verificación de E1)

- [ ] Docente y compañeros con acceso al repositorio
- [ ] Protección de la rama `main`: exigir PR, 1 aprobación, estado `ci` en verde, resolver conversaciones
- [ ] Tablero con columnas: Pendiente · En curso · En revisión · Terminada
- [ ] Cada integrante clonó, creó una rama y abrió un PR de prueba (C: PR #1 ✔)
