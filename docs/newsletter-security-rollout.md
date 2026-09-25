# Suscripción segura — plan de activación

## Estado auditado

La portada publica el correo directamente en `public.newsletter_subscriptions` mediante la Data API y una clave publicable. La tabla tiene RLS, una política de `INSERT` para `anon`, validación de formato, índice único, consentimiento obligatorio en la interfaz y honeypot.

Faltan controles server-side de frecuencia, verificación antiabuso y doble opt-in. La respuesta pública actual comunica una suscripción activa antes de verificar la casilla.

## Arquitectura preparada

```text
Portada -> Turnstile -> Edge Function -> rate limit por huella HMAC
                                      -> suscripción pending
                                      -> correo de confirmación
Enlace de correo -> Edge Function -> suscripción active
```

Principios:

- la clave `service_role`, el secreto de Turnstile, la sal de rate limit y la clave de correo permanecen sólo en secretos de Supabase;
- la IP no se almacena: se conserva una huella HMAC horaria no reversible;
- máximo de cinco intentos por hora y huella;
- reenvío del mismo correo limitado a uno cada quince minutos;
- token aleatorio de 256 bits, almacenado sólo como SHA-256 y con vencimiento de 24 horas;
- respuesta genérica para correos ya activos o pendientes, evitando enumeración;
- origen, hostname y acción de Turnstile verificados;
- dependencias fijadas por versión;
- `INSERT` directo de `anon` revocado al activar el backend.

## Prerrequisitos externos

1. Crear un widget Cloudflare Turnstile administrado para `cepoes.org` y `www.cepoes.org`.
2. Verificar el dominio remitente en Resend y definir una casilla, por ejemplo `CEPOES <novedades@cepoes.org>`.
3. Configurar en Supabase:
   - `TURNSTILE_SECRET_KEY`;
   - `TURNSTILE_ALLOWED_HOSTNAMES=cepoes.org,www.cepoes.org`;
   - `RATE_LIMIT_SALT` aleatoria y de alta entropía;
   - `RESEND_API_KEY`;
   - `NEWSLETTER_FROM`.
4. Conservar la site key pública de Turnstile para la segunda etapa del frontend.

No registrar valores secretos en GitHub, logs, documentación ni código.

## Secuencia de activación sin corte

Este PR no debe aplicarse parcialmente en producción.

1. Validar gratuitamente el contrato estático y las funciones puras con
   `python validar_suscripcion_segura.py` y
   `node --test tests/newsletter_logic.test.mjs`.
2. Para la prueba integrada, usar una rama de desarrollo de Supabase o un
   proyecto de prueba sólo si se autoriza expresamente su costo. La validación
   local no modifica producción ni sustituye esa prueba integrada.
3. Aplicar la migración y desplegar `newsletter-subscribe` con verificación JWT desactivada.
4. Configurar los secretos sólo en el entorno de prueba.
5. Probar:
   - origen no permitido: 403;
   - cuerpo inválido: 400;
   - Turnstile inválido: 400;
   - sexto intento en una hora: 429;
   - alta válida: estado `pending`;
   - repetición antes de quince minutos: respuesta genérica sin nuevo correo;
   - token válido: estado `active`;
   - token vencido, reutilizado o modificado: rechazo;
   - ninguna lectura pública de correos;
   - asesores de seguridad sin nuevos hallazgos críticos.
6. Preparar un segundo PR de frontend que:
   - renderice Turnstile con la site key pública;
   - envíe `email`, `consent`, `company` y `turnstile_token` a la Edge Function;
   - deje de usar `/rest/v1/newsletter_subscriptions`;
   - informe “Revisá tu correo para confirmar” y no “Te sumamos”.
7. En ventana coordinada:
   - desplegar función y secretos;
   - ejecutar la migración;
   - fusionar/publicar el frontend;
   - realizar smoke test completo.
8. Si el frontend no completa el smoke, revertir su publicación. Si la función falla antes del cambio de portada, no ejecutar la migración.

## Rollback

- frontend: volver al activo anterior sólo si se restaura temporalmente la política de `INSERT` anónimo;
- backend: conservar las columnas nuevas; restaurar la política anterior únicamente como contingencia breve;
- no eliminar suscripciones ni tokens durante el rollback;
- investigar logs sin registrar direcciones de correo, tokens ni IP.

## Fuera de alcance de este PR

- creación de cuentas Cloudflare o Resend;
- carga o rotación de secretos;
- cambios en la base productiva;
- despliegue de la Edge Function;
- modificación de la portada;
- fusión o publicación.
