# CEPOES v2.29 — Decisión territorial de Endeudamiento

Fecha de actualización: 22/08/2026

## Decisión ejecutiva

La investigación sobre una asignación **exacta** de deudores a los 48 barrios queda cerrada: con los microdatos oficiales vigentes distribuidos por BCRA/ARCA no es posible determinar de manera unívoca el barrio de residencia.

Sin embargo, se habilita una segunda vía metodológica distinta: construir una **estimación territorial probabilística** `CP4 -> barrios` y validarla empíricamente contra la única referencia barrial pública disponible, Mapa de la Deuda.

La estimación sólo podrá pasar a producción si demuestra capacidad predictiva fuera de muestra. No se adoptará una matriz porque reproduzca los mismos datos con los que fue calibrada.

## Límite de la fuente primaria

El procesamiento completo del `Padron_ARCA.txt` vigente confirmó que, entre registros con sexo `M/F` y provincia ARCA `00`, el campo postal se distribuye así:

- código numérico: 6.483.616 registros;
- código numérico de 4 dígitos: 6.482.666;
- código numérico de 4 dígitos entre 1000 y 1499: 5.749.766;
- código vacío: 1.411.096;
- otros formatos: residuales.

El padrón no aporta calle, altura ni coordenadas y no contiene de manera general un CPA completo con precisión suficiente. `DEUDORES/CENDEU` tampoco agrega esas variables.

Por lo tanto sigue prohibido presentar como dato observado cualquier relación determinística `CP4 -> barrio único`, así como centroides, CP modales, puntos representativos o heurísticas equivalentes.

## Nueva hipótesis de trabajo

La existencia de resultados para 48 barrios en Mapa de la Deuda no demuestra por sí sola que esa fuente conozca el barrio exacto de cada deudor. Su documentación pública indica una territorialización a partir de código postal y cartografía, pero no publica el procedimiento de resolución de códigos postales que pueden corresponder a más de un barrio.

La hipótesis a testear es que esos resultados pueden reproducirse mediante una matriz estable de ponderadores:

`w(cp,barrio) >= 0`

con:

`sum_barrio w(cp,barrio) = 1`

De ese modo, para una magnitud agregada por CP:

`valor_barrio = sum_cp valor_cp * w(cp,barrio)`

La matriz representa una distribución territorial estimada. No equivale a geolocalizar personas individualmente.

## Cómo se reconstruye

El pipeline `reconstruir_matriz_cp_barrio.py` implementa tres capas separadas:

1. **Agregados CEPOES BCRA/ARCA por CP4.** Se utilizan únicamente estadísticas agregadas por CP, sexo y edad producidas por el pipeline directo.
2. **Referencia barrial agregada.** Se leen los 48 resultados públicos de Mapa de la Deuda para el mismo período y segmentaciones comparables. La referencia se usa para calibración y validación, no como fuente final de los datos CEPOES.
3. **Restricción geográfica BA Data.** Los datasets georreferenciados ya existentes en `badata/` se utilizan sólo para determinar en qué barrios se observó cada CP. La frecuencia de equipamientos o puntos públicos **no se utiliza como ponderador poblacional**.

Esto evita que la optimización coloque peso en barrios geográficamente incompatibles sin convertir una muestra de equipamientos en una estimación de población.

## Validación fuera de muestra

La reconstrucción debe separar segmentos completos antes del ajuste.

- Los segmentos de entrenamiento se usan para estimar los ponderadores.
- Determinadas combinaciones `sexo x edad` se reservan y no participan de la estimación.
- La matriz obtenida se aplica luego a esos segmentos reservados.
- Se compara la distribución predicha de los 48 barrios con la referencia pública.

El diagnóstico compara además el modelo contra un baseline que usa sólo la compatibilidad territorial de BA Data con pesos uniformes.

La matriz sólo se considera **candidata validada** si, simultáneamente:

- el soporte geográfico observado cubre al menos 90% de los deudores del agregado por CP;
- la distancia de variación total media fuera de muestra es <= 10%;
- la correlación media fuera de muestra entre 48 barrios es >= 0,90;
- el ajuste mejora al menos 10% la distancia de variación total respecto del baseline territorial;
- existen al menos tres segmentos completos de validación.

Estos umbrales son gates de investigación. Superarlos autoriza una segunda auditoría; no convierte la estimación en observación exacta.

## Sensibilidad del agregado propio CABA

Aplicando situaciones 1–5, deuda positiva y exclusión documentada de SGR/FGCP, la corrida produjo:

| Universo | Deudores | Personas en mora | Incidencia de mora | Deuda total | Deuda en mora |
|---|---:|---:|---:|---:|---:|
| Provincia 00, cualquier CP | 2.056.367 | 337.829 | 16,4284% | $14,312 billones | $1,785 billones |
| Provincia 00, CP informado | 1.985.657 | 324.409 | 16,3376% | $13,838 billones | $1,734 billones |
| Provincia 00, CP 4 dígitos | 1.985.628 | 324.404 | 16,3376% | $13,838 billones | $1,734 billones |
| Provincia 00, CP 1000–1499 | 1.965.396 | 318.200 | 16,1901% | $13,775 billones | $1,718 billones |

El filtro postal acota el universo pero no transforma el CP4 en barrio observado.

## Arquitectura mientras se valida

Hasta que la matriz probabilística supere todos los gates:

- el mapa/ranking/ficha de 48 barrios continúa con la capa agregada de v2.28 y atribución visible a Mapa de la Deuda;
- los indicadores directos CABA, sexo, edad, acreedores y evolución continúan como elaboración propia CEPOES sobre BCRA/ARCA;
- no se cambia el rotulado público.

Si la matriz supera la validación y la auditoría posterior, CEPOES podrá reemplazar la capa barrial externa por una capa propia calculada directamente sobre BCRA/ARCA, rotulada explícitamente como **estimación territorial CEPOES**.

## Rotulado si se adopta

La formulación pública deberá dejar claro el carácter estimado, por ejemplo:

> Estimación territorial CEPOES sobre datos del BCRA. La fuente primaria identifica residencia mediante código postal y no permite determinar de manera unívoca el barrio en todos los casos. Los registros agregados se distribuyen entre barrios mediante una matriz de correspondencia postal-territorial validada empíricamente. Los valores barriales deben interpretarse como estimaciones y no como geolocalizaciones individuales exactas.

No se podrá afirmar que CEPOES y Mapa de la Deuda son dos fuentes independientes que confirman un dato si la referencia externa fue utilizada para calibrar la matriz.

## Qué sigue descartado

No se retomarán como método productivo:

- CP modal por barrio;
- centroide de CP;
- un único punto representativo por CP;
- frecuencia de equipamientos públicos usada como peso poblacional;
- GeoNames como asignador de barrio;
- cualquier tabla `CP4 -> barrio único` presentada como exacta.

## Estado

**Barrio exacto observado desde BCRA/ARCA: descartado por insuficiencia de la fuente.**

**Estimación probabilística CP4→barrio: en validación empírica.**

**Mapa público actual: se mantiene sin cambios hasta que esa validación concluya.**
