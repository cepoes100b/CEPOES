# Portada HTML de boletines

Los cinco boletines publicados y las nuevas ediciones usan la misma portada compacta:
título y síntesis, metadatos, descarga PDF, acceso al resumen y sumario cerrado por defecto.
La tapa se presenta como miniatura de 160 px en escritorio; en móvil se prioriza la lectura.
El índice detallado se abre mediante details/summary nativos, sin depender de JavaScript.
Los accesos directos del riel y el contenido íntegro se conservan.

Fuente visual compartida: deploy/site-overlay/assets/publicaciones-html-cepoes.css.
La regla se limita a boletines (.bol:not(.inf)); los informes mantienen su portada.
El publicador aplica compact_newsletter_hero a todas las rutas /publicaciones/boletines/,
incluidas futuras ediciones copiadas de una plantilla anterior. Es idempotente.

Validación reproducible: python -m unittest test_boletines_layout.
Comprueba las cinco ediciones, una futura edición heredada, enlaces, contenido e idempotencia.
Sintaxis Python y controles estructurales aprobados localmente.
Revisión visual de escritorio/móvil pendiente: el entorno no tiene Chromium y su descarga falló.
Fusión y publicación requieren autorización específica según AGENTS.md.
