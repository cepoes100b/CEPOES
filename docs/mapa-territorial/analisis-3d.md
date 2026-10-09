# Modo analítico territorial: primera integración incremental

## Alcance y aislamiento

Ampliación del issue #192, posterior a la fusión del PR #193 (`73d0cf3`). Se conserva el explorador de inventarios. Este trabajo vive en `experiments/mapa-territorial/`, usa el mismo `TerritorialMap` y permanece fuera de los destinos del publicador. No habilita correo, notificaciones, R2, despliegue ni enlaces públicos. Se entrega mediante PR en borrador, sin autorización para fusionar o publicar.

La base local de trabajo tiene árbol `addca76261940b8ceb9bffb4c9b0bbee0e909822`, idéntico al de `main` en `73d0cf3`; el commit remoto parte del SHA de `main` verificado, no del historial local de preparación.

## Interfaz original e integración

- Selector persistente **Explorar servicios / Analizar indicadores**.
- Mapa único. La entrada a Analizar importa `analysis/controller.mjs` y obtiene su dataset sólo al solicitar ese modo.
- Vista plana y 3D usan la misma selección, fuente, escala, ranking y tabla. La URL conserva modo, representación, indicador y territorio. Atrás/Adelante reconstruyen la vista.
- Se preserva una selección barrial al cambiar de modo. Cuando la fuente sólo cubre comunas, el barrio queda explícitamente **sin dato** y no recibe el valor comunal. El control “Ver las 15 comunas” hace el cambio de escala de forma explícita.
- Los 15 territorios están disponibles por teclado, selector, ranking y tabla. El ranking comparte posición entre valores iguales a la precisión visible; los faltantes quedan fuera del orden estadístico.
- El prototipo HTML aportado se estudió como referencia de interacción. Su estructura, estilos, datos embebidos y motor no se copiaron.

## Primer indicador

Población en viviendas particulares que declaró no tener obra social, prepaga ni plan estatal de salud, **Censo 2022**. Se presenta como cobertura declarada en ese universo y fecha. No describe uso exclusivo de hospitales públicos, cobertura actual, capacidad de servicios ni desocupación EPH/ETOI.

Fuente primaria: [INDEC, cuadro 1.1 de salud para CABA](https://www.indec.gob.ar/ftp/cuadros/poblacion/c2022_caba_salud_c1_1.xlsx). Contraste: cuadro 6.C.3 del [Anuario Estadístico 2023 de la Ciudad](https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2024/07/anuario_estadistico_2023.pdf), página impresa 84. Numerador y denominador proceden de la misma tabla; la Ciudad se calcula mediante cociente de sumas.

Presupuesto, alquiler y desocupación del prototipo quedan pendientes. En particular, el presupuesto comunal administrado no equivale al gasto total del GCBA localizado en una comuna; el censo distingue población total y población en viviendas particulares. La coincidencia con cifras ya versionadas por CEPOES no reemplaza verificar el anexo oficial y sus denominadores.

## Escala y límites de lectura

- Porcentajes: dominio **0–100%**, fijo para todas las comunas, todas las selecciones y ambas representaciones.
- Altura = porcentaje / 100 × **3.200 metros gráficos**, base exactamente cero. Es una magnitud simbólica, no elevación geográfica. Un cero válido tiene altura cero; un faltante es gris y no genera altura.
- Color continuo y longitud de las barras usan exactamente la misma normalización. Leyenda, ranking, cifras y tabla usan la misma unidad y corte.
- La geometría de cada prisma conserva el área administrativa. **El volumen no representa un total**: la comparación cuantitativa se hace con las alturas, cifras, ranking o vista plana. Perspectiva y oclusiones justifican conservar siempre la alternativa plana y la tabla.
- La selección usa contorno naranja y un estado textual; no sustituye el color del indicador.
- Otros indicadores que se agreguen deberán tener fuente, licencia, universo, numerador, denominador, unidad, período, cobertura y calidad verificadas. Una escala propia debe declararse; no se comparan alturas de indicadores distintos.

## Animación, compatibilidad y recursos

`analysis/layer.mjs` opera sobre la fuente comunal existente. Un solo `requestAnimationFrame` cancelable interpola el `feature-state` que realmente alimenta altura y color. No se atribuye animación a las transiciones de propiedades data-driven de MapLibre, que no interpolan esos cambios. No se regeneran geometrías por frame.

Se usan APIs públicas de MapLibre 6.13.0. No se accede a `map.transform`, no se eleva texto mediante proyecciones privadas y se ocultan los rótulos de suelo en perspectiva 3D. La selección y los nombres completos permanecen en controles y ranking. La geometría es la ya validada en CEPOES (48 barrios / 15 comunas).

El giro está apagado por defecto. Sólo se inicia mediante su botón y se detiene al interactuar con el mapa mediante puntero, rueda, toque o teclado. No se reactiva solo. Los cambios en `prefers-reduced-motion` se escuchan dinámicamente: finalizan interpolaciones y deshabilitan el giro. Ocultar la pestaña detiene los bucles. La resolución del mapa analítico se limita a DPR 1,5 y al volver al explorador se restaura la anterior.

MapLibre 6 necesita WebGL2 tanto para la vista plana como para la 3D. Ante fallo inicial o pérdida del contexto gráfico, se conservan ranking, tabla y controles territoriales; el 3D queda deshabilitado. Esa alternativa textual no se presenta como un render de mapa.

## Verificación

En la revisión local inicial pasaron 22 pruebas JS/DOM/adaptador y 15 pruebas Python de datos. Se corrigieron carreras de cargas al navegar Atrás/Adelante, conservación de foco, activación inicial de cámara y finalización de movimiento reducido.

Pruebas puras y de adaptador cubren validación de datos, suma ponderada, cero/faltante, empates, URL, interpolación, cancelación, movimiento reducido, giro voluntario, selección barrial y restauración de la instancia 2D. Los tests DOM/adaptador no validan apariencia ni WebGL.

La revisión de navegador usa el mismo harness canónico del PR #194, en el propio SHA de este candidato, más `qa/analysis.spec.mjs`. Cubre 320/390/430/1440 px, ambos temas, WebGL2 real, píxeles del canvas, vista plana/3D, selección/URL, retorno a 2D, ausencia de GPU, error HTTP y reintento, movimiento reducido y accesibilidad. Las capturas y métricas se preservan de forma acotada en logs de Actions, sin crear un despliegue externo ni almacenamiento de artifacts facturable.

ANGLE/SwiftShader produce un render WebGL real por software: sus métricas no equivalen a rendimiento de una GPU física ni a validación en Safari/iPhone. La demostración navegable requiere servir la copia local completa; no se publicó una preview externa. El resultado final de Actions y la revisión visual se registrarán antes de considerar al candidato listo para revisión.

## Licencias

- Motor MapLibre GL JS: BSD-3-Clause, bundle y licencia locales ya fijados.
- Cartografía BA Data: atribución y licencia preservadas en el manifiesto existente.
- Datos censales INDEC: CC BY-SA 4.0; se atribuye la fuente y se indica el cálculo CEPOES. Esa licencia no se atribuye al diseño editorial del PDF del Anuario.
- Sin teselas, fuentes ni JavaScript de terceros nuevos. Las calles opcionales del explorador conservan sus atribuciones preexistentes.
