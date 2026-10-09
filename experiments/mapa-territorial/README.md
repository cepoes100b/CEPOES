# Mapa Territorial CEPOES 2.0 · laboratorio local

Implementación original del [encargo #192](https://github.com/cepoes100b/CEPOES/issues/192), en [PR draft #193](https://github.com/cepoes100b/CEPOES/pull/193). **No está publicada ni habilitada para fusionar.**

## Aislamiento

`public/` es una capa exclusivamente experimental, fuera de `deploy/site-overlay/`. Ningún workflow la copia ni la publica. El build local la agrega después del build público normalizado, en `/laboratorio/mapa-territorial/`, sin enlace en menú, buscador, sitemap ni feeds. No se modifica R2, respaldo, despliegue, portada, presupuestos, credenciales, DNS, analítica o suscriptores.

## Qué implementa

- 48 barrios y 15 comunas, límites locales, selección por mapa/búsqueda/selectores/tabla.
- MapLibre GL JS 6.13.0 local, pan/zoom/encuadre, etiquetas de territorios sin solapamiento deliberado, clusters y selección de registros. Calles de OpenFreeMap opcionales y fallback local.
- Salud: 86 registros/puntos; educación: 2.732 registros, 2.672 puntos y 60 faltantes justificados; verdes: 2.176 registros, 2.135 puntos habilitados y 41 discrepancias señaladas.
- Densidad de inventario para salud/educación, comparada con comuna/Ciudad. Verdes no tiene tasa/ranking por sus discrepancias.
- URL con territorio/capa/escala y Atrás/Adelante. Búsqueda libre y ubicación personal no se guardan en URL. No se solicita geolocalización.
- Fuentes, licencia, fechas y métodos visibles. Registros sin coordenadas permanecen en tabla; cero y falta de datos son estados diferentes.
- Reglas responsive para 320/390/430/1440 y claro/oscuro, foco, controles ≥44px, movimiento reducido, tabla accesible. **Pendientes de verificación visual real.**

## Preparar dependencias

Node 24 y npm. El lockfile fija versiones y hashes; `npm ci` no requiere instalar software global.

```sh
npm ci --ignore-scripts --prefix experiments/mapa-territorial
npm run vendor --prefix experiments/mapa-territorial
node --test tests/mapa-territorial/*.test.mjs
```

Los archivos MapLibre ya están versionados en `public/assets/mapa-territorial/vendor/`. `vendor/manifest.json` registra hashes y licencia. El frontend no depende del registro npm ni de un CDN de JavaScript.

## Datos y reproducción

Leer `data-pipeline/README.md`. Los insumos locales del repositorio se verifican por SHA-256. Dos GeoJSON de apoyo se descargan de fuentes oficiales con hash fijado; no están en el frontend ni se versionan en este PR. Si una URL oficial cambia de bytes, se aborta y conserva la última salida válida.

```sh
python experiments/mapa-territorial/data-pipeline/descargar_fuentes_mapa.py \
  --sources experiments/mapa-territorial/data-pipeline/sources.json \
  --output experiments/mapa-territorial/data-pipeline/raw
/usr/bin/python3 experiments/mapa-territorial/data-pipeline/generar_mapa_territorial.py \
  --repo . --output experiments/mapa-territorial/public/assets/mapa-territorial/data
CEPOES_REPO="$PWD" \
CEPOES_MAP_DATA_OUTPUT="$PWD/experiments/mapa-territorial/public/assets/mapa-territorial/data" \
/usr/bin/python3 -m unittest discover -s experiments/mapa-territorial/data-pipeline -p 'test_*.py' -v
```

Requiere bindings Python GDAL/OGR/PROJ. El entorno de preparación ya los tenía; no se instaló una cadena geoespacial adicional. En un entorno sin ellos, usar el paquete oficial del sistema antes de regenerar. Los artefactos y pruebas JS pueden usarse sin regeneración geoespacial.

## Copia pública completa y normalización

El repositorio es un overlay: no contiene toda la base del sitio. El script local `scripts/build_public_local.py` obtiene exclusivamente recursos públicos de `cepoes.org`, conserva su trazabilidad, replica los pasos de preparación/validación canónicos y permite agregar este experimento. La captura pública **no es un respaldo SFTP** y no sirve para restaurar producción.

Ver los comandos completos y resultados en `docs/mapa-territorial/estado-y-pruebas.md`. El constructor no puede publicar ni invoca notificaciones. La normalización de la nueva página se limita a ese HTML, después de generar los feeds.

Para servir una copia ya generada en un entorno que permita sockets locales:

```sh
python -m http.server 4173 --bind 127.0.0.1 --directory /ruta/al/candidato
# Abrir http://127.0.0.1:4173/laboratorio/mapa-territorial/
```

## Evidencia y límites

Pruebas de datos y de estado DOM son reproducibles. Los tests de adaptador usan un motor falso y **no validan WebGL ni apariencia**. La salida pública completa fue construida y los validadores canónicos se ejecutaron sobre ella.

En el entorno actual no se logró render del candidato: `sites-preview` está ausente, el navegador cloud no alcanza el servidor local y Chromium falla al crear el socket de su proceso. No se alteró el sandbox ni se publicó una vista para eludirlo. Quedan pendientes las capturas 4 anchos × 2 temas, las mediciones reales de latencia/FPS/memoria y la prueba táctil/teclado del motor real.

`measure_payload.py` sólo calcula bytes y gzip estimado. Las métricas del navegador expuestas en `window.__CEPOES_MAP_QA` son locales, no se envían a ningún servidor.

## Publicación futura

Sólo después de completar el render y recibir aprobación final: proponer un diff explícito de integración con el publicador existente, R2 y backups. Este draft no crea ni autoriza un despliegue paralelo. El issue permanece abierto.
