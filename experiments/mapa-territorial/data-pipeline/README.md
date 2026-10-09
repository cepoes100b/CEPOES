# Datos para Mapa Territorial CEPOES 2.0

**Veredicto: apto con reservas para la rama draft.** La capa de salud y el padrón educativo permiten comparación descriptiva de densidad de inventario. Espacios verdes se entrega como capa exploratoria; sus tasas y rankings quedan deshabilitados por discrepancias entre la localización y el barrio declarado en parte de la fuente.

Consulta y descarga de apoyo: 9 de octubre de 2026. No se modificó el checkout integrador ni se fusionó o desplegó nada.

## Archivos para integrar

Copiar `output/` a un único directorio público nuevo del mapa. Contiene:

- `territories.geojson`: 48 barrios y 15 comunas. Todas las geometrías son válidas.
- `layers/salud.geojson`: 86 registros, 86 puntos verificables.
- `layers/educacion.geojson`: 2.732 registros activos, 2.672 puntos verificables; 60 registros conservados con `geometry:null` y motivo.
- `layers/verdes.geojson`: 2.176 registros y puntos interiores derivados; 2.135 compatibles con el barrio declarado. Los 41 puntos discrepantes quedan conservados para auditoría, con `position_territory_warning:true`, y deben ocultarse en el mapa.
- `indicators.json`: conteos, disponibilidad de coordenadas y registros/km² por barrio y comuna. Para verdes, `comparable:false` y `records_per_km2:null`.
- `manifest.json`: fuentes, licencias, fechas diferenciadas, método, cobertura, advertencias, paths relativos y SHA-256.
- `audit.json`: pruebas de cobertura, geometría, duplicación, faltantes, micro-solapes y detalle de discrepancias.

`manifest.layers` es una lista con `id`, `url`, `count`, `mapped` (geometrías presentes), `positions_verified` (puntos habilitados para mostrar), `comparable`, `missing_coordinates`, `territory_discrepancies` y, para verdes, `comparison_disabled_reason`.

Los puntos y polígonos se entregan en longitud/latitud WGS84 (`OGC:CRS84`). Los puntos verdes no son entradas ni puntos observados: son representaciones interiores derivadas. En 25 polígonos inválidos de la fuente se aplicó `MakeValid` exclusivamente para obtener el punto interior. El polígono original y la superficie declarada no se reemplazan en el inventario oficial.

## Contrato de interfaz

Cada territorio tiene `properties.id`, `slug`, `name`, `level`, `comuna`, `area_km2` y `center:[lon,lat]`.

- IDs de barrio: `barrio:la-boca`, `barrio:monserrat`, `barrio:agronomia`, etc.
- IDs comunales: `comuna:1` a `comuna:15`.
- Los barrios conservan `source_feature_id` oficial 1–48.
- Las comunas se disuelven desde los barrios de la misma versión; se evita mezclar dos cartografías distintas.
- Los centros de etiqueta son puntos interiores derivados, no centroides estadísticos.

Cada equipamiento tiene `properties.id`, `name`, `address`, `barrio_id`, `comuna_id`, `category`, `source_id` y `position_method`. Educación y verdes añaden `geometry_source_id`.

Una posición se puede mostrar sólo cuando existe `geometry` y `position_territory_warning !== true`. La búsqueda y la tabla deben conservar los registros sin punto o con posición cuestionada. Diferenciar “registros de la fuente” de “puntos visibles”.

La ausencia de establecimientos de salud en un barrio se representa por cero registros en este inventario, no por una afirmación de falta total de oferta sanitaria. La capa sólo incluye los hospitales y CeSAC de los recursos citados.

## Fuentes y fechas

Todos los recursos están publicados por BA Data / Gobierno de la Ciudad de Buenos Aires y declaran licencia CC-BY-2.5-AR. Atribuir a BA Data (GCBA), enlazar las fuentes e indicar las transformaciones de CEPOES.

| Fuente | Uso | Fecha visible o registrada | Limitación |
|---|---|---|---|
| [Barrios](https://data.buenosaires.gob.ar/dataset/barrios) | Límites, IDs y comuna | Catálogo 29/07/2026 | Dos micro-solapes heredados; se preservan |
| [Padrón educativo](https://data.buenosaires.gob.ar/dataset/establecimientos-educativos) | Universo de 2.732 activos | Recurso registrado 02/10/2026 | Coordenadas locales del CSV no se interpretan sin CRS explícito |
| [Geometría educativa](https://data.buenosaires.gob.ar/dataset/establecimientos-educativos/resource/319c2bcf-5b17-4c52-abeb-0aca81478c9f) | Apoyo geográfico EPSG:9498 | Recurso visible 01/09/2026 | Universo distinto, se enlaza con controles y no sustituye el padrón |
| [CeSAC](https://data.buenosaires.gob.ar/dataset/centros-salud-accion-comunitaria-cesac) | 50 centros | Catálogo 02/10/2026 | `source_last_modified` heredado dice 2020; no es fecha comprobada de observación |
| [Hospitales](https://data.buenosaires.gob.ar/dataset/hospitales) | 36 hospitales | Catálogo 02/10/2026; GeoJSON 02/09/2026 | XLSX está en EPSG:9498, no en lon/lat |
| [Espacios verdes públicos](https://data.buenosaires.gob.ar/dataset/espacios-verdes) | 2.176 registros, clases y superficies | Catálogo 06/07/2026 | Incluye canteros, jardines, plazas y otros espacios; no equivale a parques accesibles |
| [Polígonos verdes completos](https://data.buenosaires.gob.ar/dataset/espacios-verdes/resource/2a9af960-02a3-44bb-b57e-0a8295f6e0e2) | Recuperación de geometría íntegra | Recurso visible 19/08/2025 | 69 geometrías XLSX estaban truncadas a 32.767 caracteres; se usa GeoJSON |

Las fechas de catálogo, modificación de recurso, descarga y observación son conceptos distintos. Ninguna fuente declara inequívocamente el corte de observación: `data_observed_at:null`. No rotular “datos a octubre 2026” sólo por la fecha de descarga.

## Indicador comparativo

**Registros de salud o educación por km² de superficie administrativa.**

- Numerador: todos los registros del inventario asignados al barrio/comuna por atributo oficial, incluidos los educativos sin punto verificable.
- Denominador: área del polígono oficial, proyectada a EPSG:9498 y expresada en km². La superficie unida de la ciudad es 203,981036 km².
- Tipo: derivado por CEPOES, no indicador publicado directamente por BA Data.
- Alcance: densidad territorial del inventario. La cantidad de registros no informa camas, plazas escolares, turnos, capacidad, calidad, tiempos de viaje ni cobertura poblacional.
- No se usa población manual, estimaciones CP4, ponderaciones ni índices sintéticos.
- Verdes: sólo conteos declarados y exploración; tasas y rankings deshabilitados hasta revisar las discrepancias.

## Hallazgos de calidad

| Severidad | Hallazgo | Evidencia | Tratamiento en el draft |
|---|---|---|---|
| Error resuelto para visualización | 36 hospitales sin punto en el JSON anterior | XLSX con coordenadas EPSG:9498, confirmado por GeoJSON oficial | Transformación real de CRS, 36 posiciones recuperadas |
| Error controlado | Padrón y geometría educativa tienen distinto universo/edificio | 39 sin CUE+anexo, 18 CUI distintos y 3 atributos territoriales incompatibles | 60 registros sin posición, sin reemplazar por centroides ni geocodificación |
| Error resuelto para visualización | 69 WKT verdes truncados por límite Excel | Celdas con exactamente 32.767 caracteres y WKT no parseable | Recuperación de GeoJSON íntegro por ID y territorio |
| Error controlado | 25 polígonos verdes inválidos | Auto-intersecciones de la fuente | Reparación sólo para derivar un punto; método declarado |
| Error / advertencia según caso | 41 puntos verdes fuera del barrio declarado | Distancias desde centímetros hasta 7.503,5 m; listado en `audit.json` | Puntos ocultos; filas preservadas; comparación verde deshabilitada |
| Advertencia | Micro-solapes de barrios oficiales | Belgrano–Palermo 18,4689 m²; La Boca–Puerto Madero 0,3470 m² | Límites preservados; no se asignan automáticamente equipamientos a partir de bordes ambiguos |
| Advertencia | Corte de observación no declarado | Fechas dispares del catálogo y recursos | Mostrar fechas diferenciadas y evitar promesa de actualidad uniforme |

La geografía de los 86 puntos de salud y los 2.672 puntos educativos coincide con los polígonos de su barrio declarado. Todos los puntos verdes representativos están dentro de su polígono fuente, con tolerancia de 5 cm por precisión de serialización.

Las tolerancias son exclusivamente numéricas: diferencia de superficie menor a 0,01 m² al comprobar la disolución comunal y distancia máxima de 0,05 m del punto serializado al polígono fuente. Se informan solapes de más de 0,01 m². Los dos solapes cartográficos observados se reportan aparte y no se absorben como una corrección de límites ni como tolerancia para reasignar registros.

## Reproducción sin dependencias nuevas

Se utilizó Python del sistema con GDAL/OGR/PROJ ya instalado. El lector XLSX usa exclusivamente la biblioteca estándar. No se requiere pandas, openpyxl, Shapely ni instalar paquetes.

Desde esta carpeta:

```sh
/usr/bin/python3 generar_mapa_territorial.py --repo /ruta/al/checkout/CEPOES --output output
CEPOES_REPO=/ruta/al/checkout/CEPOES /usr/bin/python3 -m unittest -v test_mapa_territorial_data
```

Si no se conservan los dos snapshots comprimidos locales, recuperarlos explícitamente antes:

```sh
python descargar_fuentes_mapa.py --sources sources.json --output raw
```

La descarga comprueba SHA-256 antes de reemplazar el snapshot. Si el recurso oficial cambia, falla de manera explícita y mantiene el último snapshot válido. La generación también valida los hashes de los insumos locales para evitar cambios silenciosos de fuente. El paquete se genera entero en una carpeta temporal y sólo reemplaza la salida cuando todas las validaciones terminan; una prueba provoca un fallo de hash y confirma que la última salida válida permanece idéntica.

Guardar para reproducibilidad: `generar_mapa_territorial.py`, `descargar_fuentes_mapa.py`, `test_mapa_territorial_data.py`, `sources.json`, y opcionalmente `raw/educacion.geojson.gz` (181 KB) y `raw/verdes.geojson.gz` (5,7 MB). El GeoJSON verde íntegro de 18,4 MB es un insumo offline y no se publica ni se carga en el navegador. Los archivos auxiliares `raw/educacion.geojson`, `raw/verdes.json`, logs y `__pycache__` no hacen falta para integrar.

## Validación y próximo paso

11 pruebas offline aprobadas: cobertura/IDs, geometrías válidas, disolución comunal consistente, conteos y faltantes, contrato, coordenadas dentro del territorio en salud/educación, puntos verdes dentro del polígono, conciliación del indicador, fuentes/licencias/cortes, hashes, regeneración idéntica byte por byte y conservación de la última salida válida ante fallo de fuente.

Próximo paso: integrar el paquete en la interfaz draft respetando `positions_verified` y `comparable`, y verificar escritorio/móvil sin publicar ni desplegar.
