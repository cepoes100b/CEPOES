# Boletín automático CEPOES — activación

Estado 2026-10-07: dominio cepoes.org verificado en Resend. Código preparado; ninguna migración ni función de newsletter aplicada a producción. Configuración pública y workflow desactivados.

## Circuito

La portada solicita Turnstile y consentimiento. La función privada guarda el alta pendiente y envía un enlace de confirmación con vencimiento de 24 horas. Confirmar activa el correo. Cada edición detectada en el catálogo público genera una cola para los suscriptores activos de ese momento. La cola se revisa después de un despliegue exitoso y cada hora. Una edición y un suscriptor tienen un único registro. Los cambios de una edición ya registrada no disparan otro envío. La primera activación comienza con el boletín N.º 6; no distribuye automáticamente los cinco anteriores.

La baja requiere confirmar una solicitud POST; abrir el enlace no da de baja, evitando escáneres de correo. Se incluyen cabeceras de baja con un clic.

## Configuraciones externas pendientes

1. Crear en Cloudflare un widget gratuito Turnstile administrado, hostnames cepoes.org y www.cepoes.org. Site key pública en assets/data/newsletter-config.json; clave secreta exclusivamente en Supabase.
2. Crear en Resend una API key de sólo envío restringida al dominio cepoes.org. Guardarla directamente en secretos de Supabase; nunca copiarla al repositorio, conversación o logs.
3. Secretos de Supabase: RESEND_API_KEY, NEWSLETTER_FROM (CEPOES <novedades@cepoes.org>), TURNSTILE_SECRET_KEY, TURNSTILE_ALLOWED_HOSTNAMES (cepoes.org,www.cepoes.org), RATE_LIMIT_SALT, NEWSLETTER_UNSUBSCRIBE_SECRET, NEWSLETTER_DISPATCH_SECRET y NEWSLETTER_ENABLED=true. Los tres secretos propios deben ser aleatorios, distintos y de alta entropía. Guardar copia segura del secreto de baja: rotarlo invalida enlaces previos.
4. GitHub: secreto NEWSLETTER_DISPATCH_SECRET con el mismo valor del servidor; variable NEWSLETTER_ENABLED=true sólo después de las pruebas integradas.

Los conectores disponibles no permiten escribir secretos en Supabase ni GitHub. Esta carga debe completarse en sus paneles o mediante CLI autenticada autorizada; no se solicita pegar claves en el chat.

## Secuencia coordinada

1. Ejecutar node --test tests/newsletter_logic.test.mjs tests/newsletter_delivery.test.mjs, python validar_suscripcion_segura.py, controles obligatorios y prueba del build canónico.
2. Configurar secretos y desplegar las tres funciones newsletter-subscribe, newsletter-dispatch y newsletter-unsubscribe con verify_jwt=false. El dispatcher exige su propio Bearer secreto. Todavía no activar la variable de GitHub.
3. Preparar site key y enabled=true en la configuración pública. Aplicar ambas migraciones en orden y publicar frontend en una ventana coordinada: la primera revoca INSERT anónimo y el formulario anterior deja de poder guardar altas.
4. Probar en escritorio y móvil: alta pendiente, recepción de confirmación, token válido/vencido/reutilizado, rechazo de origen y captcha inválidos, límite de frecuencia, respuesta genérica para correo existente, lectura pública de correos bloqueada, baja confirmada y baja con un clic.
5. Probar entrega con una edición de prueba aislada y receptor de prueba consentido; no insertar una edición falsa en el catálogo público. Verificar eventos reales del proveedor. accepted significa aceptado por Resend, no entregado a la bandeja.
6. Activar GitHub y verificar primer workflow. El catálogo se genera desde páginas públicas durante el build, sin borradores ni redirects. Revisar asesores de seguridad.

## Fiabilidad y operación

Procesamiento de cinco destinatarios por ejecución; reserva conservadora de 50 primeras entregas por día, sin contratar planes pagos. El correo de confirmación también consume cuota del proveedor. Ante timeout se reintenta con la misma clave de idempotencia. Pasadas 18 horas desde el primer intento, pasa a review y el workflow falla para pedir revisión humana: no se reenvía automáticamente fuera de la ventana de idempotencia del proveedor. Revisar estos casos y cuotas en el panel antes de resolverlos. No se garantiza recepción en bandeja; pueden existir rebotes, spam o supresiones del proveedor.

## Rollback

Desactivar primero NEWSLETTER_ENABLED en GitHub y Supabase. Preservar suscripciones, cola y estados de envío. Revertir frontend sólo si se restaura la política de INSERT anterior como contingencia breve. No borrar entregas aceptadas ni reutilizar números de edición.
# Plantilla editorial y prueba de distribución — 8 de octubre de 2026 (UTC)

El sistema ya confirmó una suscripción y entregó el N.º 5 únicamente al destinatario de prueba autorizado. La configuración `NEWSLETTER_DISPATCH_SECRET` debe tener el mismo valor en Supabase y en **Repository secrets** de GitHub. El workflow 37670720937 se ejecutó satisfactoriamente después de corregir ese faltante.

El correo usa la marca tipográfica y los colores de CEPOES, número y mes, introducción, tres indicadores, hasta cuatro extractos y agenda pública. El catálogo toma texto y fuentes del HTML aprobado. La columna privada `newsletter_editions.email_content` conserva una instantánea antes del primer envío; los reintentos reutilizan ese contenido. Se mantiene la alternativa de texto simple y la baja personal. La nueva prueba de diseño se envía sólo al destinatario autorizado, con una clave de idempotencia independiente del envío automático ya realizado.

Las siguientes secciones conservan el procedimiento original de activación. La baja real y la recepción en otros clientes de correo todavía requieren comprobación.
