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
