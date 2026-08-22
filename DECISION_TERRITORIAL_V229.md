# CEPOES v2.29 — Decisión metodológica sobre territorialización

Fecha de decisión: 22/08/2026

## Resultado del diagnóstico postal

El procesamiento completo del `Padron_ARCA.txt` vigente confirmó que, entre registros con sexo `M/F` y provincia ARCA `00`, el campo de código postal no contiene en general el CPA alfanumérico moderno. La distribución observada fue:

- código numérico: 6.483.616 registros;
- código numérico de 4 dígitos: 6.482.666;
- código numérico de 4 dígitos entre 1000 y 1499: 5.749.766;
- código vacío: 1.411.096;
- otros formatos: residuales.

Por lo tanto, el insumo territorial disponible en el padrón masivo es, de hecho, mayoritariamente el código postal numérico tradicional de 4 dígitos.

## Sensibilidad del agregado CABA

Aplicando situaciones 1–5, deuda positiva y exclusión documentada de SGR/FGCP, el diagnóstico produjo:

| Universo | Deudores | Personas en mora | Incidencia de mora | Deuda total | Deuda en mora |
|---|---:|---:|---:|---:|---:|
| Provincia 00, cualquier CP | 2.056.367 | 337.829 | 16,4284% | $14,312 billones | $1,785 billones |
| Provincia 00, CP informado | 1.985.657 | 324.409 | 16,3376% | $13,838 billones | $1,734 billones |
| Provincia 00, CP 4 dígitos | 1.985.628 | 324.404 | 16,3376% | $13,838 billones | $1,734 billones |
| Provincia 00, CP 1000–1499 | 1.965.396 | 318.200 | 16,1901% | $13,775 billones | $1,718 billones |

El filtro postal reduce de manera importante la diferencia en cantidad de deudores y deuda total frente al benchmark v2.28, pero no explica por sí solo la brecha en personas en mora.

## Límite para asignar los 48 barrios

Un código postal tradicional de 4 dígitos no identifica unívocamente un barrio de la Ciudad. Un mismo código puede cubrir direcciones situadas en más de un barrio. Por esa razón, **no es metodológicamente válido construir una tabla determinística `CP de 4 dígitos -> barrio` y atribuir todos los deudores de un código a un único barrio**.

La cartografía oficial de los 48 barrios permite resolver barrio a partir de una ubicación suficientemente precisa (coordenadas o dirección normalizada), pero el Padrón ARCA masivo vigente no aporta calle, altura ni coordenadas.

## Revisión de otros archivos masivos del BCRA

La documentación oficial vigente de la Central de Deudores establece que `24DSFAAAAMM` contiene código de entidad, tipo/número de identificación y, para cada uno de los 24 meses, situación, monto y marca de proceso judicial/revisión. No incorpora domicilio, localidad, código postal más preciso ni coordenadas.

`1DSF` es un subconjunto de deudores por situación y `INFRET/INFRETPA` corresponden a información rectificada. No constituyen una fuente territorial adicional.

En consecuencia, descargar esos archivos con el único objetivo de obtener una geografía barrial no aportaría una variable que el diseño oficial no contempla.

## Decisión v2.29

1. **No se fabricará una asignación exacta a barrio desde el código postal de 4 dígitos.**
2. La capa directa BCRA/ARCA se continuará validando primero a nivel CABA.
3. La diferencia de universo se investigará ahora por **tipo de acreedor/informante**, usando registros oficiales del BCRA.
4. La capa barrial de v2.28 no se reemplazará hasta contar con una territorialización reproducible y defendible.
5. Si en el futuro se desarrolla una estimación barrial probabilística, deberá publicarse explícitamente como estimación, con método, cobertura e incertidumbre; no como observación individual exacta.
6. Los microdatos y los identificadores siguen siendo exclusivamente temporales y no se publican ni persisten en GitHub/hosting.

## Próximo gate

Recalcular CABA restringiendo el universo de acreedores a categorías identificables mediante registros oficiales vigentes del BCRA:

- entidades financieras;
- empresas no financieras emisoras de tarjetas de crédito/compra;
- otros proveedores no financieros de crédito;
- y, como diagnósticos separados, proveedores de créditos entre particulares, SGR, FGCP y otros códigos residuales.

El objetivo es determinar cuánto de la brecha de deudores y, especialmente, de mora respecto del benchmark v2.28 se debe al universo de informantes y no a la territorialización.
