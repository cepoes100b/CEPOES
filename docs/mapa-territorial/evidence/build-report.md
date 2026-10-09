# Verificación local: mapa territorial CEPOES

Resultado del 9 de octubre de 2026, 02:37 UTC: **build público completo e
integración aislada validados localmente**. No hubo publicación ni escritura
externa. No se ejecutaron workflows, SFTP, custodia privada, DNS, analítica,
suscripción ni difusión.

## Identidad y alcance

- Checkout canónico: `f7e0f1a462ce7666675240ad1aa25b3fc66affd9`.
- SHA observado en el marcador público:
  `2307ecf17742bc25db91a10d5b362f849e295da9`.
- Run publicado: `37866848864`, intento 1, repositorio `cepoes100b/CEPOES`.
- El marcador fue idéntico antes y después de la captura.
- Las tres huellas públicas coincidieron exactamente:
  - Portada: 22.479 bytes;
    `08d8c27f8f53e6398045167356b28eb155a259fc13d11d95815bab9d9071dc3c`.
  - Estado de los datos: 10.627 bytes;
    `985b0a7d70f420c9892b1e7755ab39ea1a0842f1627c271e9431793d27c9e62b`.
  - Panorama productivo: 9.783 bytes;
    `5daf8031557b6e6340389a535d245c252d93d0ac216acf2646cc237f3051ad2f`.

La captura está basada en [sitemap público](https://cepoes.org/sitemap.xml),
[marcador público](https://cepoes.org/.well-known/cepoes-release.json) y recursos
públicos enlazados. Los insumos canónicos y el overlay provienen del checkout.
Los hashes de los archivos del prototipo identifican sus bytes exactos del árbol
de trabajo; no se presume que todos estuvieran ya confirmados en ese SHA.

## Salidas conservadas

- `base-public/`: 338 archivos únicos, 15.093.809 bytes y 167 HTML obtenidos
  mediante 362 respuestas públicas. Están las 151 rutas del sitemap.
- `canonical-baseline/`: 378 archivos, 78.767.786 bytes y 168 HTML.
- `candidate/`: 396 archivos, 84.253.397 bytes y 169 HTML.
- Ambas salidas construidas conservan los 48 barrios y 151 URLs indexables.

La base pública es una captura acotada por HTTPS, **no un respaldo SFTP privado**
ni una copia íntegra de producción. No se leyó ni copió ningún archivo privado
de Drive. No se conoce ni reproduce el `.htaccess` privado del servidor.

## Pruebas ejecutadas

Pasaron los 19 pasos del build canónico público, incluidos:

- Deuda pública: 3 períodos, último 2026-08.
- Índice ciudadano: 20.564 registros de 59 fuentes.
- Búsqueda global: 157 URLs canónicas; 34/34 consultas de verificación correctas.
- Estado de los datos: 6 fuentes críticas.
- Catálogo editorial: 7 tests; 12 informes, últimos 5 en Publicaciones.
- Lo nuevo: 10 tests; 148 contenidos públicos.
- Feed editorial: 22 publicaciones.
- Publicación canónica, contraste crítico, R1 y validador completo del sitio.

Pasaron además los 6 pasos de integración: normalización exclusiva del HTML del
prototipo y nueva ejecución de los cinco validadores públicos. El validador
completo informó: **169 HTML, 48 barrios, 151 URLs indexables, sin crudos**.
El helper reproducible tiene 4 tests de alcance HTTPS, rutas y referencias, y
pasó compilación de sintaxis.

## Aislamiento del prototipo

Se agregaron exclusivamente 18 archivos bajo:

- `laboratorio/mapa-territorial/`
- `assets/mapa-territorial/`

**Ninguno de los 378 archivos previos cambió.** La página nueva conserva
`noindex`; la navegación, footer, fuentes y revisiones CSS se incorporaron
mediante `normalize_html` aplicado solamente a ese HTML.

Durante esa integración no se reejecutó el normalizador completo ni se
regeneraron feeds o búsqueda. Sitemap XML/TXT, índice de búsqueda, Lo nuevo,
newsletter-publications, newsletter-editions y newsletter-config mantuvieron
exactamente los hashes de la base. La ruta del prototipo no está en ellos.

La comprobación de referencias literales en HTML/CSS/JS/MJS no encontró archivos
públicos locales faltantes. Esto no representa una auditoría de todas las URLs
contenidas en datasets, ni de URLs construidas por JavaScript en ejecución.

## Fallas y limitaciones registradas

1. La primera construcción se detuvo porque HEAD avanzó de `ddefe51` a
   `f7e0f1a` mientras se descargaba la base. Se verificó el nuevo SHA y se ejecutó
   nuevamente el build; todas las etapas posteriores pasaron.
2. Dos constantes JS de directorios de assets produjeron HTTP 403:
   `/assets/data/estructura-productiva/` y `/assets/data/endeudamiento/`.
   No se reintentaron por otra vía. La versión final del helper excluye esas
   constantes del rastreo; los archivos reales requeridos están presentes.
3. Un enlace mal formado ya presente en datos públicos produjo HTTP 404:
   `/www.deljurista.com/`. Quedó registrado como defecto de origen; no fue
   corregido ni ocultado mediante contenido sustituto.
4. Las CDN externas, rutas no enlazadas y URLs calculadas en ejecución no se
   espejaron. La captura no es una garantía de archivo exhaustivo de todo el host.
5. Esta verificación no sustituye pruebas visuales/interactivas del mapa,
   control de consola/red del navegador ni un smoke de publicación. El sitio
   siguió sin publicar.

## Segundo ensayo del helper final

Se repitieron los 19 pasos del build y 6 de integración en una salida separada;
todos pasaron y la base canónica fue idéntica byte a byte. Durante ese intervalo
cambiaron tres insumos del prototipo: `app.mjs`, `data/audit.json` y
`data/manifest.json`. La salida `repro-check/candidate/` incorpora esos cambios;
`candidate/` se mantuvo intacta para no interferir con la revisión de navegador.
La evidencia está en `evidence/reproducibility-check.json`. Tras nuevas
correcciones del prototipo, reintegrar antes de la verificación final.

## Evidencia y repetición

- `README.md`: comandos portables y límites.
- `build_public_local.py`: captura, build y reintegración offline.
- `test_build_public_local.py`: tests del helper.
- `verification.json`: resumen portable, sin rutas absolutas del entorno.
- `evidence/*checksums.json`: inventarios SHA-256 de captura, base, candidato,
  insumos del prototipo y archivos de entrega.
- `evidence/build-steps.json`, `evidence/integration-steps.json` y `logs/`:
  comandos completos y resultados locales.

Próximo paso: revisión visual e interactiva del candidato local en escritorio y
móvil. Si se corrige el prototipo, repetir sólo `--mode integrate` y esas pruebas.
