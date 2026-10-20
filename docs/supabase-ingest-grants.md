# Permisos explícitos de ingesta para instalaciones nuevas

Fuente oficial consultada el 20/10/2026: [Supabase, discusión 45329](https://github.com/orgs/supabase/discussions/45329).
El anuncio prevé aplicar los nuevos defaults a proyectos existentes el 30/10/2026.
Las tablas existentes conservan sus grants; las tablas nuevas en `public` necesitan
permisos explícitos para la Data API. RLS continúa funcionando por separado.
Esto también afecta a `service_role`: omitir RLS no sustituye los privilegios de tabla.
No se ha demostrado una caída actual por este cambio.

## Contrato verificado en código

| Tabla | Consumidor | Permisos necesarios |
|---|---|---|
| `expediente_analyses` | `legislative-analysis-ingest-v2/index.ts` | SELECT para consultas de identidad, duplicados, versión y retorno del INSERT; INSERT para crear versiones; UPDATE para desmarcar `is_current` de versiones anteriores |
| `press_notes` | `press-draft-ingest/index.ts` | SELECT para comprobar hash y slug; INSERT para borradores nuevos; los duplicados se omiten |

Ambas funciones construyen el cliente de backend con la clave de servicio.
No requieren DELETE; prensa tampoco requiere UPDATE. Los IDs son UUID y no
requieren permisos sobre secuencias. El foco ya tiene SELECT explícito para
`service_role` en `005_focus_analisis_rls.sql`.

## Instalación y recreación

Los grants se incorporan a `infra/supabase/legislativa.sql` y
`infra/supabase/008_prensa_editorial.sql`, junto a los permisos existentes.
Se mantienen intactos los grants de anon/authenticated, las políticas y los triggers.
No se agrega una migración de reparación para bases existentes ni se cambian defaults.

En una instalación nueva, usar los scripts de estructura y sus dependencias
habituales incluyendo estas versiones corregidas. Si un procedimiento autorizado
recrea una tabla, debe restaurar también sus grants, RLS, políticas y triggers:
restaurar sólo CREATE TABLE resulta insuficiente. Estos scripts históricos no son
reentrantes (hay CREATE POLICY/INDEX sin guardas); no volver a ejecutarlos sobre una
instalación existente como método de parcheo. La prueba siguiente es un fixture
reducido de las dependencias de ambas ingestas, no un instalador completo de CEPOES.
El despliegue web no aplica estos scripts SQL.

## Pruebas reproducibles sin secretos

Desde la raíz del repositorio:

```sh
python -m unittest discover -s tests -p test_supabase_ingest_grants.py -v
python verificar_area_legislativa.py
python verificar_analisis_automatico.py
git diff --check
```

La comprobación estática se agrega al workflow existente
`validar-area-legislativa.yml`; verifica los grants exactos, su correspondencia
con las operaciones actuales y que omisiones o permisos excesivos sean detectados.
No conecta a Supabase. No constituye una prueba de ejecución PostgreSQL/PostgREST.

La prueba SQL carga los scripts reales, sin grants predeterminados de tablas,
simula los roles y `auth.uid()` y prueba operaciones permitidas, denegadas y RLS.
Para ejecutarla se necesita PostgreSQL con pgcrypto **ya instalado y autorizado**.
Como usuario local no root, en un entorno descartable, con los binarios en PATH:

```sh
set -eu
fixture_dir=$(mktemp -d /tmp/cepoes-grants.XXXXXX)
trap 'pg_ctl -D "$fixture_dir/data" -m immediate stop >/dev/null 2>&1 || true; rm -rf "$fixture_dir"' EXIT
initdb -D "$fixture_dir/data" -U postgres --auth=trust
pg_ctl -D "$fixture_dir/data" -o "-c listen_addresses='' -k $fixture_dir" -w start
psql -X -h "$fixture_dir" -U postgres -d postgres -v ON_ERROR_STOP=1 -f supabase/tests/ingest_grants.sql
```

El socket está dentro de un directorio temporal privado y TCP está deshabilitado.
La prueba rechaza clústeres con roles Supabase, esquema auth, tablas públicas o
default ACL preexistentes; los objetos y datos sintéticos se revierten con ROLLBACK.
Nunca apuntar este archivo a producción. No usa tokens, red ni datos reales.
No prueba HTTP, OIDC ni el runtime de las Edge Functions.

## Resultado de la preparación previa a la incorporación

Base inicial: `9c7f28e349d69dee71fc5c53f423aa8756261e8e` (main confirmado en GitHub).
Antes de abrir el PR se incorporó el main `7e855a9ca7c3ca4b90bbaea71693ffe83255bf43`,
sin conflictos ni cambios concurrentes en los archivos de esta corrección.
Las pruebas estáticas y la prueba PostgreSQL completa volvieron a pasar sobre esa base.
Las tres pruebas unittest y ambos verificadores estáticos pasaron; `git diff --check`
pasó. Se comprobó además que retirar las dos adiciones de los scripts produce
exactamente el SQL original, preservando permisos y RLS anteriores.
La ejecución SQL pasó en PostgreSQL **17.11 (Debian 17.11-0+deb13u1)**,
x86_64, con pgcrypto, en un clúster temporal vacío sin TCP. Se comprobaron los
privilegios exactos, SELECT/INSERT/UPDATE de análisis, SELECT/INSERT de prensa,
rechazo de DELETE en ambas tablas y de UPDATE en prensa, y aislamiento por RLS
para anon y authenticated sin perfil activo. Al terminar el ROLLBACK quedaron
cero roles de fixture y cero esquemas auth/private; el clúster se detuvo y eliminó.

También se ejecutaron dos controles negativos en copias temporales: retirar el
grant de análisis o el de prensa hace fallar la prueba real con `Grant incorrecto`
para la tabla correspondiente (psql exit 3). No se modificó el SQL del repositorio
para esos controles. No aparecieron defectos en la prueba ni en los grants.

La instalación fue autorizada exclusivamente para este entorno descartable.
Se descargaron `postgresql-17`, `postgresql-client-17` y `libpq5`, versión
`17.11-0+deb13u1`, de `https://deb.debian.org/debian`, suite trixie/main,
mediante APT con verificación de InRelease por el keyring oficial de Debian
(`/usr/share/keyrings/debian-archive-keyring.pgp`), sin permitir repositorios
inseguros. Los paquetes se extrajeron con `dpkg-deb -x` bajo
`/tmp/cepoes-postgresql`; índices y configuración APT también fueron temporales.
No se ejecutaron scripts de instalación del sistema ni se creó un servicio.
La distribución Debian es una vía oficial indicada por
[PostgreSQL](https://www.postgresql.org/download/linux/debian/).
Un intento previo de descarga de fuentes desde ftp.postgresql.org devolvió HTTP
403 y no instaló nada; la vía Debian completó la instalación y la validación.

Para reproducir con esos binarios extraídos, anteponer a los comandos anteriores:

```sh
export PATH=/tmp/cepoes-postgresql/usr/lib/postgresql/17/bin:$PATH
export LD_LIBRARY_PATH=/tmp/cepoes-postgresql/usr/lib/x86_64-linux-gnu
```

Los resultados validan privilegios PostgreSQL, no la integración HTTP/PostgREST,
OIDC o el runtime de las Edge Functions, ni una versión de producción desconocida.
No se usaron datos ni credenciales de producción. No se ejecutaron Actions,
SQL en producción, push, PR, merge ni despliegue.
