# CEPOES: captura pública y prototipo territorial local

Este ensayo no publica ni escribe en servicios externos. Sólo descarga recursos
públicos de `https://cepoes.org` mediante GET HTTPS y genera archivos locales.
No consulta SFTP, privados, login, suscriptores, APIs autenticadas ni Drive.

## Directorios y evidencia

- `base-public/`: captura HTTPS acotada del sitemap y sus dependencias públicas.
  **No es** un respaldo SFTP, una imagen íntegra de `public_html` ni un rollback.
- `pipeline-source/`: copia aislada de insumos del checkout para ejecutar el
  pipeline sin modificar el repositorio fuente. Excluye el overlay privado,
  crudos de endeudamiento y las dos capas grandes que el índice ya excluye.
- `canonical-baseline/`: salida pública validada, sin el prototipo.
- `candidate/`: salida pública con el prototipo aislado, tras `integrate`.
- `evidence/`: marcador público, hashes por archivo, resultados y fallas.
- `logs/`: salida completa de cada comando canónico e integración.

La captura rechaza rutas privadas/API/login/suscriptores, credenciales en URL y
redirecciones fuera del mismo origen HTTPS. No evalúa JavaScript ni rastrea CDN
externas. Las constantes de directorio de assets tampoco se descargan. Las
fallas nunca se reemplazan por archivos vacíos. No se usa un respaldo privado.

Las dos carpetas presupuestarias históricas que necesita el normalizador se
conservan cuando son respuestas públicas; sus redirecciones quedan registradas.
Si faltan, el script crea alias exclusivamente locales de sus rutas canónicas,
con procedencia explícita. El `.htaccess` es generado por el preparador público:
no reproduce reglas privadas del hosting. Este resultado es para vista previa
estática y no debe reemplazar producción.

## Reproducir desde el checkout

Requiere Python 3. El capturador y los pasos ejecutados usan biblioteca estándar.
Los comandos asumen que estos dos scripts se versionaron en
`experiments/mapa-territorial/scripts/`; ajustar `BUILDER` si se elige otra ruta.

```bash
REPO=$(git rev-parse --show-toplevel)
BUILDER="$REPO/experiments/mapa-territorial/scripts/build_public_local.py"
OUT="${TMPDIR:-/tmp}/cepoes-mapa-local"
SHA=$(git -C "$REPO" rev-parse HEAD)
python "$BUILDER" --repo "$REPO" --output "$OUT" --expected-sha "$SHA" --mode all
python "$BUILDER" --repo "$REPO" --output "$OUT" --expected-sha "$SHA" \
  --mode integrate --prototype-dir "$REPO/experiments/mapa-territorial/public"
python "$REPO/experiments/mapa-territorial/scripts/test_build_public_local.py"
```

Para una captura nueva usar un `OUT` nuevo. Una captura existente es inmutable:
`all` verifica sus hashes; `build` e `integrate` no hacen tráfico de red.
`--mode build` reconstruye y reemplaza las salidas locales y la base canónica.
`--mode integrate` restaura el candidato desde esa base, copia sólo las dos
carpetas del prototipo y normaliza exclusivamente su HTML. Es seguro repetir
esta integración cuando cambien código o datos del prototipo.

El SHA esperado detiene una carrera si cambia HEAD. Los hashes de los insumos
registran también el contenido exacto del árbol de trabajo. Los generadores
canónicos usan la fecha del sistema: repetir los mismos pasos en otro día puede
cambiar bytes de metadatos. Se conservan los hashes exactos de cada ejecución.

## Pipeline canónico

El build sigue los pasos públicos de `desplegar-hostinger.yml`: agregados de
deuda; índice de equipamientos; overlay y borrados explícitos; Legislatura;
búsqueda; Estado de los datos; ajuste institucional; normalizador; puentes;
pruebas/generadores de catálogo y Lo nuevo; feed editorial; y validadores de
publicación canónica, contraste, búsqueda, R1 y sitio completo.

La integración del prototipo ocurre **después** de ese build:

1. Verifica hashes de la base y que el preparador/validadores no cambiaron.
2. Copia sólo `laboratorio/mapa-territorial/` y `assets/mapa-territorial/`.
3. Ejecuta `normalize_html` solamente en el nuevo `index.html`, que debe tener
   `noindex`, conservando sin cambios el resto del sitio.
4. Ejecuta nuevamente todos los validadores públicos completos.
5. Exige cero cambios en los archivos de la base, cero nuevas rutas en feeds o
   buscador y cero referencias públicas literales faltantes.

No regenera feeds/búsqueda durante la integración. No crea un marcador falso de
release publicado ni ejecuta custodia OCI, deploy, SFTP, smoke de publicación,
IndexNow o reglas privadas. El desafío público de IndexNow se conserva porque
lo exige el validador; no se utiliza para notificar URLs.

## Leer el resultado

`REPORT.md` resume esta ejecución. `evidence/build-summary.json` registra el
build sin prototipo; `evidence/integration-summary.json`, el candidato integrado.
Una falla sólo puede darse por resuelta mediante un resultado posterior válido.
Consultar `evidence/failure.json` y los logs si no hay resumen exitoso posterior.
