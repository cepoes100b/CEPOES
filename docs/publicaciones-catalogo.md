# Informes y boletines: integración obligatoria

Desde el 01/10/2026, `deploy/reports-registry.json` es la fuente única de las tarjetas de informes. Conserva títulos, bajadas y portadas aprobadas. Incluye los informes alojados junto a herramientas territoriales, como Tierras y soberanía.

Al publicar un informe:

1. Incorporar su página, PDF completo y miniatura de portada al sitio.
2. Registrar URL, título, subtítulo opcional, descripción, tipo, período, portada y PDF en el catálogo. Usar `AAAA-MM-DD` si el día está comprobado o `AAAA-MM` si sólo consta el mes; conservar el orden editorial dentro del mismo período.
3. Ejecutar `python generar_catalogo_informes.py RUTA_DEL_SITIO` sobre el build completo. Genera todo el archivo de Informes y los cinco informes más recientes en Publicaciones con las plantillas existentes.

El publicador canónico ejecuta el generador antes de Lo nuevo y bloquea la publicación si detecta un informe fuera del catálogo, rutas duplicadas, una página privada o la falta de página, PDF o portada. Detecta páginas bajo `/publicaciones/informes/`, la plantilla `web-report` y monitores que ofrecen «Descargar informe completo» con un PDF propio. Para informes en otros formatos o rutas se debe registrar la ficha igualmente. Los archivos HTML de tarjetas son salidas; no editarlos como una segunda fuente.

Cada edición pública bajo `/publicaciones/boletines/` ingresa automáticamente en Lo nuevo. El índice de la serie no se clasifica como una edición. El tipo y filtro son «Boletín». Se conserva todo el historial, sin descartar publicaciones al superar 80 novedades. Los cambios de navegación o estilos mantienen la fecha. Las ediciones heredadas sin fecha comprobable se incorporan con la etiqueta «Incorporado al archivo», sin atribuirles una fecha de publicación inventada. Los borradores y las páginas `noindex` quedan fuera.

Verificaciones reproducibles:

```sh
python -m unittest test_catalogo_informes.py test_lo_nuevo.py
python generar_catalogo_informes.py deploy/site-overlay --check-source
python generar_catalogo_informes.py RUTA_DEL_SITIO
python generar_lo_nuevo.py RUTA_DEL_SITIO --previous RUTA_DE_PRODUCCION_ANTERIOR
```

`--check-source` comprueba la cobertura editorial del overlay; los PDF y las portadas heredados de producción se verifican en el build completo. El workflow R2 ejecuta las pruebas y el control del overlay en cada PR. El workflow canónico de Hostinger genera y valida los dos catálogos antes de publicar.
