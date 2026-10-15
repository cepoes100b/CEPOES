# Fechas públicas — auditoría y corrección del 15/10/2026

## Evidencia

- Se descargaron las 152 rutas del sitemap público de cepoes.org; todas devolvieron HTTP 200. La inspección corresponde al HTML y recursos, no a una validación visual en navegador.
- El registro público `https://cepoes.org/assets/data/lo-nuevo.json` contiene 151 entradas: 149 con evento «Actualizado» y fecha 2026-10-14, y dos contenidos nuevos de esa fecha.
- Causa reproducida: `generar_lo_nuevo.py` excluía `/assets/common.js` al identificar datos vinculados, pero no `/assets/common-r1.js`, que es el recurso realmente servido. Ese archivo referencia el índice global de búsqueda. Incorporar una publicación al buscador podía cambiar la huella de todas las páginas, incluidos informes y boletines históricos.
- Las fechas de procesamiento (`generado`) y el texto de las filas de metadatos y controles de compartir también participaban de la huella. Cambios de infraestructura o procesamiento podían parecer cambios editoriales.
- En el HTML de 91 rutas del sitemap hay un indicador `#data-date`. Los scripts lo completan con la generación de su base. La fecha compartida puede ser correcta como procesamiento, pero el rótulo «Última actualización» confunde ese dato con el período estadístico o con una revisión editorial.
- `/presupuesto/` tenía además el 26 de agosto de 2026 escrito como constante en el normalizador, mientras las páginas de ejecución usaban `presupuesto.json.generado`.

## Cambios

1. Exclusión de scripts y controles compartidos en las huellas de contenido; exclusión de `generado` junto con los restantes campos de procesamiento. Los cambios de texto y de valores estadísticos vinculados continúan generando novedades.
2. Lectura de fechas editoriales explícitas en JSON-LD y metadatos `article:published_time` / `article:modified_time`, con validación del formato de estos últimos.
3. Migración acotada del registro v1 cuando hay una concentración documentada de al menos 100 eventos «Actualizado» en un día y ese lote representa al menos el 90% del archivo. Se corrigen sólo las páginas cuyo contenido semántico no cambió entre las dos copias. Un cambio real nuevo conserva su fecha efectiva.
4. Se recupera la fecha editorial explícita, o el mes de edición del registro canónico de informes o de la ruta del boletín. El período mensual se muestra sin inventar un día. Cuando no hay fecha documental, se presenta «Sin fecha editorial verificada», con `date=null`, conservando el evento y fecha anteriores como `legacy_event` y `legacy_detected_at`. El registro usa versión 2; validadores y lector del catálogo editorial aceptan ambos esquemas.
5. Los widgets estadísticos se rotulan «Base procesada». Se conservan el período de cada indicador y las fechas de sus fuentes. El normalizador toma la generación real del presupuesto para su portada.

## Alcance y comprobaciones

- Regeneración sobre copia de la salida pública completa, con las 152 páginas contrastadas y los registros públicos descargados. Se mantienen las 151 entradas, sin duplicados ni eliminación de contenidos. Resultado en esa instantánea: 13 fechas editoriales recuperadas, nueve meses de edición, dos altas nuevas conservadas y 127 fechas de actualización editorial pendientes. Estas últimas incluyen principalmente herramientas y archivos; su fecha de procesamiento estadístico se sigue mostrando en la propia página.
- El informe de coyuntura N.º 2 recupera 2026-10-01; Salud Mental, 2026-10-08. Los cinco boletines conservan sus meses de edición de mayo a septiembre de 2026. Los informes con sólo un período mensual conservan esa precisión.
- Se corrigen 93 widgets de procesamiento en la salida completa de referencia, incluidos dos HTML que no son rutas canónicas del sitemap. No se cambia la fecha de un artículo por ejecutar un despliegue.
- 21 pruebas locales aprobadas: novedades, fechas de procesamiento y compatibilidad del catálogo editorial. Incluyen cambios en el buscador compartido, cambios reales de un indicador, períodos distintos con una misma generación, controles de compartir, preservación de metadatos editoriales, reparación de un lote masivo y un cambio editorial real durante la migración.
- No se modifican el control de aprobación de difusión ni el envío de correos. El catálogo editorial sólo amplía la lectura del registro a la versión 2.
- La revisión visual supervisada sigue pendiente del acceso autorizado a la vista privada; `sites-preview` falla por el montaje de `/proc` en bwrap. Los controles de HTML y código no se presentan como validación visual.

## Siguiente paso

Completar la revisión visual y desplegar la corrección mediante el publicador canónico con autorización de publicación. Las fechas históricas sin evidencia suficiente permanecen explícitamente sin verificar hasta reconstruirlas documentalmente.
