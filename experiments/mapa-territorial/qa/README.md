# QA real del mapa territorial

Alternativa autorizada a la vista previa local bloqueada: GitHub Actions + Playwright.
El workflow no publica un sitio, no abre un puerto externo, no fusiona ramas ni
usa secretos, credenciales persistentes, SFTP, Pages, servicios de suscripción o
permisos de escritura. Se ejecuta sólo para PR internos con cambios del mapa o
manualmente; conserva R2 y el publicador sin cambios funcionales.

## Ejecutar

La ruta `QA_SITE` debe apuntar a la salida **completa** del constructor público,
con el experimento integrado y normalizado. No servir el HTML fuente aislado.

```sh
npm ci --ignore-scripts --prefix experiments/mapa-territorial/qa
cd experiments/mapa-territorial/qa
npx playwright install --with-deps chromium
QA_SITE=/ruta/al/candidato QA_OUTPUT=/ruta/a/evidencias npx playwright test --config playwright.config.mjs
```

El job usa un runner Ubuntu estándar, un worker, máximo 20 minutos, sin cache ni
artefactos almacenados. [GitHub confirma que el runner estándar es gratuito en
repositorios públicos y que los logs no consumen cuota de artefactos](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
No se autoriza ni configura gasto. Si GitHub exige cuota, detenerse.

## Qué acredita

- Chromium real ejecutando MapLibre WebGL; verifica contexto vivo, renderer,
  dimensiones y diversidad de píxeles del canvas capturado.
- Ocho combinaciones: 320/390/430/1440 px, claro/oscuro; capturas reales JPEG.
- Búsqueda por teclado, selección de mapa/selector, zoom, filtros, URL/Atrás,
  fichas, error/reintento y fallback de proveedor.
- Axe-core sobre el explorador, foco y ausencia de overflow horizontal.
- Carga diferida, transferencia observada, tiempos de mapa/filtros y heap JS.
- Muestreo de tiempos de frame durante interacción, con contexto de ejecución.

ANGLE/SwiftShader es un renderer WebGL real por software. No simula un canvas o
DOM, pero tampoco es una GPU física móvil: sus medidas no pueden presentarse
como FPS/latencia de un teléfono real. Touch se emula en Chromium; no sustituye
pruebas con dispositivo físico y lector de pantalla. Las capturas deben mirarse
además de pasar los asserts.

Los únicos endpoints permitidos en las ocho pruebas base son el servidor
loopback y Google Fonts usados por la plantilla compartida. La falla de calles
se inyecta deliberadamente para probar que sobreviva la base local. Las pruebas
no hacen peticiones a APIs privadas ni rellenan formularios de suscripción.

## Evidencia sin cuota de almacenamiento

`evidence_log.py emit` transporta únicamente JPG/JSON de primer nivel, máximo
600 KB por archivo y 5 MB totales, en líneas base64 con SHA-256. Excluye HTML,
traces, videos, cookies, headers y estado autenticado. No usa upload-artifact ni
publicación web. Sólo se incluyen vistas experimentales con datos públicos ya
autorizados del repositorio.

Descargar el log del job por la conexión oficial GitHub CEPOES y reconstruir:

```sh
python experiments/mapa-territorial/qa/evidence_log.py extract \
  --log qa-job.log --destination evidencias-recuperadas
```

La extracción falla ante nombres inseguros, chunks faltantes, tamaño excesivo o
hash distinto. Inspeccionar los píxeles de las capturas recuperadas; conservar
SHA de commit, run ID, navegador, renderer y contexto junto al resultado.

## Modalidad 3D

El runner descubre también `analysis.spec.mjs` cuando se incorpore en una rama
posterior. La modalidad debe compartir el motor, señalar readiness tras idle
real y documentar indicador/unidad/período/escala. No se declara cubierta por los
tests 2D actuales.

## Referencia interna D3

`baseline.spec.mjs` carga el mapa temático original de CEPOES dentro del mismo
candidato completo. Fija D3 7.9.0 (ISC) y sus dos fuentes públicas al snapshot del
checkout; mide render de 48 polígonos, cambio de indicador, transferencia y heap.
Los tiempos excluyen la variabilidad de descargar datos/CDN externos. Los
indicadores y funcionalidades difieren del nuevo explorador: es una referencia
interna reproducible, no una comparación equivalente ni una promesa de mejora.

## Interacciones y degradación controlada

`interaction.spec.mjs` despacha un gesto táctil real de dos dedos por CDP sobre
Chromium/MapLibre, verifica que cambien los píxeles y usa taps para seleccionar y
cerrar fichas. También verifica restauración de foco, búsqueda sin resultados y
recuperación del listado. Una prueba separada inyecta ausencia de WebGL para
comprobar que sigan operativos el selector y la tabla de los 48 barrios; esta
última es una prueba de fallo simulado, no evidencia de render.
