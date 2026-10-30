# Verificación del prototipo (E8, Hito 3)

Lista de verificación de los requisitos obligatorios R01–R21 de la guía (derivados del enunciado §3).
Para cada uno hay una **prueba automática** que corre en el CI (Linux y Windows, Python 3.10 y 3.12) y una
**comprobación manual** que se hace con la aplicación abierta durante la sesión conjunta de E8.

`tests/test_trazabilidad.py` comprueba que cada prueba citada aquí existe y que están los 21 requisitos.

**Cómo llenarlo.** En la sesión, cada integrante corre `python -m blockout` en su máquina y hace las
comprobaciones manuales. En la columna de su sistema escribe sus iniciales y `✔`, o `✘` con una nota debajo
de la tabla. Debe quedar al menos una corrida en **Linux**: el enunciado (§10) exige mostrar la ejecución en
Linux en el video.

Iniciales: **EP** Emmanuel · **JA** Juan Sebastián · **HQ** Harrinson.

| ID | Requisito | Prueba automática | Comprobación manual en la aplicación | Linux | Windows |
| --- | --- | --- | --- | --- | --- |
| R01 | Contenedor 3D con cuadrícula visible | `tests/test_escena.py::test_contenedor_tiene_las_aristas_esperadas` | Al abrir se ve el pozo 5×5×10 con rejilla en el piso y en dos paredes | | |
| R02 | ≥ 5 piezas distintas de cubos unitarios | `tests/test_escena_tr.py::test_las_piezas_son_distintas_aunque_se_roten` | Con `Tab` se recorren 6 piezas de formas distintas | | |
| R03 | ≥ 2 piezas no planarias | `tests/test_escena_tr.py::test_hay_al_menos_cinco_piezas_y_dos_no_planarias` | Trípode y Tornillo ocupan más de un nivel de altura | | |
| R04 | Seleccionar y trasladar una pieza | `tests/test_escena_tr.py::test_translate_mueve_un_numero_entero_de_cubos` | `Tab`/`1`–`6` cambian la pieza activa (más gruesa); `A D S W F R` la mueven un cubo | | |
| R05 | Rotar alrededor de los tres ejes | `tests/test_escena_tr.py::test_rotar_37_veces_sigue_siendo_rigida_y_exacta` | `I K`, `J L`, `U O` giran 90° en X, Y y Z del mundo | | |
| R06 | Pivotes y rigidez | `tests/test_escena_tr.py::test_el_pivote_queda_quieto_al_rotar` | Tras muchos giros la pieza no se deforma ni se sale de la rejilla | | |
| R07 | Cámara que orbita | `tests/test_camera.py::test_orbitar_360_grados_vuelve_al_mismo_ojo` | Arrastrar con el ratón y las flechas giran alrededor del pozo; las piezas no se mueven | | |
| R08 | Cambiar la distancia | `tests/test_camera.py::test_zoom_cambia_la_distancia_y_no_el_objetivo` | La rueda y `RePág`/`AvPág` acercan y alejan; `dist` cambia en el HUD | | |
| R09 | Ajustar el campo de visión | `tests/test_camera.py::test_cambiar_el_fov_cambia_K_y_no_la_posicion` | `Z`/`X` cambian `fov` en el HUD; la imagen se agranda sin cambiar la perspectiva | | |
| R10 | Restablecer la vista | `tests/test_camera.py::test_reset_restaura_todo` | Tras mover la cámara, `C` vuelve exactamente a la vista de arranque | | |
| R11 | La cámara no altera el mundo | `tests/test_interfaz.py::test_mover_la_camara_no_cambia_la_escena` | Mover la cámara y volver con `C`: las piezas siguen donde estaban | | |
| R12 | Escena en 3D; la pantalla se calcula de ella | `tests/test_app.py::test_el_renderizador_no_importa_la_escena_ni_la_proyeccion` | Revisión de código: `renderer.py` solo recibe `DrawPrimitives2D` | | |
| R13 | Cadena `λx = K[R\|t]MX` con `P` 3×4 | `tests/test_integracion_e3.py::test_cada_arista_de_la_pieza_cae_donde_dice_la_formula` | Cada integrante sigue un punto de su pieza de local a pantalla con `docs/INTERFACES.md` §7 | | |
| R14 | Sistemas, dimensiones, orden y ejes documentados | `tests/test_contrato_codigo.py::test_cada_funcion_del_contrato_existe_con_esa_firma` | Un integrante reproduce un punto del ejemplo compartido solo con el documento | | |
| R15 | Puntos cerca o detrás de la cámara sin fallos | `tests/test_clipping.py::test_mil_camaras_al_azar_sin_nan_ni_excepciones` | Acercar la cámara al máximo y orbitar dentro del pozo: nada se rompe ni aparecen líneas absurdas | | |
| R16 | Visibilidad coherente con caras rellenas | `tests/test_interfaz.py::test_arista_lejana_queda_tapada_por_una_cara_cercana` | Con `G`, desde varios ángulos, las caras de adelante tapan a las de atrás y a la rejilla | | |
| R17 | Sin cámara de un motor gráfico | `tests/test_proyeccion.py::test_P_es_la_misma_cadena_que_K_R_t` | Revisión de `requirements.txt`: solo `numpy` y `pygame-ce` | | |
| R18 | Derivar la homografía entre dos vistas | `tests/test_homography.py::test_dos_derivaciones_dan_la_misma_H21` | `docs/INFORME.md` §2.2 explica la derivación | | |
| R19 | Verificar con ≥ 4 puntos y reportar errores en píxeles | `tests/test_homography.py::test_H21_lleva_el_piso_de_una_vista_a_la_otra` | `python experiments/homography_experiment.py` imprime las tablas de `docs/INFORME.md` §2.4 | | |
| R20 | Mostrar que falla fuera del plano | `tests/test_homography.py::test_la_misma_H_falla_fuera_del_plano_y_el_error_crece_con_la_altura` | `results/homografia.png` y la tabla de errores contra `Z` | | |
| R21 | HUD con controles, pieza activa y estado | `tests/test_interfaz.py::test_el_hud_muestra_pieza_estado_y_camara` | La columna izquierda muestra pieza, estado, cámara y teclas; `H` la oculta | | |

## Notas de la sesión

_Fecha real de la sesión, quién la moderó, en qué sistemas se corrió y cualquier ✘ con su causa y el PR que
lo arregla._

## Desajustes encontrados antes de la sesión

Se revisó el prototipo (E4–E7) contra `docs/INTERFACES.md` y se corrigió en el PR de E8:

| Desajuste | Corrección |
| --- | --- |
| `create_scene` lanza `ValueError` con una pieza desconocida o si no caben, y el contrato no lo decía | §3.1 lo documenta |
| `clip_polygon_near` es pública y la usa §6, pero no estaba en §3.2 | Fila nueva en §3.2 |
| La fila de `project` no decía qué hace `fill_faces=True` | Descarte de caras traseras, recorte y pintor, en §3.2 |
| Las funciones de homografía no estaban en el contrato | Tabla nueva en §3.2 |
| `OrbitCamera` ignora entradas no finitas y `zoom` ≤ 0, sin documentar | §3.2 lo documenta |
| `VictoryAnimation` y `DemoRunner` figuraban como si existieran | Marcadas como pendientes de E9 |
| §3.3 dice que `run` y `render_frame` están en `blockout.app`, pero `app/__init__.py` no las exportaba | `app/__init__.py` las exporta |
| El experimento de E7 fallaba con `UnicodeEncodeError` en la consola de Windows (cp1252) | Corregido en el PR de E7, con una prueba |

`tests/test_contrato_codigo.py` lee las tablas de §3 y comprueba que cada función existe en el módulo que dice
el documento, con los mismos parámetros. Si el código y el contrato vuelven a separarse, el CI falla.
