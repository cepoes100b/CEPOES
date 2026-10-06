# Despliegue CEPOES → Hostinger

Esta capa automatiza la publicación del sitio sin convertir el repositorio de datos en un espejo de `public_html`.

## Cómo funciona
1. GitHub Actions descarga por SFTP la versión que está en producción y la conserva como rollback.
2. Aplica los archivos versionados en `deploy/site-overlay/`.
3. Valida estructura, sitemap, 48 barrios, favicon y ausencia de microdatos.
4. Empaqueta la producción anterior y el candidato exacto, rechaza archivos sensibles y genera hashes y manifiesto de release.
5. Conserva el release en un paquete privado de GitHub Container Registry antes de escribir en producción. La política exige al menos 90 días y las últimas 10 publicaciones.
6. Sincroniza la versión validada con Hostinger.
7. Ejecuta smoke tests sobre las rutas principales.
8. Si la publicación o el smoke test fallan después de subir, restaura el respaldo anterior.
9. Si todo queda verde, notifica las URLs del sitemap a IndexNow.

## Ensayo de restauración

`Ensayar restauración durable` recibe el run ID, intento, commit y digest de un despliegue canónico exitoso. Descarga por digest su release desde el paquete privado, verifica identidad y hashes, restaura `before` o `candidate` en un runner efímero y ejecuta los validadores del sitio. No usa secretos SFTP, no referencia el entorno `production` y no escribe en Hostinger. El acta JSON del ensayo —sin contenido del sitio— se conserva durante 90 días.

El workflow comprueba la privacidad de `cepoes-durable-backups` de forma efectiva: una descarga anónima debe ser rechazada por autenticación y la misma imagen por digest debe descargarse con el token del workflow. Si cualquiera de las dos pruebas falla, aborta antes de toda escritura SFTP. El digest inmutable necesario para el ensayo queda registrado en el resumen del run.

La restauración real sobre producción permanece deshabilitada. Habilitarla requiere autorización específica, revisión del destino y una publicación controlada.

## Configuración única en GitHub
En **Settings → Secrets and variables → Actions** cargar como *Repository secrets*:
- `HOSTINGER_SFTP_HOST`
- `HOSTINGER_SFTP_PORT` (si se omite se usa 65002)
- `HOSTINGER_SFTP_USER`
- `HOSTINGER_SFTP_PASSWORD`
- `HOSTINGER_REMOTE_DIR` (directorio `public_html` de `cepoes.org` visto por SFTP)

Luego crear la *Repository variable*:
- `HOSTINGER_DEPLOY_ENABLED` = `true`

Mientras esa variable no sea `true`, los pushes no despliegan. El workflow puede probarse manualmente desde Actions.

## Publicar cambios web
Los archivos colocados bajo `deploy/site-overlay/` reproducen la ruta que tendrán en `public_html`.
Ejemplo: `deploy/site-overlay/assets/site.css` → `public_html/assets/site.css`.

`deploy/delete-paths.txt` permite registrar borrados relativos de forma explícita. No acepta rutas absolutas ni `..`.

Esta arquitectura es una etapa de transición segura. A futuro puede migrarse el sitio completo al repositorio, pero ya elimina la necesidad de subir ZIP para cambios versionados.

El procedimiento operativo, los objetivos de recuperación y las evidencias exigidas están en [`docs/seguridad/procedimiento-restauracion-r2.md`](../docs/seguridad/procedimiento-restauracion-r2.md).


## Catálogo editorial

Los informes se integran desde `deploy/reports-registry.json`; el publicador genera el archivo completo y los últimos cinco de Publicaciones. Los boletines ingresan automáticamente en Lo nuevo. Ver [contrato y verificación](../docs/publicaciones-catalogo.md).

## Encadenamiento automático y SHA publicado

Los commits hechos con `GITHUB_TOKEN` no generan otro evento `push`. El publicador
canónico escucha además `workflow_run` de una lista fija de dieciséis productores:
Observatorio (`actualizar.yml`), Territorio, Presupuesto, Legislatura, Panorama
actual, Estructura productiva, Descentralización, Dinámica productiva, Migraciones,
Natalidad, Personas Mayores, Salud Mental, Salud Reproductiva, los dos validadores
manuales de Legislatura y Presupuesto, y Endeudamiento. Los IDs, nombres, rutas y eventos autorizados
están en `producer-workflows.json`; se verificaron contra GitHub el 6/10/2026.
No se agregan credenciales ni permisos Actions al publicador.

Cada productor conserva en trailers el workflow, run, intento y SHA de entrada.
Después del push registra su SHA definitivo, incluido cualquier rebase. La
selección sólo acepta eventos exitosos del mismo repositorio y de `main`, entrada
ancestral y un commit directo único con esos trailers y cambios en
`publication-inputs.json`. Un trailer aislado no autoriza la publicación. Runs
fallidos, PR/fork, otras ramas, diagnósticos y ausencia de cambios no publican.

El preflight sin secretos queda fuera del mutex de producción y no lee el
marcador, para no observar una subida todavía pendiente de smoke o rollback.
Sólo las selecciones con cambios encolan el job de escritura. Bajo el mutex se vuelve a
leer main y el marcador público, se fija `DEPLOY_SHA` y se hace checkout exacto.
Esto evita que un no-op desplace un despliegue pendiente, y que selecciones lentas
publiquen una instantánea vieja. Un evento ya consumido sólo puede publicar otra
vez si main tiene un SHA distinto con nuevas entradas publicables respecto de
producción; los duplicados reales terminan sin SFTP.

El SHA construido, que puede diferir del SHA del evento, identifica tanto el
manifiesto durable como la revisión OCI y `/.well-known/cepoes-release.json`.
Este marcador público contiene únicamente identidad y huellas de portada,
Estado de los datos y panorama actual. El smoke exige los mismos bytes del
candidato en esas tres rutas; rechaza redirecciones y respuestas HTML/JSON
obsoletas aunque el HTTP sea 200. El primer despliegue acepta la ausencia del
marcador únicamente con HTTP 404; errores de red, otro HTTP o contenido inválido
bloquean. La lectura SFTP del respaldo debe coincidir con la producción observada.
No se publican el inventario ni los archivos del respaldo privado.

### Frescura de las rutas canónicas

Antes de cualquier sondeo con nonce, el smoke compara los bytes del marcador,
portada, Estado de los datos y panorama en sus URLs canónicas, sin query string
ni encabezados de petición que fuercen revalidación. Luego conserva el control
con nonce. Una respuesta canónica obsoleta hace fallar el despliegue y activa el
rollback existente; un nonce correcto no alcanza para declarar éxito.

El preparador añade a `.htaccess` una sección idempotente de revalidación sólo
para `/`, `/index.html`, `/datos/estado/`, `/datos/estado/index.html`,
`/assets/data/estructura-productiva/actual.json` y el marcador público.
Emite `Cache-Control: no-cache, max-age=0, must-revalidate`, conservando el resto
del archivo, las rutas privadas y las políticas de los demás assets. No purga
la CDN ni cambia cuentas o permisos. El smoke exige esas tres directivas por HTTP
al publicar: no elimina retroactivamente copias ya almacenadas en navegadores o
intermediarios que todavía no consultan al servidor. Si persisten, se debe
diagnosticar esa capa y usar sólo un mecanismo de invalidación autorizado.

Se conserva la custodia privada por digest, los gates y el rollback; éste también
cubre subidas parcialmente fallidas. Si el respaldo legacy carecía de marcador,
la restauración elimina sólo ese marcador nuevo. El ensayo durable verifica el
intento exacto, su origen canónico, la ancestría en main, la revisión OCI y el
manifiesto; no confunde `head_sha` del evento con el SHA construido.

### Cobertura de productores y límites de las entradas

Los dieciséis productores registran identidad después de validar, conservan los
trailers ante rebase y registran el SHA final después del push exitoso. Los diez
productores de la segunda incorporación sólo escriben en `main`; las validaciones
de PR y otras ramas continúan disponibles sin producir commits publicables.
Los dos validadores manuales sólo admiten `workflow_dispatch`. Dinámica
productiva conserva el diagnóstico de error y termina fallida aunque la escritura
se omita por tratarse de otra rama. El [inventario de identidades y salidas](../docs/seguridad/productores-publicacion.md)
registra evidencia, eventos admitidos y salidas secundarias fuera del manifiesto.

Endeudamiento agrega exclusivamente `datos/endeudamiento/manifest.json` y archivos
mensuales con nombre `AAAA-MM.json` y mes válido. Antes de versionar y antes del
build se comprueba el esquema agregado completo, sus 48 barrios, segmentos
numéricos, filtros y rutas. El staging se limita al manifest y al último período
validado. La matriz territorial, diagnósticos, padrones, archivos comprimidos y
microdatos quedan fuera. No se incorpora una copia de la carpeta al sitio ni se
modifica la metodología o el mapa: el consumidor existente sigue siendo la portada.

`diagnostico_presupuestario.json` se incorpora como ruta explícita: contiene
agregados institucionales y comunales ya usados por el hub de Presupuesto. El
cambio aislado de este archivo dispara el build desde ambos productores
presupuestarios, después de sus verificaciones existentes. No se modifica el
diagnóstico, su método ni los textos que el preparador ya genera. Una prueba
revisa las lecturas JSON directas del preparador y Estado de los datos para
impedir que una nueva dependencia quede fuera del manifiesto. El inventario
explica por qué las salidas secundarias restantes no son entradas directas.

Verificación offline: `python -m unittest test_cadena_publicacion.py test_endeudamiento_publico.py` y
`python validar_rollback_durable.py`. R2 también verifica el endpoint público del
marcador, por separado de los tests offline y sin secretos. La detección sustantiva
del panorama ignora sólo `generado` y `fuentes.*.extraido`; un no-op restaura los
bytes previos completos, conservando hashes, URLs, períodos y datos como criterios
de cambio.

## Panorama y transporte verificable

El panorama C2 fue generado por el workflow autorizado y su commit con
`GITHUB_TOKEN` se publica por `workflow_run`, sin producir otro evento `push`.
El CLI canónico y el generador usan ahora el mismo `estructura_actual_schema.py`;
ninguna salida nueva puede omitir sus controles de fuentes, períodos y conteos.
La interfaz usa las tasas y períodos del asset servido.

Salud Mental conserva su frecuencia y método. Se eliminan los dos bypass TLS
preexistentes: todas las descargas y redirecciones deben usar HTTPS con
certificados y hostname verificados. Errores de TLS o transporte abortan antes
de escribir ambos JSON, sin activar una publicación. El fallback de esquema del
contraste DEIS no absorbe esos errores. Los tests offline prueban preservación
byte a byte. Una comprobación segura del CKAN el 6/10/2026 a las 17:11 UTC obtuvo
HTTP 502; eso no verifica disponibilidad de la fuente ni autoriza omitir TLS.

La CI también ejecuta `test_cache_publicacion_apache.py` con el paquete oficial
`apache2-bin`, sin privilegios y con configuración temporal limitada a
`127.0.0.1`. Verifica DirectoryIndex, las seis variantes de URL pública, siete
controles, reglas previas e idempotencia. No inicia servicios globales. La
compatibilidad efectiva del hosting se comprueba nuevamente al publicar.
