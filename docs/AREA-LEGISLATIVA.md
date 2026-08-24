# CEPOES · Área Legislativa privada

## Objetivo

Crear una capa de trabajo reservada para legisladores, asesores e investigadores autorizados sin mezclar información estratégica con el sitio público ni con los datasets públicos del repositorio.

Ruta: `/legislativa/`.

La ruta pública existente `/legislatura/` sigue siendo el Monitor Legislativo abierto. No se sustituye ni se mezclan sus contenidos.

## Principio de seguridad

La aplicación aplica una separación estricta de dos capas:

1. **Capa oficial/pública**: agenda, expedientes, estructura de comisiones, sesiones, sanciones y votaciones. Se obtiene de los procesos ya existentes de CEPOES y puede residir en GitHub.
2. **Capa interna**: análisis, recomendación, prioridad política, argumentos, modificaciones, preguntas para comisión, carpetas de sesión, comentarios y banco de proyectos. Reside exclusivamente en Supabase con autenticación y Row Level Security (RLS).

Una URL oculta o una contraseña en JavaScript no constituyen protección. La UI de `/legislativa/` falla cerrada si Supabase no está configurado o si el perfil no está activo.

## Roles

- `legisladora`: lectura del contenido interno.
- `asesor`: lectura y edición de análisis, carpetas y banco de proyectos.
- `investigador`: lectura y edición de análisis técnico.
- `admin`: administración funcional y acceso completo a los registros privados.

El usuario debe existir en Supabase Auth **y** tener un registro `profiles.active = true`.

## Alta de usuarios

Los correos autorizados se cargan en `private.access_allowlist`, junto con su rol inicial. Las filas reales de esa tabla no se versionan en GitHub.

Desde `/legislativa/`, una persona puede solicitar un enlace seguro de acceso por correo. Cuando Supabase Auth crea la identidad, el trigger `private.handle_new_user()` consulta la allowlist:

- si el correo está autorizado, crea/actualiza `profiles` con el rol y estado definidos;
- si no está autorizado, el perfil queda inactivo y no puede acceder al contenido interno.

Esto permite el primer acceso sin contraseñas provisorias ni secretos compartidos.

## Componentes incorporados

### Frontend

- `deploy/site-overlay/legislativa/index.html`
- `deploy/site-overlay/assets/legislativa.css`
- `deploy/site-overlay/assets/legislativa.js`
- `deploy/site-overlay/assets/legislativa-config.js`

La aplicación incluye login, enlace seguro por correo, validación de perfil y rol, dashboard, filtros de expedientes, análisis internos, carpetas de sesión, banco de proyectos e indicadores visibles de uso interno. La página lleva `noindex`, `nofollow`, `noarchive`, `nosnippet` y `noimageindex`.

### Base privada

- `infra/supabase/legislativa.sql`: esquema inicial.
- `infra/supabase/002_harden_legislativa.sql`: helpers privados y endurecimiento posterior a auditoría.
- `infra/supabase/003_access_allowlist.sql`: allowlist y alta segura por correo.

El rol `anon` no tiene privilegios sobre las tablas privadas. Los helpers sensibles están fuera del esquema público.

## Puesta en marcha

1. Conectar el proyecto Supabase CEPOES.
2. Aplicar las migraciones del directorio `infra/supabase/`.
3. Cargar directamente en Supabase los correos autorizados y su rol en `private.access_allowlist`.
4. Publicar `/legislativa/`.
5. La persona autorizada solicita su enlace de acceso desde la pantalla de login.
6. Verificar los permisos de cada rol extremo a extremo.

## Credenciales y secretos

La publishable key de Supabase es pública por diseño y opera bajo Auth + RLS. Nunca deben colocarse en el repositorio:

- `service_role` o secret keys;
- contraseña de base;
- tokens administrativos;
- contraseñas de usuarios;
- secretos SFTP/Hostinger;
- correos reales de la allowlist;
- documentos o análisis internos.

## Validación

`verificar_area_legislativa.py` y el workflow `Validar Área Legislativa privada` controlan estructura, fail-closed, ausencia de secretos, `noindex/nofollow` y presencia de RLS/revocación anónima. Después de cambios de esquema se ejecuta además el asesor de seguridad de Supabase.

## Próximas extensiones

- editor específico de carpeta de sesión;
- comparación proyecto original vs. dictamen;
- vinculación automática entre expediente y análisis;
- alertas por comisión/tema;
- notas y comentarios por usuario;
- historial/versionado de recomendaciones;
- exportación de briefing a PDF;
- MFA/TOTP para usuarios con acceso a información especialmente sensible;
- futura Área Comunas reutilizando la misma capa de identidad y permisos.
