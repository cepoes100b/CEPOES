# Tierras y soberanía · corte de revisión 30/09/2026

PR: https://github.com/cepoes100b/CEPOES/pull/153
Ruta preparada: `/territorio/tierras-y-soberania/`.

## Entrega

Dossier HTML, mapa departamental, tabla y selector equivalentes, ficha, JSON registral, informe completo PDF con plantilla CEPOES y miniatura derivada de la misma portada. El documento editable conserva el análisis y la propuesta de monitoreo. Serie territorial propuesta: T.01.

Fuente judicial: sentencia completa FLP 47574/2023/CS1 y FLP 47574/2023/1/RH1, 29/09/2026, copia íntegra publicada por Palabras del Derecho: https://drive.google.com/file/d/12oNyyylTZtdlO0ghWYXxfyfefh1jfCRl/view. Considerandos 5 y 7: legitimación y caso colectivo; considerando 9: no decide constitucionalidad del artículo 154 ni interfiere con el Congreso. No se obtuvo un enlace canónico en el servidor de CSJN.

Normativa oficial: DNU 70/2023 artículo 154; Ley 26.737, texto original, artículos 8-10, 14 y 17; Ley 26.122 artículos 22-25. El anuncio periodístico de pedido de sesión especial sigue pendiente de registro y convocatoria parlamentaria; no se presenta como sesión convocada ni votación.

## Fuente registral y cartográfica

- RNTR: https://www.argentina.gob.ar/justicia/tierrasrurales/datos/extranjerizacion-departamento. La página marca agosto de 2025 como última actualización, sin atribuirle un día de corte no informado.
- PDF: https://www.argentina.gob.ar/sites/default/files/2021/02/extranjerizacion_por_departamento_pdf.pdf. SHA256: `b724f5b51c2d77e687b1e56e9e17b087ee639c4f1d849b8ebd621829bff26e2e`.
- Georef: https://apis.datos.gob.ar/georef/api/departamentos.ndjson; versión 13.0.0, 09/04/2026, fuente IGN, 529 unidades. Simplificación Shapely con tolerancia 0.012 grados y preservación de topología; vista continental, Tierra del Fuego y Malvinas. Otras islas y Antártida quedan fuera de encuadre.
- 513 filas originales, 512 identificadores territoriales distintos. El PDF repite Ituzaingó, Corrientes: 33,90% y otra fila con rural=0. Se preservan ambas filas, se etiqueta la duplicada y se representa en mapa la fila con superficie.
- 31 registros con porcentaje publicado estrictamente >15. Malargüe 14,74% y Chilecito 14,86% quedan debajo del umbral. Los nulos se conservan; las cifras no se redistribuyen.
- Total nacional extranjero: 13.262.725,64 ha (4,97%). Suma provincial: 13.262.725,65 ha; suma departamental informada: 13.262.719,20 ha. Diferencia Córdoba frente a sus departamentos: 6,55 ha.
- El porcentaje y el antiguo umbral sirven para describir concentración. La calificación de operaciones exige revisar fechas, derechos adquiridos y normas aplicables.

El repositorio de Thomás Artopoulos se inspeccionó por el conector GitHub oficial y se enlaza con atribución. No se encontró licencia. No se reutilizan sus geometrías ni su base de conflictos. Su workflow actualiza conflictos, no las cifras RNTR.

## Regeneración

Descargar las fuentes oficiales a un directorio temporal. `pdftotext -layout rntr.pdf rntr.txt`. Dependencias: Python 3.12, Shapely, ReportLab y Poppler. El generador PDF importa la plantilla institucional existente; no la modifica.

```sh
python scripts/normalizar_tierras.py --texto rntr.txt --pdf rntr.pdf --georef departamentos.ndjson --salida deploy/site-overlay/territorio/tierras-y-soberania/rntr.json
python scripts/generar_mapa_tierras.py --datos deploy/site-overlay/territorio/tierras-y-soberania/rntr.json --georef departamentos.ndjson --salida mapa.svg
python scripts/generar_web_tierras.py --datos deploy/site-overlay/territorio/tierras-y-soberania/rntr.json --mapa mapa.svg --plantilla templates/tierras-soberania.html --salida deploy/site-overlay/territorio/tierras-y-soberania/index.html
python scripts/generar_pdf_tierras.py
python scripts/verificar_tierras.py
python scripts/test_monitor_tierras.py
```

La cobertura y el conteo del corte están validados explícitamente; un corte nuevo exige revisar narrativa, anomalías y verificadores antes de generar una publicación.

## Monitor

Tres fuentes oficiales: PDF RNTR, catálogo RNTR y texto DNU. Descarga con límites y control de formato, huella SHA256, versión documental, fechas de consulta y cambio separadas. Un error preserva el documento anterior. Cambio documental requiere revisión; no se infiere un cambio legal desde una huella distinta.

Consulta local real del 30/09/2026 18:06 UTC: tres primeras capturas correctas. Pruebas: primera captura, consulta sin cambios y preservación tras error correctas. Programación propuesta diaria 10:30 UTC (07:30 Argentina), permisos de contenido sólo lectura. GitHub Actions aún no ejecutado para este dossier. Cache/artifacts no constituyen archivo histórico permanente; retención de artifacts 30 días. Congreso y nuevos fallos requieren revisión editorial y fuentes primarias adicionales. Capas de recursos y conflictos quedan para una etapa posterior documentada.

## Validaciones y publicación

513 filas / 512 IDs, 31 >15%, nulos y sumas, concordancia de porcentajes con hectáreas y colores: correctos. Navegador: búsqueda sin acentos, resultado vacío, restablecimiento, filtro >15, selección, escritorio 1440 px y móvil 390 px, temas claro/oscuro sin desbordamiento. Leyenda revisada tras corregir estilo global. PDF cinco páginas e interiores revisados; documento editable cuatro páginas.

No modifica portada, buscador, suscripción, autenticación ni zona privada. La ruta sólo se incorpora a producción después de aprobación del PR. No se ejecutaron workflows de publicación. Pendiente final: autorización explícita para fusionar/desplegar según AGENTS.md.
# Revisión editorial y de integración del 30 de septiembre de 2026

- La página omitía la carga de Poppins e Inter: el encabezado canónico usaba fuentes de reemplazo. La plantilla ahora carga la misma familia y pesos del sitio; el contenido hereda Inter y los títulos conservan Poppins.
- Los selectores de layout se restringen al módulo `.tierras` para preservar navegación, logo y componentes comunes.
- La navegación común dispone de un ancho máximo de 1600 px; adelanta la marca apilada a 1450 px y la separación compacta a 1600 px. Con fuentes reales, el encabezado anterior excedía el viewport a 1440 px. Se conserva tamaño y peso del logo y se evita comprimirlo.
- Se agrega Tierras y soberanía al menú territorial de escritorio y móvil. El normalizador inserta un acceso visible y persistente, sin depender de JavaScript, en Territorio y Publicaciones. Su ejecución repetida no duplica bloques.
- El informe y la síntesis se reorientan a extranjerización, concentración, recuperación de la Ley de Tierras y soberanía. La crítica al efecto político del fallo se expresa como posición editorial, diferenciada de su alcance procesal.
- Se retiran utilidad para CEPOES, implementación del monitor, condiciones de publicación y notas de trabajo de la pieza pública. DOCX y PDF provienen del mismo contenido revisado; PDF y miniatura conservan la plantilla institucional.
- Se preservan datos RNTR, geometrías, controles y monitor. La fecha registral sigue siendo agosto de 2025; no se incorporan nuevos propietarios o eventos sin documentos.
