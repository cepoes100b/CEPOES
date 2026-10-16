# Limpieza urbana y reclamos — candidato y actualización oficial

## Estado verificable

Primera versión en revisión, sin publicación. Ruta prevista: `/territorio/limpieza-urbana/`.

Explorador por barrio/comuna, mapa SVG con límites oficiales, evolución mensual, distribución de prestaciones, tablas accesibles y ranking de cuadras. Geometrías derivadas de `badata/barrios.geojson`, conservando las 48 correspondencias y 15 comunas. La muestra geográfica de origen tiene 276.240 registros, 233 menos que el total de la nota; 16 carecen de barrio. Los totales visibles usan los registros realmente disponibles.

El generador de referencia verifica esquema, fechas y sumas antes de escribir. Reproducir:

```
python scripts/generar_limpieza_urbana.py --source /ruta/reclamos-compact.json --geometry badata/barrios.geojson --output deploy/site-overlay/assets/data/limpieza-urbana.json
node --check deploy/site-overlay/assets/limpieza-urbana.js
```

Archivo de referencia: https://especialess3.lanacion.com.ar/interactivos/26/08/mapa-basura-caba/reclamos-compact.json

SHA-256: `787c999cbb38a13eacf05ba959bf88c26e6c17cc26789af680c87ee02c0e9b6b`.

## Cambio solicitado: sección que se autoactualiza

Usar el SUACI oficial para las futuras versiones; el corte periodístico sólo es un insumo de contraste. Catálogo: https://data.buenosaires.gob.ar/dataset/sistema-unico-atencion-ciudadana

Recursos oficiales identificados:

- CSV 2025: `ec9da864-d2e0-480d-8fd3-06807c083ff4`.
- CSV 2026: `3350c0ae-58ff-4252-b496-7cb07bdb88b1`.
- El catálogo declara actualización semestral, aunque el historial registra reemplazos intermedios. Propuesta: comprobar semanalmente, publicar sólo cambios válidos.
- El 16/10/2026 el catálogo y la API CKAN devolvieron HTML de rechazo desde el contenedor. El CDN oficial sí respondió 206 a una solicitud parcial del CSV 2026.
- URL comprobada: https://cdn.buenosaires.gob.ar/datosabiertos/datasets/atencion-ciudadana/sistema-unico-atencion-ciudadana/sistema-unico-de-atencion-ciudadana-2026.csv

La cabecera REAL del CSV 2026 difiere de las descripciones del catálogo:

```
nro_solicitud,periodo,categoria,prestacion,tipo,fecha_ingreso,hora_ingreso,comuna,barrio,calle,altura,esquina_proxima,canal,x,y,genero,estado_general
```

Nunca interpretar `x`/`y` como longitud/latitud: están en coordenadas locales. Para comparar barrios se prioriza la asignación oficial barrio/comuna; cualquier geocodificación posterior requiere transformación y controles explícitos. No replicar automáticamente las correcciones manuales de cuadras hechas por el medio.

## Integración pendiente antes de publicar

1. Separar descargador, normalizador y verificador oficial. Descargar recursos anuales de forma atómica, comprobar respuesta CSV completa (rechazar HTML/206) y registrar SHA-256 y último corte real.
2. Verificar unicidad de `nro_solicitud`, catálogo de prestaciones y fecha; informar faltantes y exclusiones. Definir prestaciones incluidas mediante lista versionada, incluyendo lavado, sin equiparar silenciosamente universos con el derivado periodístico.
3. Conservar series históricas; agregar meses completos nuevos. Identificar por separado el último mes parcial cuando corresponda. No desplazar la ventana de comparación por el reloj si la fuente no se actualizó.
4. Regenerar agregados y metadatos dinámicos del HTML: total, promedio, períodos, procedencia y cobertura. La fecha de comprobación debe diferenciarse del corte estadístico y la actualización real.
5. Validar integridad de 48 barrios/15 comunas, sumas entre vistas, coherencia territorial y no regresión de meses. Si falla descarga/esquema/control, conservar el último producto válido y registrar el error; nunca publicar una salida parcial.
6. Integrar al workflow canónico `territorio.yml` y al manifiesto/cadena de publicación existentes. Revisar sus condiciones de ejecución y registro de productores. No crear un workflow instalador ni un despliegue alternativo. No activar programación hasta probar la cadena completa.
7. Los cambios rutinarios de datos no disparan avisos por correo. Difusión sólo mediante autorización editorial independiente.
8. Revisar candidato completo en escritorio/móvil, claro/oscuro, teclado y estados de error. Quitar `noindex` y la marca de candidato sólo al aprobar la versión pública. Incorporar accesos desde Territorio, buscador y metodología mediante normalizador canónico.

## Limitación de vista previa en esta ejecución

Se intentó primero `sites-preview` con salida estática completa y navegador integrado. El proceso falla antes de estar saludable: `bwrap: Can't mount proc on /newroot/proc: Operation not permitted`. El servidor HTTP alternativo no es accesible desde el navegador integrado (`ERR_CONNECTION_REFUSED`). No se instaló Chromium. Se prepara una vista autónoma de revisión como alternativa, sin modificar producción.

La automatización todavía NO está activada. Este candidato no debe presentarse como un producto oficial ya conectado ni como diseño validado.
