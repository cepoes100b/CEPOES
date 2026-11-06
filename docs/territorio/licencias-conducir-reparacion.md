# Recuperación del directorio de licencias de conducir

Base: `db98327d775e06db9782f40862cdacbac1cab546`, revalidada el 6/11/2026.

Se utiliza exclusivamente `badata/licencias_conducir.csv` versionado. El mapeo
recupera `lat`, `long`, `calle_nombre` + `calle_altura`, `actividad`, `link`,
`email` y `observacion`. La dirección compuesta es un fallback configurable:
no cambia las capas que no lo solicitan ni reemplaza una dirección explícita.
Se conservan los 18 IDs, el orden estable, nombres, comuna/barrio declarados,
contacto telefónico, fuente y metadatos temporales. Las actividades distintas
de ACA Flores, ACA Libertador y Comuna 13 continúan como registros separados.

La observación de Comuna 5 se conserva literalmente: «(Momentáneamente sin
servicio)». Es información histórica de la fuente cuyo `source_last_modified`
es 2019-04-22T14:28:29.976042; no se verificó el funcionamiento actual. No se
realizó ni se afirma una nueva descarga del CSV oficial.

## Derivados

`equipamientos/busqueda.json` sólo cambia en los 18 registros de esta capa.
El publicador ejecuta `generar_indice_busqueda_equipamientos.py`, que produce
`/assets/data/equipamientos-busqueda.json`; ambos generadores de búsqueda se
prueban contra los mismos registros. El índice compacto no transporta email;
el directorio completo sí lo conserva para sus acciones de contacto.

La página versionada `/territorio/equipamientos/` usa `CEPOES.equipmentCatalog()`
y `CEPOES.equipment(type)`, definidos en el runtime heredado `/assets/data.js`.
Ese runtime no está versionado aquí y no pudo descargarse: la ruta efectiva
del JSON completo en producción sigue pendiente de confirmar. No se deduce
un defecto de producción a partir de una ruta supuesta.

El resumen territorial aplica su regla preexistente de prioridad espacial:
18 registros pasan a territorializarse por coordenadas y cuatro discrepan
con el barrio/comuna declarado. Los tres de Comuna 14/Palermo se contabilizan
en Comuna 2/Recoleta y el de Comuna 5/Boedo en Comuna 3/San Cristóbal. Se
actualizan exclusivamente esos conteos y controles derivados; el método y
las etiquetas territoriales del directorio permanecen intactos. El total
sigue siendo 18. No se refrescan fechas ni las restantes capas.

## Verificación y límite de entrega

- `python -m unittest -v test_licencias_conducir`: mapeo completo, coordenadas,
  direcciones, actividades, enlaces, observación, IDs/orden, duplicados legítimos,
  fallback optativo, ambos índices y ejecución real del runner diario aislada.
- `python verificar_oferta_total.py`: 61 capas, 106.233 registros.
- `python verificar_resumen_territorial.py`: controles territoriales.
- `python validar_pr_r2.py --base-sha db98327d775e06db9782f40862cdacbac1cab546`.
- `python -m unittest test_cadena_publicacion.py test_endeudamiento_publico.py`.

La consulta pública desde el entorno devuelve HTTP 403; la herramienta web
tampoco puede abrir la página. No se ha completado QA visual de ficha/listado/
mapa en escritorio y móvil ni se ha certificado el archivo consumido en
producción. El PR debe permanecer en borrador hasta resolver estas comprobaciones.
No se fusionó ni desplegó, ni se enviaron correos.
