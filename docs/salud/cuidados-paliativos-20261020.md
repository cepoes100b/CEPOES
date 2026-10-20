# Eje Salud y cuidados paliativos

Pedido de Agustín del 20/10/2026: sección dentro de Salud, acceso desde el menú principal al nivel de Educación y conservación fiel de todo el documento `Cuidados paliativos en la Ciudad de Buenos Aires.docx`.

## Implementación

- `/salud/`: portada editorial con especial destacado y ocho accesos a contenidos existentes.
- `/salud/cuidados-paliativos/`: título, 61 párrafos y cuatro tablas del documento conservados íntegramente, en su orden original. Se preservan los 25 enlaces de los párrafos y las fuentes.
- Ocho secciones y un índice lateral, que se convierte en índice de dos columnas en móvil; tablas desplazables accesibles por teclado; temas claro y oscuro.
- Recursos añadidos: línea de tiempo normativa; dos barras de la muestra hospitalaria de 2016 con denominadores separados; inventario nacional de servicios por tipo; oferta documentada de 2023; cuatro condiciones del acceso; comparación del modelo económico de Río Negro, identificada como modelización.
- Salud en menú y pie compartidos, activa en sus rutas. Menú plegable hasta 1600 px para evitar superposición. Integración en registro de informes, buscador y ambos sitemaps. El hub de Salud del Observatorio conduce al nuevo eje.
- Los datos y enlaces del documento se conservan en `datos/salud/cuidados-paliativos-texto.json`. Regeneración: `python scripts/generar_cuidados_paliativos.py`. La salida HTML versionada es la entrada del publicador canónico.

## Verificación y límites

- Comparación local contra el DOCX adjunto: 61 párrafos y todas las celdas de los cuatro cuadros presentes literalmente, sin faltantes. Orden y enlaces preservados.
- 31 pruebas existentes de catálogo, fechas públicas y tipografía, más novedades, aprobadas. Sintaxis de los tres scripts y verificador de contraste compartido aprobados; este último no reemplaza una revisión visual del nuevo módulo.
- Verificación de Salud activa en ambas rutas, un enlace principal, anclas internas y recursos locales de las dos páginas aprobada.
- `sites-preview start` inició correctamente el servidor supervisado. El navegador integrado primero recibió conexión rechazada y luego rechazó observar la pestaña de error por política de URL; la revisión automática también rechazó un nuevo intento. No se declara QA visual ni móvil aprobada. Se ofrece copia privada accesible al usuario, sin medición y con noindex.
- Se mantienen las preguntas abiertas y expresiones de trabajo pendiente del documento (adhesión normativa y revisión presupuestaria). No se agregan verificaciones externas ni se presentan como resueltas. Las cifras, afirmaciones y fuentes corresponden al original aportado.
- No se ofrece un DOCX descargable ni se genera un PDF no solicitado. El informe web completo ingresa al catálogo con formato web.
- Sin autorización de envío de correo ni marca de difusión. La publicación en cepoes.org queda pendiente de revisión y aprobación de esta versión.

## Vista privada

https://cepoes-salud-cuidados-paliativos.crivelli725370.chatgpt.site

Proyecto `appgprj_6ad7e1693c088191be5751fea396f738`; versión `appgprj_6ad7e1693c088191be5751fea396f738~appgver_17fb4a6465c88191bdbae73070a21cd1`; despliegue privado succeeded. Fuente `966da7635c1451e8aa7c0e00f9503c61ffd44b23`. El despliegue privado no equivale a publicación en cepoes.org ni a revisión visual aprobada.

## Ajuste de portada solicitado

Todos los temas del eje Salud pasan a una única grilla de nueve tarjetas con el mismo diseño. Se retira el bloque destacado de cuidados paliativos. El normalizador canónico asigna una única etiqueta «Nuevo» a la tarjeta con la fecha de publicación más reciente, usando el catálogo y los metadatos de publicación de las páginas. Las actualizaciones no cambian por sí mismas la novedad. Prueba de etiqueta única, idempotencia y traslado a otra tarjeta ante una nueva publicación aprobada.

La misma regla se aplica a Educación por pedido expreso: cinco tarjetas equivalentes, sin bloque destacado universitario. Clase compartida `axis-new` y función `mark_latest_axis`. La fecha de publicación se lee independientemente del orden de los atributos HTML.
