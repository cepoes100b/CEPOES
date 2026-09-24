# Procedimiento de respaldo y restauración R2-A4

## Alcance y estado

Cada ejecución canónica que llega a producción conserva dos estados exactos:

- `before`: copia de la producción anterior a la publicación;
- `candidate`: sitio validado que se publicará.

Ambos estados se comprimen de forma determinista, se inventarían archivo por archivo y se acompañan con hashes SHA-256. La custodia se realiza como una imagen OCI en el paquete privado `cepoes-durable-backups` de GitHub Container Registry (GHCR). El workflow aborta antes de SFTP si la API de GitHub no confirma visibilidad `private`.

La restauración sobre Hostinger permanece deliberadamente deshabilitada. El workflow disponible restaura únicamente en un runner efímero y no recibe secretos SFTP ni acceso al entorno `production`.

## Objetivos y retención

| Control | Objetivo |
|---|---|
| RPO | una publicación canónica |
| RTO | hasta 60 minutos desde la decisión de restaurar |
| Retención mínima | 90 días |
| Versiones mínimas | últimas 10 publicaciones |
| Borrado | manual, sólo cuando se cumplen simultáneamente ambos mínimos |

No existe una limpieza automática en esta etapa. La ausencia de borrado es conservadora para recuperación, aunque el consumo y costo de almacenamiento deben revisarse periódicamente antes de automatizar una política destructiva.

## Identidad de cada release

La etiqueta de la imagen es `<run_id>-<run_attempt>`. El manifiesto incluido registra:

- repositorio, commit, run e intento;
- fecha UTC;
- objetivo RPO/RTO y política de custodia;
- altas, modificaciones y bajas respecto de producción;
- nombre, tamaño y SHA-256 de cada archivo comprimido;
- inventario, tamaño y SHA-256 de cada archivo del sitio.

El resumen del run de despliegue registra además la referencia OCI completa con digest. Para ensayar una restauración deben usarse juntos el run ID, intento, commit y digest de ese mismo resumen.

## Ensayo controlado

1. Confirmar que `Desplegar sitio en Hostinger` terminó con conclusión `success`.
2. Copiar del resumen del run el run ID, intento, commit y digest `sha256:…`.
3. Ejecutar manualmente `Ensayar restauración durable` y seleccionar `before` o `candidate`.
4. El workflow verifica que el run corresponde al publicador canónico, que fue exitoso y que el commit coincide.
5. Confirma que el paquete sigue siendo privado, descarga la imagen por digest, valida los hashes y extrae el contenido con protección contra traversal.
6. Ejecuta los validadores y smoke tests locales sobre el directorio efímero.
7. Conserva durante 90 días un acta JSON sin contenido del sitio y con `production_written: false`.

Un ensayo sólo se considera satisfactorio cuando ambos jobs están verdes y el acta identifica el release, el activo restaurado, la cantidad de archivos, la duración y la ausencia de escritura en producción.

## Restauración real

La recuperación real no debe improvisarse a partir del workflow de ensayo. Requiere autorización específica, comprobación del destino SFTP, ventana de intervención y un mecanismo revisado que:

1. descargue exactamente el digest previamente ensayado;
2. vuelva a verificar manifiesto, identidad y hashes;
3. tome una nueva copia de emergencia del estado presente;
4. sincronice el estado autorizado;
5. ejecute smoke tests públicos;
6. preserve el acta y el resultado del incidente.

## Referencias de seguridad de GitHub

- [Trabajar con el Container registry](https://docs.github.com/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Configurar la visibilidad y el control de acceso de un paquete](https://docs.github.com/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility)
- [Publicar paquetes con GitHub Actions](https://docs.github.com/actions/use-cases-and-examples/publishing-packages/publishing-docker-images)
