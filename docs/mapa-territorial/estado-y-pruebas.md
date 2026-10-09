# Estado y pruebas · Mapa Territorial CEPOES 2.0

Fecha: 9 de octubre de 2026. [PR draft #193](https://github.com/cepoes100b/CEPOES/pull/193) · [encargo #192](https://github.com/cepoes100b/CEPOES/issues/192), abierto.

**Resultado: prototipo implementado y salida pública local construida, con controles offline aprobados. No es una candidata aprobada para publicar: falta render real y medición de interacción.**

## Hitos

- Hito 0: auditoría, diseño propio, arquitectura, capacidades probadas y PR draft documentados.
- Hito 1: implementación completa del prototipo y controles de datos/estado; validación visual y táctil pendiente.
- Hito 2: integridad, seguridad, URL, DOM, estados faltantes/error, recuperación y contratos de accesibilidad probados; rendimiento de navegador y contraste renderizado pendientes.
- Hito 3: salida pública completa generada y validada; no aprobado por falta de render real en 4 anchos × 2 temas. No fusionar ni desplegar.

## Datos verificados

| Capa | Registros | Puntos habilitados | Tratamiento |
|---|---:|---:|---|
| Salud | 86 | 86 | Hospitales y CeSAC; CRS original transformado y verificado |
| Educación | 2.732 | 2.672 | 60 sin punto por enlace o identidad no verificables; permanecen en tablas/conteos |
| Espacios verdes | 2.176 | 2.135 | 41 discrepancias territoriales señaladas; puntos ocultos y comparación suspendida |

48 barrios, 15 comunas y 63 IDs únicos. Geometrías válidas, comunas disueltas de la misma versión de barrios. Se preservan dos micro-solapes heredados (18,4689 y 0,3470 m²) con tolerancias explícitas. Los puntos verdes son interiores derivados de polígonos, no entradas.

Indicador: registros/km² para salud y educación. Numerador de inventario según atributo oficial, incluidos registros sin punto; superficie administrativa como denominador. Comuna y Ciudad usan sumas de registros/superficies. No mide capacidad, calidad, accesibilidad ni cobertura poblacional.

Las fuentes BA Data declaran CC-BY-2.5-AR. La interfaz separa actualización de catálogo, modificación del recurso y corte de observación (no informado). Detalle y hashes en `data-pipeline/README.md`, `sources.json` y el manifiesto público.

## Pruebas ejecutadas

| Prueba | Resultado | Alcance real |
|---|---|---|
| Datos GDAL/OGR/PROJ | 11/11 aprobadas | 48/15, geometrías, puntos, IDs, faltantes, sumas, hashes, reproducción idéntica y preservación ante fallo |
| Node: modelo, DOM, adaptador y a11y estática | 11/11 aprobadas | Carga lazy, selección, URL, Atrás, error HTTP/reintento, textos, filtros, fallback, contraste calculado y contratos |
| Helper de build local | 4/4 aprobadas | Sólo HTTPS/origen autorizado, bloqueo de rutas privadas, referencias y destinos locales |
| R2 universal | Aprobado local | Sintaxis, workflows, detectores y contratos canónicos; no sustituye CI remota del commit final |
| Build público canónico | 19 pasos aprobados | Datos públicos, índices, navegación, catálogo, Lo nuevo, puentes, búsqueda, R1, contraste existente y sitio |
| Integración local del prototipo | 6 pasos aprobados | Normalización de un HTML y validadores completos sobre el candidato |
| Revisión independiente de código | Sin P1/P2 confirmados pendientes | Detectó errores de estado, carreras y contraste; corregidos y con regresiones |
| Render WebGL y visual | **No ejecutado con éxito** | Bloqueo de entorno detallado abajo |
| Latencia, FPS, memoria real | **No medidos** | Requieren navegador funcionando sobre este candidato |
| Táctil/dispositivo físico | **No probado** | Reglas implementadas y pendientes de verificar |

Los tests DOM usan JSDOM; el motor de prueba es simulado. El mensaje esperado de falta de WebGL en ese test confirma la ruta de fallback, no un funcionamiento del mapa real.

Regresiones incorporadas tras revisión: limpiar ficha/tabla al cambiar capa o categoría; sincronizar filtros al volver; restaurar realmente estilo local si falla OpenFreeMap; invalidar zoom de cluster tardío; controles deshabilitados antes de inicializar; SVGs de zoom y hover legibles en oscuro. Contorno territorial doble blanco/azul para distinguir selección sobre todos los colores.

## Build y aislamiento

La base pública capturada corresponde al marcador `2307ecf17742bc25db91a10d5b362f849e295da9`, estable durante la descarga. Se verificaron sus tres huellas públicas. El checkout parte de `ddefe51` y Hito 0 está en `f7e0f1a`; los hashes del prototipo identifican los bytes nuevos del árbol de trabajo.

La base canónica contiene 168 HTML; el candidato, 169 HTML, 48 fichas barriales y 151 URLs indexables. La integración sólo añade el experimento. Ningún archivo previo cambia; sitemap, búsqueda, Lo nuevo y feeds conservan sus hashes exactos. El helper se ejecuta offline en reintegraciones. Esta captura HTTPS no es un respaldo SFTP ni una imagen completa de archivos privados del hosting.

Comandos y detalles: [build local](build-local.md), [reporte del build](evidence/build-report.md), [resumen portable](evidence/build-verification.json). Después de una corrección:

```sh
python experiments/mapa-territorial/scripts/build_public_local.py \
  --repo "$PWD" --output /ruta/al/ensayo \
  --expected-sha "$(git rev-parse HEAD)" --mode integrate \
  --prototype-dir experiments/mapa-territorial/public
```

## Peso reproducible, todavía sin benchmark de navegador

`evidence/static-payload.json` se regenera con:

```sh
python experiments/mapa-territorial/scripts/measure_payload.py \
  --output docs/mapa-territorial/evidence/static-payload.json
```

Medición estática aproximada al cierre:
- Inicio con salud: 3,00 MB de recursos propios; 0,89 MB gzip estimado.
- Educación diferida: 1,30 MB / 0,139 MB gzip.
- Verdes diferida: 1,12 MB / 0,142 MB gzip.
- Se excluyen de ese subtotal los estilos/fuentes compartidos del sitio y las calles opcionales. El servidor de preview no prueba compresión real del hosting.

El objetivo inicial de <2 MB sin comprimir / <800 KB gzip no se alcanzó. Se conserva precisión territorial completa antes que simplificar límites sin un benchmark visual. El mayor costo de datos inicial es cartografía: 1,23 MB / 428 KB gzip. Siguiente optimización a evaluar con render: transporte topológico sin pérdida o carga diferida de geometría comunal. No se afirma que el mapa sea más rápido que D3 sin medir ambas versiones.

## Bloqueo observado de render

- `sites-preview` ausente en perfil portable.
- Navegador cloud `cua_repl`: servidor local no accesible (HTTP 502/conexión rechazada).
- Navegación `file://`: denegada por la política del navegador; no reintentada por otra vía.
- Chromium instalado: falla `socket() Operation not permitted` antes de renderizar.
- Ejecución escalada: falla `bwrap ... Not a directory` antes de arrancar Chromium.

No se alteró el sandbox, no se creó un túnel ni se publicó el prototipo para eludir el bloqueo.

## Checklist pendiente antes de aprobación final

- [ ] Render del candidato actualizado a 320, 390, 430 y 1440 px, claro/oscuro; capturas vinculadas al commit exacto.
- [ ] Verificar zoom/pan/clusters/etiquetas, filtros rápidos, selección, restablecer, volver y estado de error en el motor real.
- [ ] Comprobar teclado, foco y lector de pantalla, gestos táctiles, scroll de página y contrastes efectivos.
- [ ] Medir descarga real, mapa listo, latencia de filtro, FPS en zoom y memoria; registrar navegador, red, CPU y dispositivo.
- [ ] Comparar referencia interna con el mismo contexto; decidir optimización a partir de las medidas.
- [ ] Repetir R2 y controles remotos en el commit final.
- [ ] Obtener autorización final de integración/fusión/publicación.

Único próximo paso: habilitar un entorno con navegador real que alcance la copia local y completar esta matriz. Producción, datos existentes, suscriptores y el pipeline canónico permanecen sin cambios.

## Control remoto del primer commit de implementación
R2 del commit `cbc1083` detectó una URL ficticia con usuario/clave en el test del capturador. Se corrigió el fixture siguiendo el patrón del propio detector, sin debilitarlo ni agregar excepciones. No era una credencial real. El escaneo local inicial sólo veía el commit documental, porque R2 compara contra HEAD; se repitió sobre un commit local con el diff completo después de esta corrección. La CI remota del siguiente commit debe quedar aprobada antes de cerrar la entrega offline.
