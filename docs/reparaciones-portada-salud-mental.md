# Identidad de portada y barras federales — 11/10/2026

Base contrastada con GitHub oficial, cuenta CEPOES: `0202625bc79988461f2fcaf40ed132a9e9adbebd`.
El generador de compartir vigente es el integrado por #216. No había otro PR abierto de compartir al comenzar esta reparación.

## Cambio acotado

- Sólo la ruta raíz usa el `<title>` institucional íntegro para títulos sociales, mensajes y placas. El `h1` del destacado permanece intacto. Artículos e informes conservan su criterio anterior y el registro sigue siendo la fuente de títulos de informes.
- `.sm-jur-fill` incorpora `display:block`. El enlace CSS pasa de `v=2` a `v=3` en el monitor y en la nota que comparte ese recurso. Normalizador y validador de publicación quedan alineados.
- No se modifican datos, tasas, orden, metodología, registros editoriales, newsletter ni suscriptores.

## Pruebas reproducibles

```sh
python -m unittest test_compartir_publicaciones.py test_salud_mental_presentacion.py
python validar_pr_r2.py
python -m unittest test_cadena_publicacion.py test_catalogo_informes.py test_lo_nuevo.py test_home_editorial.py test_salud_mental_tls.py
node --test tests/compartir_publicaciones.test.mjs tests/public_corrections.test.mjs
python verificar_salud_mental.py
python validar_contraste_visual.py
python tests/qa_salud_mental.py /ruta/al/candidato /ruta/a/evidencia
```

La QA usa Chromium 151 real, HTML/JS/datos del monitor, normalizador y generador de compartir. El CSS global fue recuperado de Library: 134337 bytes, SHA-256 `14ad805eb2a76f7480bf3d117f903ad581d51b58009babb88a113df71b327133`.

Se aprobaron 320/390/1440 px × claro/oscuro, con 24 barras por variante. Se comprueban nombres, tasas, orden, porcentaje, altura de 12 px y proporción del ancho con tolerancia subpíxel. El mínimo observado fue 22,59375 px a 320 px. La restauración temporal del CSS inline original produce ancho cero en las 24 barras: la regresión detecta el fallo original. No hubo desborde horizontal ni errores JavaScript. Las capturas se inspeccionaron en ambos temas. Fuentes externas bloqueadas en el harness: se usaron fuentes de respaldo locales.

La preparación de compartir se ejecutó sobre las 64 páginas elegibles del overlay. La segunda pasada produjo cero cambios y todos los hashes de HTML/PNG se conservaron. Comparación adicional contra el generador de `main`: las salidas HTML de los 12 informes disponibles en el overlay son byte-idénticas. Las pruebas de portada verifican título institucional, WhatsApp/X, metadatos, argumentos de las tres placas, imágenes reales e idempotencia incluso al cambiar el destacado.

## Límite de publicación

El acceso HTTPS a la raíz pública desde este entorno devuelve `Tunnel connection failed: 403 Forbidden`. No se intentó eludirlo. La portada base no está versionada en el overlay; por eso la prueba de portada usa un fixture explícito y no acredita la reconstrucción completa del sitio publicado.

La autorización del usuario comprende fusión y despliegue, pero exige antes cadena completa y preview comprobable. Faltan el snapshot público completo, la revisión de la portada real y la comprobación final de producción mediante el navegador público permitido. El PR debe permanecer en borrador mientras esa evidencia falte. La preparación local de 64 páginas no se presenta como un build completo ni como un despliegue.
