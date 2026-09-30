# Tierras y soberanía

Corte de revisión: 30/09/2026.

## Alcance preparado

Página propuesta /territorio/tierras-y-soberania/ con diez territorios seleccionados del PDF oficial RNTR, búsqueda accesible, cronología y acceso atribuido al mapa del Observatorio de Tierras. No reutiliza código, geometrías ni conflictos del repositorio externo, cuyo árbol revisado no contiene licencia.

Workflow diario 10:30 UTC (07:30 Argentina), sin escritura al repositorio ni despliegue: consulta tres fuentes oficiales, conserva documentos por SHA-256, detecta cambios y errores y entrega resultados para revisión. Un cambio documental puede ser editorial o de formato y requiere revisión. La caché y los artifacts son almacenamiento operativo temporal; conservar documentos aprobados en la custodia durable antes de usarlos como evidencia permanente. La fuente RNTR registra 13.262.725,64 ha y 4,97%, publicación identificada como agosto 2025.

## Validaciones realizadas

Sintaxis JS y Python correctas. Cuatro escenarios de búsqueda: acentos, mayúsculas, resultado vacío y restablecer. Pruebas reproducibles scripts/test_monitor_tierras.py: primera captura, consulta sin cambios, marca de modificación estable y preservación de documento válido ante error.

DOCX de cuatro páginas preparado y revisado visualmente. La prueba visual web Playwright no pudo ejecutarse por ausencia de Chromium instalado; falta probar integración real con common.js/site.css, móvil, teclado y ambos temas.

## Pendientes que bloquean publicación

- Recuperar y leer el fallo completo CSJN FLP 47574/2023/CS1 y FLP 47574/2023/1/RH1; actualmente la descripción se atribuye expresamente a una reseña.
- Corroborar novedades parlamentarias con documentos oficiales.
- Ejecutar workflow de detección para verificar conectividad real a las fuentes.
- Revisar navegación, catálogo, índice de búsqueda y semáforo antes de integrar la ruta al sitio.
- Completar base de departamentos, cruce territorial y conteo exacto >15% sin redondear.
- Para un mapa propio: obtener geometrías oficiales y aclarar derechos de cada capa. Malargüe 14,74% y Chilecito 14,86% no superan 15% en el PDF.
- Generar PDF con plantilla editorial CEPOES y miniatura si se decide publicar como informe descargable. El DOCX de trabajo no sustituye ese requisito.

## Fuentes

https://www.argentina.gob.ar/justicia/tierrasrurales/datos/extranjerizacion-departamento
https://www.argentina.gob.ar/sites/default/files/2021/02/extranjerizacion_por_departamento_pdf.pdf
https://www.argentina.gob.ar/normativa/nacional/192150/texto
https://www.argentina.gob.ar/normativa/nacional/decreto-70-2023-395521/texto
https://www.palabrasdelderecho.com.ar/articulo/7025/La-Corte-Suprema-revoco-el-fallo-que-habia-declarado-inconstitucional-el-DNU-que-derogo-la-Ley-de-Tierras
https://thomasartopoulos.github.io/mapa_extranjerizacion/

Próximo paso: obtener el texto judicial completo y validar su alcance antes de marcar el PR listo.
