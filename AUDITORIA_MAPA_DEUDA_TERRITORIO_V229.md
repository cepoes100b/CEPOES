# CEPOES v2.29 — Auditoría territorial de Mapa de la Deuda

Fecha de auditoría: 22/08/2026.

## Objetivo

Reconstruir, antes de definir la territorialización propia de CEPOES, la metodología utilizada por Mapa de la Deuda para transformar el código postal asociado a cada persona deudora en una unidad geográfica y, en CABA, en uno de los 48 barrios.

La auditoría se limita a recursos públicos y no intenta acceder a microdatos ni a infraestructura privada.

## Resultado principal

La infraestructura pública confirma con claridad la **salida geográfica** del procedimiento, pero no expone el **crosswalk de entrada** que transforma código postal en barrio.

Por lo tanto, a esta altura se puede afirmar:

1. Mapa de la Deuda declara que geolocaliza los registros a partir del código postal asociado a la identificación de cada deudor y utiliza cartografía del Instituto Geográfico Nacional (IGN) para la referencia territorial.
2. El frontend consume resultados que ya llegan agregados por territorio.
3. Para CABA existe un nivel explícito `barrio_caba`, scope `02`, con 48 geografías.
4. Las geometrías se publican ya normalizadas en un archivo PMTiles y cada barrio tiene identificador, nombre, bbox y referencia de fuente.
5. Los recursos públicos inspeccionados no contienen una tabla `codigo_postal -> barrio`, coordenadas asociadas a cada código postal ni una función de geocodificación que ejecute ese cruce en el navegador.
6. En consecuencia, el paso código postal -> ubicación -> unidad territorial fue realizado **aguas arriba**, en el pipeline del analista, antes de generar los slices públicos que consume el sitio.

## Evidencia técnica pública

### Manifest

`https://datos.mapadeladeuda.ar/manifest.json`

El manifest declara:

- contrato `mobile-slices-v2`;
- niveles `provincia`, `departamento`, `municipio` y `barrio_caba`;
- nivel local de CABA basado en barrios;
- 48 geografías para `barrio_caba`, scope `02`;
- geometría administrativa normalizada;
- fuente geográfica declarada: IGN;
- geometría servida mediante PMTiles.

La descripción del dataset indica que las métricas agregadas y la geometría IGN normalizada fueron entregadas al frontend ya preparadas.

### Lookup geográfico

`https://datos.mapadeladeuda.ar/geo/lookup.json`

El archivo contiene las unidades territoriales ya normalizadas. Para los barrios de CABA registra, entre otros:

- `geo_id`;
- `nombre`;
- `level = barrio_caba`;
- `scope = 02`;
- `parent_id = 02`;
- `bbox`;
- `source = IGN`;
- `source_layer = barrios_caba`;
- `source_id`.

Ejemplos observados: Agronomía, Almagro, Balvanera, Barracas, Belgrano y Boca.

No se observan allí códigos postales ni una correspondencia postal-territorial.

### Geometría

`https://datos.mapadeladeuda.ar/tiles/geo_admin_argentina.pmtiles`

La geometría vectorial expone campos tales como `geo_id`, `nombre`, `level`, `scope`, `parent_id`, `source`, `source_layer` y `source_id`. La fuente declarada es IGN.

### Frontend y tráfico de red

El frontend carga, entre otros:

- `manifest.json`;
- `dimensions/filters.json`;
- `dimensions/metrics.json`;
- `geo/lookup.json`;
- `periods/2026-06/index.json`;
- `periods/2026-06/slices/provincia/AR/default.json`;
- `periods/2026-06/slices/barrio_caba/02/default.json`;
- `tiles/geo_admin_argentina.pmtiles`;
- mapa base Argenmap del IGN.

No se observó una solicitud de red a un servicio de geocodificación ni a una tabla pública de códigos postales durante la ejecución normal del sitio. El navegador sólo representa datos territoriales previamente procesados.

## Lo que todavía NO está demostrado

La auditoría pública no permite afirmar todavía:

- qué base se utilizó para convertir cada código postal en coordenadas;
- si se utilizó un centroide, punto representativo, localidad o polígono postal;
- cómo se resolvieron códigos postales que intersectan más de una unidad territorial;
- si existió una tabla manual o propia del analista;
- si la asignación se hizo mediante un servicio de geocodificación o mediante una base local;
- cuál fue la versión exacta del insumo postal utilizado.

No corresponde completar esas lagunas por inferencia y presentarlas como metodología del productor.

## Segunda fase de reconstrucción

La estrategia CEPOES queda ordenada así:

### A. Buscar la implementación o documentación upstream

1. revisar materiales públicos del CEC/FES y presentación metodológica;
2. buscar repositorios, notebooks, scripts o archivos asociados a los autores/equipo;
3. buscar referencias específicas al insumo utilizado para georreferenciar códigos postales;
4. documentar cualquier regla encontrada y su fecha/versión.

### B. Reconstrucción empírica si el crosswalk no está publicado

Si no aparece la tabla original, CEPOES puede reconstruir la asignación de manera auditable:

1. generar con BCRA/ARCA agregados por código postal para CABA;
2. descargar los 48 agregados públicos de Mapa de la Deuda para el mismo período y universo de filtros;
3. reconciliar primero el universo de acreedores para reducir diferencias no territoriales;
4. construir candidatos `CP -> barrio` utilizando un insumo postal georreferenciado reproducible;
5. superponer los puntos/áreas postales con las mismas geometrías administrativas declaradas por Mapa de la Deuda/IGN;
6. comparar el agregado resultante barrio por barrio contra los 48 valores publicados;
7. medir error de deudores, mora y montos por barrio;
8. modificar reglas de resolución de ambigüedades sólo si existe justificación geográfica, no para forzar coincidencia estadística;
9. documentar tasa de asignación, códigos ambiguos y no asignados.

## Criterio de aceptación

Se considerará reconstruida la metodología territorial cuando exista una regla reproducible que:

- parta del mismo campo postal disponible en el padrón;
- use un insumo geográfico identificable y versionable;
- emplee las unidades territoriales del IGN o una normalización equivalente verificable;
- asigne los registros sin usar resultados de deuda como criterio de asignación;
- produzca resultados barriales consistentes al contrastarlos con los 48 agregados públicos;
- informe explícitamente cobertura, ambigüedad y no asignación.

La comparación con Mapa de la Deuda es un **test de validación**, no una fuente para decidir artificialmente dónde ubicar personas individuales.

## Decisión

Se reemplaza la idea anterior de descartar la territorialización por el solo hecho de que el código postal de cuatro dígitos no sea unívoco.

La regla correcta es:

> CEPOES no inventará una tabla arbitraria CP -> barrio; primero reconstruirá y validará la metodología territorial utilizada por Mapa de la Deuda. Si la implementación exacta no es pública, desarrollará una réplica metodológica independiente y reproducible basada en código postal + georreferencia + geometría administrativa, validada contra los agregados territoriales públicos.

Hasta completar este gate, la atribución y los datos de la v2.28 permanecen sin cambios.
