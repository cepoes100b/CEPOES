# CEPOES v2.29 — Cierre de la decisión territorial de Endeudamiento

Fecha de cierre: 22/08/2026

## Decisión ejecutiva

La investigación territorial queda **cerrada**. Con los microdatos oficiales vigentes distribuidos por BCRA/ARCA, CEPOES puede construir de forma reproducible indicadores propios para CABA, sexo, edad y tipo de acreedor, pero **no puede atribuir de manera exacta a una persona deudora a uno de los 48 barrios**.

La causa no es técnica sino informacional: `Padron_ARCA.txt` aporta provincia y, mayoritariamente, código postal numérico tradicional de 4 dígitos; no aporta calle, altura, coordenadas ni CPA completo de precisión suficiente. `DEUDORES/CENDEU` tampoco incorpora esas variables territoriales.

Por lo tanto, queda prohibido para producción fabricar una relación determinística `CP de 4 dígitos -> barrio` o usar centroides, puntos representativos, códigos modales u otras heurísticas como si fueran observaciones exactas.

## Evidencia que cierra la cuestión

El procesamiento completo del `Padron_ARCA.txt` vigente confirmó que, entre registros con sexo `M/F` y provincia ARCA `00`, el campo postal se distribuye así:

- código numérico: 6.483.616 registros;
- código numérico de 4 dígitos: 6.482.666;
- código numérico de 4 dígitos entre 1000 y 1499: 5.749.766;
- código vacío: 1.411.096;
- otros formatos: residuales.

Un CP tradicional de 4 dígitos no identifica de manera unívoca un barrio. La cartografía oficial de los 48 barrios permite resolver barrio sólo cuando existe una localización suficientemente precisa, como coordenadas o dirección normalizada; esas variables no están en el padrón masivo.

La documentación de CENDEU confirma, a su vez, que los archivos de deuda contienen identificación, entidad, situación, monto y variables crediticias, pero no domicilio, calle, altura, coordenadas ni una geografía barrial adicional.

## Sensibilidad del agregado propio CABA

Aplicando situaciones 1–5, deuda positiva y exclusión documentada de SGR/FGCP, la corrida produjo:

| Universo | Deudores | Personas en mora | Incidencia de mora | Deuda total | Deuda en mora |
|---|---:|---:|---:|---:|---:|
| Provincia 00, cualquier CP | 2.056.367 | 337.829 | 16,4284% | $14,312 billones | $1,785 billones |
| Provincia 00, CP informado | 1.985.657 | 324.409 | 16,3376% | $13,838 billones | $1,734 billones |
| Provincia 00, CP 4 dígitos | 1.985.628 | 324.404 | 16,3376% | $13,838 billones | $1,734 billones |
| Provincia 00, CP 1000–1499 | 1.965.396 | 318.200 | 16,1901% | $13,775 billones | $1,718 billones |

El filtro postal reduce parte de la diferencia frente al benchmark v2.28, pero no transforma el CP en una variable barrial y tampoco explica por sí solo la brecha de mora.

## Arquitectura productiva definitiva

La página pública de Endeudamiento se resuelve con **dos capas explícitamente separadas**:

### A. Capa territorial — 48 barrios

Para mapa, ranking, ficha barrial y evolución por barrio se mantiene la capa pública agregada de **Mapa de la Deuda — CEC + FES**, elaborada sobre la Central de Deudores del BCRA.

CEPOES la consume en tiempo de lectura mediante su contrato público `mobile-slices-v2`, sin republicar microdatos ni presentar esos agregados como elaboración propia. La validación v2.28 exige 48 barrios, correspondencia de `geo_id`, métricas consistentes, filtros y CORS.

Esta es la única capa actualmente disponible que satisface simultáneamente granularidad barrial y trazabilidad suficiente para una publicación pública.

### B. Capa CEPOES — elaboración propia sobre BCRA/ARCA

El pipeline directo continúa para producir indicadores propios cuya geografía sí está respaldada por la fuente:

- total CABA;
- deudores y personas en mora;
- monto total y monto en mora;
- sexo;
- franja etaria;
- tipo de acreedor/informante;
- evolución mensual;
- controles de universo y calidad.

Estos indicadores deberán rotularse como **CEPOES — elaboración propia sobre BCRA/ARCA** y no se desagregarán a barrio salvo que aparezca una nueva fuente territorial verificable.

## Regla de interfaz

No se mezclarán procedencias de forma silenciosa.

- Todo componente barrial debe mostrar: `Fuente territorial: Mapa de la Deuda — CEC + FES, sobre Central de Deudores BCRA.`
- Todo componente construido por el pipeline directo debe mostrar: `Fuente: BCRA/ARCA · Elaboración propia CEPOES.`
- Si una misma pantalla incluye ambas capas, la procedencia debe figurar junto al bloque correspondiente, no sólo en una nota al pie genérica.

## Qué se abandona definitivamente

No se harán nuevas pruebas de producción basadas en:

- CP modal por barrio;
- centroide de CP;
- punto representativo obtenido de mobiliario/equipamiento;
- una muestra no representativa de domicilios públicos;
- GeoNames como asignador de barrio;
- intersección espacial de un único punto por CP;
- cualquier tabla `CP4 -> barrio único` presentada como exacta.

Esas vías pueden existir como antecedentes de investigación, pero no son gates de publicación y no deben bloquear nuevamente el producto.

## Única alternativa futura para reemplazar la capa externa

CEPOES sólo reemplazará la capa barrial externa si ocurre una de estas dos condiciones:

1. obtiene una fuente primaria con dirección, coordenadas o CPA suficientemente preciso y con condiciones de uso compatibles; o
2. decide producir una **estimación barrial**, no una observación exacta, con un modelo probabilístico documentado, ponderaciones reproducibles, cobertura e incertidumbre publicadas.

Una estimación nunca se etiquetará como dato observado por barrio.

## Gate de publicación desde este cierre

La territorialización deja de ser un gate de v2.29. Los gates pendientes del pipeline propio son exclusivamente los necesarios para la capa CABA: universo de personas físicas, universo de acreedores, consistencia de mora y montos, privacidad/supresión, actualización mensual y JSON agregado.

El mapa de 48 barrios no debe esperar esos trabajos: continúa operando con la capa agregada validada de v2.28.

## Resultado

**Mapa barrial: resuelto con fuente agregada territorial validada.**

**Elaboración propia BCRA/ARCA: continúa a nivel CABA y segmentaciones compatibles con la fuente.**

**Asignación exacta BCRA/ARCA a 48 barrios: descartada por insuficiencia de la fuente, no por falta de implementación.**
