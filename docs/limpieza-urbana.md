# Monitor de limpieza urbana — PR #236

## Producto y decisión editorial

Sección territorial permanente, con el mapa como entrada. El encargo se amplió el 16/10/2026 a limpieza del espacio público; el monitor utiliza toda la categoría **HIGIENE** del SUACI. La nota de LA NACION fue el disparador inicial; su archivo y su diseño ya no son la fuente ni el modelo del producto.

Datos oficiales procesados: **858.461 contactos únicos, 01/01/2025–15/10/2026**, 48 barrios y 15 comunas. Octubre de 2026 es un mes parcial. Hay 1.444 contactos sin barrio; en 207 se usa la comuna oficial del barrio ante una comuna de origen diferente o faltante. No se detectaron duplicados de contacto en esta versión.

El volumen incluye quejas y solicitudes de servicios programados: 159.612 quejas, 413.781 solicitudes, 279.552 servicios, 4.347 denuncias y 1.169 reportes. Mostrar todo como fallas de limpieza sería engañoso. Los cinco tipos se conservan como filtros independientes de los ocho temas.

Los temas son residuos y recolección; retiro de escombros, muebles y poda; contenedores y cestos; barrido y limpieza; control de plagas; reciclado y separación; prestación del servicio; servicios por eventos. `config/limpieza-prestaciones.json` contiene la clasificación explícita de las 40 denominaciones originales observadas. Una prestación nueva detiene el refresco hasta su revisión.

Mapa, total, serie mensual y tabla usan el mismo universo filtrado. Se ofrecen los últimos 12 meses completos (selección inicial), últimos tres completos, último mes disponible y todo el histórico. El último mes parcial se señala en el gráfico y su tabla; el total del archivo completo se informa por separado. La escala del mapa depende del tema y tipo de contacto; se conserva al seleccionar territorios. Las cantidades absolutas muestran demanda registrada; la lectura debe complementarse con población, circulación, actividad comercial, acceso a canales e inspecciones para evaluar diferencias de limpieza. El texto público propone seguimiento de frecuencia efectiva, resultados por concesionaria y solución del problema, sin confundir cierre administrativo con solución efectiva.

## Fuentes

Catálogo oficial: https://data.buenosaires.gob.ar/dataset/sistema-unico-atencion-ciudadana

- Recurso 2025: `ec9da864-d2e0-480d-8fd3-06807c083ff4`.
- Recurso 2026: `3350c0ae-58ff-4252-b496-7cb07bdb88b1`.
- Archivos canónicos: `https://cdn.buenosaires.gob.ar/datosabiertos/datasets/atencion-ciudadana/sistema-unico-atencion-ciudadana/sistema-unico-de-atencion-ciudadana-AAAA.csv`.
- Límites oficiales: `badata/barrios.geojson` del repositorio; geometrías simplificadas para esta escala de consulta.
- Se conservan SHA-256 y tamaño de cada CSV en el JSON público. Los identificadores de solicitud, género y direcciones individuales no se publican.

El esquema real de 2025 tiene `long`/`lat`; 2026 usa `x`/`y` locales. La agregación territorial utiliza barrio/comuna y no interpreta esas coordenadas como WGS84. Los dos archivos completos suman 486.340.835 bytes. La primera descarga local de 2025 quedó truncada; se completó y verificó su tamaño total antes de procesarla. El descargador versionado rechaza respuestas HTML, HTTP 206, tamaños incompletos y cabeceras inesperadas; la normalización exige filas completas y un salto de línea final.

## Actualización preparada

Se integra al workflow canónico `territorio.yml`, sin workflow alternativo. Comprobación programada los lunes, dentro de su ejecución diaria de las 15:10 de Buenos Aires; las ejecuciones manuales y los cambios de código también pueden ejecutar la comprobación. Caché anual con ETag y huella para reducir descargas. El catálogo declara una frecuencia semestral, pero el recurso 2026 descargado ya contiene datos hasta el 15/10; la fecha efectiva sale de los registros.

1. `scripts/descargar_suaci.py`: descarga atómica, validación de respuesta/tamaño y manifiestos locales; HTTP 304 reutiliza el crudo existente.
2. `scripts/generar_limpieza_urbana.py`: clasificación explícita, contactos únicos, correspondencia barrio/comuna, agregación, control de meses/cobertura y no regresión de series.
3. `scripts/render_limpieza_urbana.py`: títulos, KPIs, corte y metodología desde el agregado; distingue última versión de datos y comprobación de fuente.
4. `scripts/actualizar_limpieza_urbana.py`: coordina descarga, pruebas, generación y metadatos; sólo tras superar los controles registra una comprobación satisfactoria.
5. El workflow conserva el registro de productor y la cadena de publicación existentes. Los nuevos accesos se generan por el normalizador territorial, sin tarjetas paralelas manuales.

Una falla conserva el producto anterior; no publica un archivo vacío ni una selección parcial. Una reducción histórica o una nueva prestación exige revisión. La actualización de datos no habilita correo a suscriptores: difusión únicamente por orden editorial independiente.

La configuración queda en la rama del PR. **No está activa en producción mientras el PR permanezca sin fusionar.** No se ejecutó ningún workflow de escritura.

## Validación reproducible

```
python scripts/test_limpieza_urbana.py
python scripts/actualizar_limpieza_urbana.py --local --directory /ruta/con/csv-completos
node --check deploy/site-overlay/assets/limpieza-urbana.js
```

Las pruebas cubren unicidad, duplicados incompatibles, prestaciones desconocidas, correspondencia territorial, cobertura, sumas, regresión y preservación de la descarga anterior ante una respuesta incompleta o parcial. La generación con los CSV completos pasó los controles; la segunda ejecución sin cambios conservó los agregados.

## Revisión visual

Se intentó primero `sites-preview` con todos los recursos. Falla al iniciar: `bwrap: Can't mount proc on /newroot/proc: Operation not permitted`. El navegador integrado tampoco accede al HTTP local (`ERR_CONNECTION_REFUSED`). Se usó una vista autónoma del candidato, fuera de producción, mediante RawGitHack y cua_repl. La inspección de la versión inicial detectó una falta de contraste en el título y una discrepancia entre barrio/comuna; se corrigieron.

`experiments/limpieza-urbana/index.html` contiene la vista autónoma actual. `?viewport=390` presenta el mismo contenido dentro de un iframe de 390 px para verificar el quiebre móvil real. Los enlaces de navegación conducen al sitio público; el módulo y sus datos están incluidos en el propio archivo para la revisión. Es una vista de revisión, no un release para reemplazar el árbol productivo.

Revisión del candidato oficial: render real en escritorio y en iframe de 390 px comprobado con cua_repl; mapa de 48 barrios, filtros de quejas, tema, comuna y período comprobados contra los agregados. Casos: 159.612 quejas del archivo completo; 1.893 quejas de barrido/limpieza en comuna 7 (Flores 1.067 y Parque Chacabuco 826); 12.015 contactos en octubre parcial. Ancho móvil observado: 373 px de contenido dentro del iframe de 390, con scrollWidth de 373, sin desbordamiento de página. No es una prueba táctil en teléfono real. Los controles remotos de contraste y R2 del commit 969b8ff pasaron.

Pendiente de cierre: repetir la revisión de los ajustes finales y validar la integración completa en el árbol público canónico antes de publicar. La vista se reproduce con `python experiments/limpieza-urbana/build_preview.py --site /ruta/salida-publica`. Mantener en borrador hasta completar ese cierre y aprobar su publicación.


## Revisión de comparabilidad — 16/10/2026

La versión 3 de los agregados conserva `cantidad` en la posición 5 y añade `naturaleza` en la posición 6. El filtro principal utiliza el motivo estable, definido prestación por prestación en `config/limpieza-prestaciones.json`: 290.795 problemas reportados, 567.441 servicios solicitados y 225 otros contactos. La etiqueta original permanece en opciones avanzadas. Estas categorías describen contactos y no prueban fallas, personas únicas ni resolución efectiva.

Se identificaron tres interrupciones: Mejora de barrido y Reubicación de contenedor (último registro 14/05/2026), y Vereda sucia por mascotas (12/05/2026). No se encontró explicación oficial. Los meses afectados se marcan en gráfico y tabla; una consulta afectada sin registros muestra cobertura no disponible. Ocho motivos cambian de tipo administrativo predominante entre los archivos 2025 y 2026; se documentan en el detalle público y se advierten las comparaciones filtradas por tipo original.

La comprobación semanal rechaza prestaciones desconocidas, nuevas interrupciones sin revisar y retrocesos históricos. Los controles JavaScript verifican que mapa, serie y filtros compartan el mismo universo y que una interrupción no se presente como cero problemas. La portada añade tres claves de lectura y una agenda verificable sobre recorridos, resolución y recursos. Dictamen de datos: apto con reservas explícitas de cobertura, sin inferencias de mejora en los tramos interrumpidos.
