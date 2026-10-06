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
canónico escucha además `workflow_run` de una lista fija de seis productores:
Observatorio (`actualizar.yml`), Territorio, Presupuesto, Legislatura, Panorama
actual y Estructura productiva. Los IDs, nombres, rutas y eventos autorizados
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

Se conserva la custodia privada por digest, los gates y el rollback; éste también
cubre subidas parcialmente fallidas. Si el respaldo legacy carecía de marcador,
la restauración elimina sólo ese marcador nuevo. El ensayo durable verifica el
intento exacto, su origen canónico, la ancestría en main, la revisión OCI y el
manifiesto; no confunde `head_sha` del evento con el SHA construido.

### Inventario y límite de esta primera incorporación

Otros nueve workflows también escriben rutas incluidas en las entradas de
publicación: `descentralizacion-comunas.yml`, `dinamica-productiva.yml`,
`migraciones.yml`, `natalidad.yml`, `personas-mayores.yml`, `salud-mental.yml`,
`salud-reproductiva.yml`, `validar-legislatura.yml` y `validar-presupuesto.yml`.
Sus salidas se incorporan al siguiente build canónico de main, pero sus commits
con `GITHUB_TOKEN` todavía no disparan automáticamente una publicación. Ampliar
la lista exige agregar/verificar su identidad y trailers con los mismos tests.
`endeudamiento-mensual.yml` escribe `datos/endeudamiento/`, que no está incluido en
el manifiesto actual; no se amplía ese contrato en esta reparación.

Verificación offline: `python -m unittest test_cadena_publicacion.py` y
`python validar_rollback_durable.py`. R2 también verifica el endpoint público del
marcador, por separado de los tests offline y sin secretos. La detección sustantiva
del panorama ignora sólo `generado` y `fuentes.*.extraido`; un no-op restaura los
bytes previos completos, conservando hashes, URLs, períodos y datos como criterios
de cambio.
