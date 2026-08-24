# CEPOES · Área Legislativa privada

## Objetivo

Crear una capa de trabajo reservada para legisladores, asesores e investigadores autorizados sin mezclar información estratégica con el sitio público ni con los datasets públicos del repositorio.

Ruta inicial prevista: `/legislativa/`.

La ruta pública existente `/legislatura/` sigue siendo el Monitor Legislativo abierto. No se sustituye ni se mezclan sus contenidos.

## Principio de seguridad

La aplicación aplica una separación estricta de dos capas:

1. **Capa oficial/pública**: agenda, expedientes, estructura de comisiones, sesiones, sanciones y votaciones. Se obtiene de los procesos ya existentes de CEPOES y puede residir en GitHub.
2. **Capa interna**: análisis, recomendación, prioridad política, argumentos, modificaciones, preguntas para comisión, carpetas de sesión, comentarios y banco de proyectos. Reside exclusivamente en Supabase con autenticación y Row Level Security (RLS).

Una URL oculta o una contraseña en JavaScript no constituyen protección. La UI de `/legislativa/` falla cerrada si Supabase no está configurado o si el perfil no está activo.

## Roles

- `legisladora`: lectura del contenido interno y futuro acceso a comentarios/validaciones.
- `asesor`: lectura y edición de análisis, carpetas y banco de proyectos.
- `investigador`: lectura y edición de análisis técnico.
- `admin`: administración funcional y acceso completo a los registros privados.

El usuario debe existir en Supabase Auth **y** tener un registro `profiles.active = true`. Las cuentas nuevas se crean deshabilitadas por defecto.

## Componentes incorporados

### Frontend

- `deploy/site-overlay/legislativa/index.html`
- `deploy/site-overlay/assets/legislativa.css`
- `deploy/site-overlay/assets/legislativa.js`
- `deploy/site-overlay/assets/legislativa-config.example.js`

La aplicación incluye:

- login con correo y contraseña;
- validación de perfil habilitado y rol;
- dashboard de actividad próxima;
- filtros y búsqueda de expedientes oficiales;
- lectura de análisis internos;
- creación y edición de análisis para roles autorizados;
- carpetas de sesión;
- banco de proyectos;
- indicador visible de uso interno;
- `noindex`, `nofollow`, `noarchive` y `nosnippet`.

### Base privada

`infra/supabase/legislativa.sql` crea:

- `profiles`;
- `expediente_analyses`;
- `session_briefs`;
- `session_brief_items`;
- `project_bank`;
- `internal_comments`;
- funciones de autorización;
- políticas RLS;
- triggers de auditoría temporal.

El rol `anon` no tiene privilegios sobre las tablas privadas.

## Puesta en marcha

1. Crear/conectar un proyecto Supabase para CEPOES.
2. Ejecutar `infra/supabase/legislativa.sql` en el SQL Editor.
3. Crear el primer usuario en Authentication.
4. Convertir explícitamente ese perfil en administrador y activarlo:

```sql
update public.profiles
set role = 'admin', active = true, display_name = 'Administrador CEPOES'
where id = '<UUID DEL USUARIO>';
```

5. Invitar a los demás usuarios desde Authentication y activar cada perfil con el rol correspondiente.
6. Crear `deploy/site-overlay/assets/legislativa-config.js` a partir del archivo de ejemplo con `supabaseUrl` y `supabaseAnonKey`.
7. Probar login, lectura y RLS antes de fusionar a `main`.
8. Fusionar y desplegar mediante el workflow Hostinger existente.

## Credenciales y secretos

La `anon key` de Supabase es una credencial pública de cliente y su seguridad depende de RLS. Aun así, **nunca** deben colocarse en el repositorio:

- `service_role`;
- contraseña de base;
- tokens administrativos;
- contraseñas de usuarios;
- secretos SFTP/Hostinger;
- documentos o análisis internos.

## Criterio de publicación

Esta implementación debe permanecer en rama/PR hasta que Supabase esté conectado y las pruebas de acceso confirmen:

- un usuario anónimo no puede leer tablas privadas;
- un usuario autenticado pero inactivo no puede ingresar;
- `legisladora` puede leer pero no modificar análisis;
- `asesor` e `investigador` pueden crear/editar;
- `admin` puede administrar y borrar;
- ninguna información interna aparece en sitemap, buscador público ni datasets GitHub.

## Próximas extensiones

Una vez estabilizado el núcleo:

- editor específico de carpeta de sesión;
- comparación proyecto original vs. dictamen;
- vinculación automática entre expediente y análisis;
- alertas por comisión/tema;
- notas y comentarios por usuario;
- historial/versionado de recomendaciones;
- exportación de briefing a PDF;
- MFA/TOTP para usuarios con acceso a información especialmente sensible;
- futura Área Comunas reutilizando la misma capa de identidad y permisos.
