# Tipografía de la navegación y los informes

El 08/10/2026 se corrigió la ausencia de las fuentes institucionales en el informe de salud mental, el monitor Seguridad y derechos y la nota asociada a Tormenta Negra. El CSS general declaraba Inter y Poppins, pero estas páginas no cargaban sus archivos; logo, menú y títulos usaban fuentes de reemplazo.

`ensure_site_fonts` en el normalizador público agrega la carga canónica de Google Fonts a las páginas que usan `site.css` cuando falta alguna de esas familias. Conserva las páginas que ya cargan ambas fuentes y es idempotente. Los documentos autónomos con otro sistema de estilos quedan fuera de esta transformación.

El cuerpo del informe de salud mental hereda Inter; se retiró la declaración Arial de su CSS. No se modifica el contenido editorial.

Validación: 26 pruebas de fuentes, portada de boletines, home, catálogo y novedades aprobadas. Vista previa completa con sites-preview y cua_repl: logo/menú Poppins y cuerpo Inter; salud mental y Seguridad y derechos revisados en escritorio y a 390 px, claro/oscuro, sin desbordamiento horizontal. La nota asociada está cubierta por la prueba de carga y conservación del contenido.
