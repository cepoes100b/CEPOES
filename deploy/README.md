# Despliegue CEPOES → Hostinger

Esta capa automatiza la publicación del sitio sin convertir el repositorio de datos en un espejo de `public_html`.

## Cómo funciona
1. GitHub Actions descarga por SFTP la versión que está en producción y la conserva como rollback.
2. Aplica los archivos versionados en `deploy/site-overlay/`.
3. Valida estructura, sitemap, 48 barrios, favicon y ausencia de microdatos.
4. Sincroniza la versión validada con Hostinger.
5. Ejecuta smoke tests sobre las rutas principales.
6. Si la publicación o el smoke test fallan después de subir, restaura el respaldo anterior.
7. Si todo queda verde, notifica las URLs del sitemap a IndexNow.

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
